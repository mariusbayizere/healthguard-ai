# Real-time CRITICAL alerts: delivery design

**Status: PROPOSAL. Nothing in this document is built.** Written 2026-09-17 before item 3,
because "a doctor who drops briefly does not miss a CRITICAL" is a storage decision and not
a wiring decision, and getting it wrong is silent.

Requirements in play: `CLAUDE.md` §4.2 (Kafka producer/consumer, WebSocket push), §6.3
(event-consumer failure: offset not committed, DLQ, no message lost), §13 (no message lost
on consumer restart; CRITICAL → Kafka → consumer → WebSocket within 1 s),
`ENGINEERING_SPEC.md` §6.3.

---

## The decision that shapes everything else

**Kafka is a transport. It is not the store of record, and the backfill must not read from
it.**

The temptation is to treat the alert stream as the source of truth and replay it on
reconnect — Kafka has retention, so it looks like a log you can rewind. That design fails in
a way nobody notices until it matters:

- Retention is a **time** bound (default 7 days, often less under disk pressure). Clinical
  relevance is a **state** bound. A CRITICAL patient still waiting at hour 200 is still an
  emergency; a CRITICAL patient discharged twenty minutes ago is not. Time-bounded retention
  answers the wrong question in both directions.
- A browser is not a Kafka consumer. There is no consumer group holding a doctor's position,
  so "replay from where they were" has nowhere to read from without inventing one.
- A Kafka outage would then mean lost alerts, which is exactly what §6.3 forbids.

