import {
  useLanguageBreakdown,
  useQueuePerformance,
  useSummary,
  useThroughput,
  useUrgencyBreakdown,
  useUrgencyOverTime,
  useWaitByUrgency,
} from "@/api/hooks";
import { BarRow, ColumnSeries, Metric, Panel, WaitBar } from "@/components/charts";
import { Alert, Skeleton } from "@/components/ui";

/** The dashboard. Four hero numbers, then four panels, then what is missing.
 *
 * WHAT THIS IS BUILT ON. Only the four analytics endpoints that exist:
 * /summary, /urgency-breakdown, /queue-performance and /language-breakdown.
 * Everything here is a field the server actually returns. The metrics a
 * triage dashboard SHOULD carry -- undertriage rate, clinician override rate,
 * p50/p90 waits -- are not among them, and the panel at the bottom says so
 * rather than letting their absence read as their absence of importance.
 *
 * WHY NO TREND LINES. There is no time series in the API; /analytics/daily
 * stores snapshots but nothing has been snapshotting. Drawing a line through
 * one point, or through invented points, would be the single worst thing a
 * dashboard about an unvalidated model could do.
 *
 * ADMIN ONLY. All four endpoints are gated on AdminUser server-side, so a
 * nurse or doctor account gets 403. That is shown as an explanation, not as
 * an empty board -- an analytics page that renders zeros to someone who is
 * merely unauthorised is a lie about the clinic.
 */

function minutes(value: number): string {
  return `${Math.round(value)} min`;
}

/** The four arms of the corpus, by their names.
 *
 * An ISO code is not a language name, and on the one panel whose subject is
 * which languages this system reads, "rw" is the least legible possible label
 * for the arm that carries most of the corpus. Unknown codes pass through
 * verbatim rather than being guessed at. */
const LANGUAGE_NAMES: Record<string, string> = {
  rw: "Kinyarwanda",
  en: "English",
  fr: "French",
  sw: "Kiswahili",
};

