"""The three time-and-distribution analytics endpoints.

These exist because the dashboard asked for urgency over time, throughput and
wait by acuity, and the API could supply none of them. The tests below pin the
three properties that make them worth trusting:

  * the acuity series is computed from TRIAGE ROWS, not from the snapshot
    table, which stores cumulative all-time totals and would chart as three
    rising curves regardless of what happened in the clinic;
  * every day in the window is present, including empty ones, so a renderer
    cannot join across a gap and draw a slope nobody worked;
  * wait is reported as p50/p90 per acuity rather than as one mean, because
    the mean hides the tail and the tail is the clinical problem.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from app.models.queue import Queue, QueueStatus
from app.models.triage_result import TriageResult

# Phrases whose acuity the keyword baseline classifies deterministically, so a
# seeded fixture does not depend on the model artefact being present.
CRITICAL_TEXT = "mfite ububabare bw'igituza"
URGENT_TEXT = "mfite umuriro mwinshi"
ROUTINE_TEXT = "ndumva nkeneye kubonana na muganga"


def _triage(client, patient_factory, text: str) -> dict:
    patient = patient_factory()
    return client.post(
        "/api/v1/triage", json={"patient_id": patient["id"], "symptoms_input": text}
    ).json()


def _backdate_triage(db, triage_id: int, *, days_ago: int) -> None:
    """Move a triage row into the past.

    `created_at` carries a server default, so it is rewritten after the row
    exists rather than passed at creation — otherwise every row lands today and
    the series under test collapses into a single column.
    """
    row = db.get(TriageResult, triage_id)
    row.created_at = datetime.now(UTC) - timedelta(days=days_ago)
    db.commit()


@pytest.fixture
def seeded(client, patient_factory, db):
    """Cases on day 0 and day 2, nothing on day 1, plus two completed waits."""
    today_critical = _triage(client, patient_factory, CRITICAL_TEXT)
    today_routine = _triage(client, patient_factory, ROUTINE_TEXT)
    older_urgent = _triage(client, patient_factory, URGENT_TEXT)

    _backdate_triage(db, older_urgent["triage_id"], days_ago=2)

    # Two completed entries with known waits, one CRITICAL and one ROUTINE.
    now = datetime.now(UTC)
    for triage, minutes in ((today_critical, 10), (today_routine, 90)):
        entry = (
            db.query(Queue).filter(Queue.triage_result_id == triage["triage_id"]).one()
        )
        entry.status = QueueStatus.DONE
        entry.created_at = now - timedelta(minutes=minutes)
        entry.completed_at = now
    db.commit()
    return {"critical": today_critical, "routine": today_routine}


class TestUrgencyOverTime:
    def test_returns_every_day_in_the_window_including_empty_ones(self, client, seeded):
        response = client.get("/api/v1/analytics/urgency-over-time?days=3")
        assert response.status_code == 200
        body = response.json()

        assert body["days"] == 3
        assert len(body["points"]) == 3, (
            "a day with no cases must still appear. Omitting it lets a chart "
            "draw a straight line across the gap and imply work that never "
            "happened."
        )
        days = [p["day"] for p in body["points"]]
        assert days == sorted(days), "points must be chronological"

    def test_counts_land_on_the_right_days(self, client, seeded):
        body = client.get("/api/v1/analytics/urgency-over-time?days=3").json()
        oldest, middle, today = body["points"]

        assert oldest["urgent"] == 1, "the backdated URGENT case is two days ago"
        assert (middle["critical"], middle["urgent"], middle["routine"]) == (0, 0, 0)
        assert today["critical"] == 1
        assert today["routine"] == 1

    def test_is_not_cumulative(self, client, seeded):
        """The bug this endpoint exists to avoid.

        The `analytics` snapshot table stores all-time totals. Built from it,
        every day would be >= the day before and the chart could only rise.
        Here the empty middle day is genuinely zero.
        """
        body = client.get("/api/v1/analytics/urgency-over-time?days=3").json()
        totals = [p["critical"] + p["urgent"] + p["routine"] for p in body["points"]]
        assert totals[1] < totals[0], (
            f"day totals {totals} are non-decreasing, which is the signature of "
            "a cumulative series being charted as a rate"
        )

    @pytest.mark.parametrize("days", [0, 400])
    def test_rejects_an_out_of_range_window(self, client, days):
        assert (
            client.get(f"/api/v1/analytics/urgency-over-time?days={days}").status_code
            == 422
        )

    def test_is_admin_only(self, doctor_client):
        assert (
            doctor_client.get("/api/v1/analytics/urgency-over-time").status_code == 403
        )


class TestThroughput:
    def test_counts_completions_and_zero_fills(self, client, seeded):
        body = client.get("/api/v1/analytics/throughput?days=3").json()

        assert len(body["points"]) == 3
        assert body["total_completed"] == 2
        assert body["points"][-1]["completed"] == 2, "both completed today"
        assert body["points"][0]["completed"] == 0

    def test_is_admin_only(self, doctor_client):
        assert doctor_client.get("/api/v1/analytics/throughput").status_code == 403


class TestWaitByUrgency:
    def test_reports_percentiles_per_acuity(self, client, seeded):
        body = client.get("/api/v1/analytics/wait-by-urgency").json()

        assert body["critical"]["completed"] == 1
        assert body["routine"]["completed"] == 1
        # One sample per level, so p50 == p90 == that sample.
        assert body["critical"]["p50_minutes"] == pytest.approx(10, abs=1)
        assert body["routine"]["p90_minutes"] == pytest.approx(90, abs=1)

    def test_an_acuity_with_no_completions_is_null_not_zero(self, client, seeded):
        """0.0 would read as "seen instantly", the opposite of "not measured"."""
        body = client.get("/api/v1/analytics/wait-by-urgency").json()
        assert body["urgent"] is None

    def test_is_admin_only(self, doctor_client):
        assert doctor_client.get("/api/v1/analytics/wait-by-urgency").status_code == 403