**The alerts are already durable.** A CRITICAL triage writes `triage_results` and `queue`
rows inside one transaction (that is item 0's audit work, unchanged). Those rows survive
indefinitely, and they are the clinical truth. So:

> **Backfill is a QUERY over existing state, not a replay of a message log.**

Kafka's job shrinks to what it is good at: getting an alert to a connected dashboard in
under a second. Everything about correctness after a disconnection is Postgres's job.

---

## 1. What survives a laptop sleeping through a shift, and for how long

**Survives: the alert itself, indefinitely, because it is a row and not a message.**

On reconnect the server answers one question:

```sql
-- every CRITICAL that is still clinically live, and not yet acknowledged BY THIS DOCTOR
SELECT q.* FROM queue q
  JOIN triage_results t ON t.id = q.triage_result_id
 WHERE t.urgency_level = 'CRITICAL'
   AND q.status IN ('WAITING', 'IN_PROGRESS')
   AND NOT EXISTS (SELECT 1 FROM queue_alert_acknowledgements a
                    WHERE a.queue_id = q.id AND a.user_id = :doctor)
```

**Bounded by state, not by time.** There is deliberately no `created_at > now() - interval`
clause:

| Scenario | What the doctor receives on reconnect |
|---|---|
| Dropped for 30 seconds | The CRITICALs they missed, still waiting |
| Laptop asleep for a whole shift | Every still-waiting CRITICAL, however old |
| Away a week; those patients were seen | Nothing. `status` is `DONE`, so they are history, not alerts |
| Away a week; one patient is *still waiting* | That one. It is eight days old and still an emergency |

A time window would have suppressed the last row, which is the only one that could kill
somebody. That is the whole argument for state-bounding.

**What does not survive, and should not:** the *ordering* of alerts as a stream, and any
alert for a patient no longer active. Neither is clinically meaningful after the fact.

---

## 2. Where the per-connection cursor lives, and what happens when it is lost

**Proposal: there is no authoritative cursor. State is the cursor.**

A cursor is an optimisation, and an optimisation that can silently disagree with reality is
a defect waiting to happen. So:

- The client **may** send `?since=<queue_id>` on connect, purely to shrink the first
  payload.
- The server treats it as a hint. It runs the state query regardless and uses `since` only
  to skip rows the client provably already rendered.
- If `since` is **absent, stale, unparseable, or from another deployment**, it is ignored
  and the full state-derived set is sent.

**So losing the cursor costs a larger payload, never a missed alert.** The failure direction
is duplicates, and duplicates are made harmless by rendering idempotently on `queue_id`: a
dashboard that already shows queue entry 412 does not show it twice.

This is the same reasoning as the blocklist's `is_blocked` returning `False` when Redis is
unreachable — pick the failure mode you can live with, and say which it is. Here the
tolerable failure is "the doctor sees an alert they already saw". The intolerable one is
"the doctor never sees it".

**Server-side cursor storage is explicitly rejected**: it adds a write on every delivery, it
has to be garbage-collected, and when it drifts from `queue.status` the drift is invisible.

---

## 3. Acknowledged versus merely delivered

**Yes, distinguishable — but only if acknowledgement is recorded explicitly, per doctor.**

Proposed table:

```
queue_alert_acknowledgements
  id, created_at, updated_at        (TimestampedModel)
  queue_id        FK queue(id)      ON DELETE CASCADE
  user_id         FK users(id)      ON DELETE CASCADE
  acknowledged_at timestamptz NOT NULL
  UNIQUE (queue_id, user_id)
```

Three states, all distinguishable:

| State | How it is known |
|---|---|
| Never delivered | No acknowledgement row, and the entry post-dates the doctor's last connection |
| Delivered, not acknowledged | No acknowledgement row. **Re-sent on every reconnect** |
| Acknowledged | A row for this `(queue_id, user_id)` |

**Per doctor, not per alert.** "Seen by the doctor going off shift" is not "seen by the
doctor coming on". A single global acknowledgement would let a CRITICAL vanish from the
incoming doctor's board because somebody else dismissed it.

**Acknowledgement is NOT a clinical disposition, and must not be conflated with one.** It
means "this alert reached a human". It does not mean the patient was assessed, and it must
not touch `queue.status`, which is the clinical record. Two separate facts, two separate
columns; overloading `status` would make "dismissed a popup" indistinguishable from "saw the
patient" in every later audit and every retraining set.

Acknowledging is a state change, so it writes an `audit_logs` row like everything else, and
the completeness test will require it.

---

## 4. The cost when Kafka is down (§6.3)

**Cost: alerts arrive late. No alert is lost, and no triage fails.**

| Component | With Kafka down |
|---|---|
| Triage write path | **Unaffected.** Publish happens *after* `db.commit()`, following the SMS precedent, so a broker outage cannot roll back a clinical record |
| Alert durability | **Unaffected.** The alert is a row; Kafka never held it |
| Dashboard latency | Degrades from sub-second push to the existing 5 s poll |
| Reconnect backfill | **Unaffected.** It is a Postgres query and never touched Kafka |
| Readiness | Reports `kafka: degraded`; does **not** gate, exactly as Redis does not. Taking pods out of rotation for a transport outage would turn it into a triage outage |

**The producer must never block the request.** A publish is attempted after commit with a
short timeout and a wrapped failure, logged once per transition rather than per triage.

**Consumer side**, per §6.3: `enable_auto_commit=False`; the offset is committed only after
the WebSocket fan-out has been attempted; an exception leaves the offset uncommitted so the
message is redelivered; a message that fails repeatedly goes to `kinyamed_alerts.DLQ` with
its failure count, so one poison payload cannot wedge the partition for every patient
behind it.

**The claim this design lets us make honestly:** a Kafka outage cannot lose a CRITICAL
alert, because Kafka was never what made it durable. What it costs is seconds of latency.

---

## What I would build, in order

1. `queue_alert_acknowledgements` table + migration (SQL shown before it runs).
2. The state query and its tests, **with no Kafka and no WebSocket at all** — backfill
   correctness is testable on its own and is the part that must not be wrong.
3. WebSocket endpoint + connection manager, delivering the backfill on connect.
4. Kafka producer after commit, wrapped; readiness reports it.
5. Consumer with `enable_auto_commit=False`, DLQ, offset-on-success.
6. The two required tests: no message lost across a consumer restart, and end-to-end under
   one second.

Note that steps 1–3 deliver the safety property (**no missed CRITICAL**) and steps 4–6
deliver the latency property (**sub-second**). If item 3 has to stop early, stopping after
step 3 leaves the system safer than it is today; stopping after step 5 would not.

---

## Open questions for the decision-maker

1. **Should an acknowledged CRITICAL ever re-alert** if the patient is still waiting after
   some interval? Clinically this is an escalation policy, not a delivery mechanism, and I
   have not designed one. Default proposed: no.
2. **Who receives an alert?** Proposed: every on-duty doctor. The alternative — only the
   assigned doctor — is not available, because a CRITICAL arrives before assignment.
3. **Retention of acknowledgement rows.** They grow with queue volume. Proposed: keep, since
   they are small and are audit-adjacent evidence of who saw what.