export function Dashboard() {
  const summary = useSummary();
  const urgency = useUrgencyBreakdown();
  const performance = useQueuePerformance();
  const languages = useLanguageBreakdown();
  const overTime = useUrgencyOverTime(30);
  const throughput = useThroughput(30);
  const waits = useWaitByUrgency();

  const queries = [
    summary, urgency, performance, languages, overTime, throughput, waits,
  ];
  const forbidden = queries.some(
    (q) => (q.error as { status?: number } | null)?.status === 403,
  );
  const error = queries.find((q) => q.isError)?.error as Error | undefined;

  if (forbidden) {
    return (
      <Alert kind="offline">
        These figures are restricted to administrator accounts. Ask an
        administrator to open the dashboard, or to change your role.
      </Alert>
    );
  }
  if (error) return <Alert>{error.message}</Alert>;
  if (queries.some((q) => q.isLoading)) return <Skeleton rows={5} />;

  const s = summary.data;
  const u = urgency.data;
  const p = performance.data;
  const l = languages.data;
  const t = overTime.data;
  const th = throughput.data;
  const w = waits.data;
  if (!s || !u || !p || !l || !t || !th || !w) return <Skeleton rows={5} />;

  // The gap between what a patient was told and what they waited. Positive
  // means the clinic ran slower than it promised.
  const waitGap = p.average_actual_wait_minutes - p.average_quoted_wait_minutes;

  const languageRows = Object.entries(l.counts).sort((a, b) => b[1] - a[1]);

  // ONE scale across the three acuity panels. Per-panel scaling would make a
  // day with 2 critical cases look identical to a day with 200 routine ones,
  // which is the most consequential lie a small-multiple layout can tell.
  const acuityMax = Math.max(
    ...t.points.flatMap((pt) => [pt.critical, pt.urgent, pt.routine]),
    1,
  );
  // Likewise one scale across the three wait bars, driven by the longest p90.
  const waitMax = Math.max(
    w.critical?.p90_minutes ?? 0,
    w.urgent?.p90_minutes ?? 0,
    w.routine?.p90_minutes ?? 0,
    1,
  );

  return (
    <div className="space-y-6">
      {/* Hero strip: four, which is inside the 3-5 a reader can hold. */}
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4 lg:gap-4">
        <Metric
          label="Waiting now"
          value={p.currently_waiting.toLocaleString()}
          note={`${p.currently_in_progress} being seen`}
        />
        <Metric
          label="Critical"
          value={s.critical_cases.toLocaleString()}
          tone="critical"
          note="Of all cases triaged"
        />
        <Metric
          label="Wait vs quoted"
          value={`${waitGap >= 0 ? "+" : ""}${Math.round(waitGap)} min`}
          note={`Told ${minutes(p.average_quoted_wait_minutes)}, waited ${minutes(
            p.average_actual_wait_minutes,
          )}`}
        />
        <Metric
          label="Doctors on duty"
          value={s.doctors_on_duty.toLocaleString()}
          note={`${p.completed_today} completed today`}
        />
      </div>

      {/* Small multiples, one per acuity, on a SHARED y scale so the panels
          are comparable at a glance. Three series on one chart is not an
          option here: CRITICAL and URGENT are ΔE 1.9 apart under
          deuteranopia, so overlaid or stacked they would be one series to a
          red-green colour-blind reader. */}
      <Panel
        title="Cases per day by acuity"
        hint={`Last ${t.days} days. Each panel shares the same vertical scale.`}
        footnote="Computed from triage rows, not from the daily snapshot table — that table stores cumulative all-time totals, so charting it would draw three curves that only ever rise. Days with no cases are drawn as zero rather than skipped, so nothing is interpolated across a closed day."
      >
        <div className="grid gap-6 sm:grid-cols-3">
          {([
            ["Critical", "critical", "bg-critical"],
            ["Urgent", "urgent", "bg-urgent"],
            ["Routine", "routine", "bg-routine"],
          ] as const).map(([label, key, fill]) => (
            <div key={key}>
              <div className="mb-2 flex items-baseline justify-between">
                <span className="text-sm font-medium text-ink-800">{label}</span>
                <span className="tnum text-sm text-ink-700">
                  {t.points.reduce((n, pt) => n + pt[key], 0).toLocaleString()}
                </span>
              </div>
              <ColumnSeries
                points={t.points.map((pt) => ({ day: pt.day, value: pt[key] }))}
                max={acuityMax}
                fill={fill}
                unitLabel={`${label.toLowerCase()} cases per day`}
              />
            </div>
          ))}
        </div>
      </Panel>

      <div className="grid gap-6 lg:grid-cols-2">
        <Panel
          title="Throughput"
          hint={`Patients completed per day. ${th.total_completed.toLocaleString()} over ${th.days} days.`}
          footnote="Measured on completion, not arrival: someone who arrived yesterday and was seen today is today's work."
        >
          <ColumnSeries
            points={th.points.map((pt) => ({ day: pt.day, value: pt.completed }))}
            max={Math.max(...th.points.map((pt) => pt.completed), 1)}
            fill="bg-action"
            unitLabel="completed per day"
          />
        </Panel>

        <Panel
          title="Wait by acuity"
          hint="Median and 90th percentile, joining the queue to completion."
          footnote="Percentiles, not the mean the summary reports. A mean hides the tail, and a CRITICAL p90 is the figure that says whether the sickest patients are actually seen first."
        >
          <WaitBar label="Critical" stats={w.critical} max={waitMax} fill="bg-critical" />
          <WaitBar label="Urgent" stats={w.urgent} max={waitMax} fill="bg-urgent" />
          <WaitBar label="Routine" stats={w.routine} max={waitMax} fill="bg-routine" />
        </Panel>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Panel
          title="Acuity mix"
          hint={`Share of ${u.total.toLocaleString()} triaged cases at each level.`}
          footnote="Drawn as three labelled rows rather than one stacked bar on purpose: CRITICAL and URGENT are ΔE 1.9 apart under deuteranopia, so adjacent segments would be indistinguishable to a red-green colour-blind reader. The word carries the identity here, not the fill."
        >
          <BarRow
            label="Critical"
            value={u.critical.count}
            total={u.total}
            fill="bg-critical"
          />
          <BarRow
            label="Urgent"
            value={u.urgent.count}
            total={u.total}
            fill="bg-urgent"
          />
          <BarRow
            label="Routine"
            value={u.routine.count}
            total={u.total}
            fill="bg-routine"
          />
        </Panel>

        <Panel
          title="Quoted wait against measured wait"
          hint="Whether the clinic keeps the promise it makes at intake."
          footnote="Both figures are MEANS — the API returns no percentiles. A mean hides the tail, and the tail is where a long wait becomes a clinical problem. p50/p90 would need a change to /analytics/queue-performance."
        >
          <BarRow
            label="Quoted at intake"
            value={Math.round(p.average_quoted_wait_minutes)}
            total={Math.max(
              p.average_quoted_wait_minutes,
              p.average_actual_wait_minutes,
              1,
            )}
            display={minutes(p.average_quoted_wait_minutes)}
            showShare={false}
          />
          <BarRow
            label="Actually waited"
            value={Math.round(p.average_actual_wait_minutes)}
            total={Math.max(
              p.average_quoted_wait_minutes,
              p.average_actual_wait_minutes,
              1,
            )}
            display={minutes(p.average_actual_wait_minutes)}
            fill="bg-ink-900"
            showShare={false}
          />
        </Panel>

        <Panel
          title="Language of the symptom report"
          hint={`Detected language across ${l.total.toLocaleString()} reports.`}
          footnote="Neutral bars, not a colour per language: a categorical palette here would spend the one channel urgency needs on a page where a nurse is looking for critical patients."
        >
          {languageRows.length === 0 ? (
            <p className="text-sm text-ink-600">No symptom reports yet.</p>
          ) : (
            languageRows.map(([code, count]) => (
                <BarRow
                key={code}
                label={LANGUAGE_NAMES[code] ?? code}
                value={count}
                total={l.total}
              />
            ))
          )}
        </Panel>

        <Panel
          title="Patient messages"
          hint="SMS delivery, where the feature flag is on."
          footnote="A failed message is a patient who was not told their urgency or queue number. It is counted, not hidden."
        >
          <BarRow
            label="Delivered"
            value={s.sms_sent}
            total={Math.max(s.sms_sent + s.sms_failed, 1)}
          />
          <BarRow
            label="Failed"
            value={s.sms_failed}
            total={Math.max(s.sms_sent + s.sms_failed, 1)}
            fill="bg-critical"
          />
        </Panel>
      </div>

      {/* The most important panel on the page. */}
      <section className="rounded-lg border border-dashed border-ink-400 bg-ink-50 px-4 py-5 sm:px-5">
        <h2 className="text-sm font-semibold text-ink-900">
          What this dashboard does not show
        </h2>
        <p className="mt-2 max-w-3xl text-sm leading-relaxed text-ink-700">
          Wait percentiles, throughput and the acuity series were added to the
          API on 2026-09-11 and are above. Two figures are still missing, and
          they are the two that would tell you whether this system is safe.
        </p>
        <ul className="mt-3 max-w-3xl space-y-2 text-sm leading-relaxed text-ink-700">
          <li>
            <strong className="font-semibold text-ink-900">
              Undertriage rate.
            </strong>{" "}
            The share of patients called ROUTINE or URGENT who turned out to
            need immediate care. It is one minus critical recall — the
            project&rsquo;s own acceptance gate, which this model does not
            currently meet.
          </li>
          <li>
            <strong className="font-semibold text-ink-900">
              Clinician override rate.
            </strong>{" "}
            How often a nurse or doctor changes the urgency the model
            suggested. It is the only direct measure of whether staff trust it,
            and the strongest signal available for improving it.
          </li>

        </ul>
        <p className="mt-4 max-w-3xl text-xs leading-relaxed text-ink-600">
          Each needs a new endpoint and, for the first two, a record of the
          clinician&rsquo;s decision against the model&rsquo;s. Nothing here
          estimates them.
        </p>
      </section>
    </div>
  );
}
