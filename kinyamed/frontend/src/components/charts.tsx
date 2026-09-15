import type { ReactNode } from "react";

/** The only chart primitives this product has, and deliberately few.
 *
 * TWO RULES DECIDED THESE, and both were computed rather than chosen.
 *
 * 1. NO STACKED URGENCY BAR, EVER. Running the three urgency fills through a
 *    CVD validator returns ΔE 1.9 between CRITICAL (#a2120b) and URGENT
 *    (#8a4b00) under deuteranopia, and 10.1 at normal vision against a floor
 *    of 15. Adjacent segments of one bar would be indistinguishable to a
 *    red-green colour-blind reader -- around 8% of men -- and the two
 *    categories they could not separate are the two that decide who is seen
 *    first. So urgency is drawn as SEPARATE rows, each carrying its own word
 *    and number. Colour reinforces; the label identifies. That is the
 *    project's own rule 2, and the validator is the reason to trust it.
 *
 * 2. NO CATEGORICAL PALETTE ANYWHERE ELSE. Language, SMS and wait-time bars
 *    are neutral ink, not a set of hues. A dashboard that paints four
 *    languages in four colours has spent the one channel urgency needs, on
 *    the page where a nurse is looking for critical patients.
 */

function pct(value: number, total: number): number {
  return total > 0 ? Math.min(100, Math.max(0, (value / total) * 100)) : 0;
}

/** A hero number. Not a chart, on purpose.
 *
 * A single magnitude with no comparison is a stat tile; drawing a
 * one-datum chart around it adds ink and no information.
 */
export function Metric({
  label,
  value,
  note,
  tone = "neutral",
}: {
  label: string;
  value: ReactNode;
  note?: string;
  tone?: "neutral" | "critical";
}) {
  return (
    <div className="rounded-lg border border-ink-200 bg-white px-4 py-4 shadow-card sm:px-5">
      <div className="text-xs font-semibold uppercase tracking-wide text-ink-600">
        {label}
      </div>
      <div
        className={[
          "tnum mt-2 text-2xl font-semibold",
          // The only place a metric takes urgency colour is when it IS an
          // urgency count. Everywhere else the number is ink.
          tone === "critical" ? "text-critical" : "text-ink-900",
        ].join(" ")}
      >
        {value}
      </div>
      {note && <p className="mt-1 text-xs leading-snug text-ink-600">{note}</p>}
    </div>
  );
}

/** One labelled bar. The label is the identity; the fill is magnitude.
 *
 * Marks follow the house spec: thin, rounded data-end, recessive track, and
 * the value set in ink rather than in the bar's own colour.
 */
export function BarRow({
  label,
  value,
  total,
  display,
  fill = "bg-ink-700",
  title,
  showShare = true,
}: {
  label: string;
  value: number;
  total: number;
  display?: string;
  /** Show the percentage. FALSE when `total` is merely the larger of two
   *  magnitudes rather than a whole -- a share of a non-whole is a number the
   *  reader will try to interpret and cannot. */
  showShare?: boolean;
  /** Tailwind background class. Urgency fills only where the row IS an urgency. */
  fill?: string;
  title?: string;
}) {
  const share = pct(value, total);
  return (
    <div title={title ?? `${label}: ${value} of ${total}`}>
      <div className="flex items-baseline justify-between gap-4">
        <span className="text-sm font-medium text-ink-800">{label}</span>
        <span className="tnum text-sm text-ink-700">
          {display ?? value.toLocaleString()}
          {showShare && (
            <span className="ml-2 text-ink-600">{share.toFixed(0)}%</span>
          )}
        </span>
      </div>
      {/* h-2 track, rounded ends. The track is a surface, not a series. */}
      <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-ink-100">
        <div
          className={`h-2 rounded-full ${fill}`}
          style={{ width: `${share}%` }}
          role="img"
          aria-label={
            showShare
              ? `${label}: ${value} of ${total}, ${share.toFixed(0)} percent`
              : `${label}: ${display ?? value}`
          }
        />
      </div>
    </div>
  );
}

/** A framed block with a title and an explanation of what the number means.
 *
 * Every panel states its own provenance. On a dashboard whose subject is a
 * model that has not met its safety gate, a number without a caveat is the
 * failure mode.
 */
export function Panel({
  title,
  hint,
  children,
  footnote,
}: {
  title: string;
  hint?: string;
  children: ReactNode;
  footnote?: string;
}) {
  return (
    <section className="rounded-lg border border-ink-200 bg-white shadow-card">
      <header className="border-b border-ink-200 px-4 py-4 sm:px-5">
        <h2 className="text-sm font-semibold text-ink-900">{title}</h2>
        {hint && <p className="mt-1 text-xs leading-snug text-ink-600">{hint}</p>}
      </header>
      <div className="space-y-4 px-4 py-5 sm:px-5">{children}</div>
      {footnote && (
        <p className="border-t border-dashed border-ink-200 px-4 py-3 text-xs leading-snug text-ink-600 sm:px-5">
          {footnote}
        </p>
      )}
    </section>
  );
}


/** A column series over days. One measure, one colour, always labelled.
 *
 * WHY COLUMNS AND NOT A LINE. Daily counts are discrete events, not a
 * continuous quantity sampled over time; a line implies a value existed
 * between Tuesday and Wednesday. Columns also make a zero day visibly zero
 * rather than a dip in a curve, which matters because the API zero-fills and
 * a closed clinic is a real fact about the series.
 *
 * WHY NOT THREE SERIES ON ONE CHART. The acuity trio fails CVD separation --
 * CRITICAL and URGENT are ΔE 1.9 apart under deuteranopia -- so three overlaid
 * or stacked series would be unreadable to a red-green colour-blind reader.
 * Callers render one of these PER ACUITY as small multiples on a shared scale
 * instead, which the colour validator's own guidance prescribes.
 */
export function ColumnSeries({
  points,
  max,
  fill = "bg-ink-700",
  unitLabel,
}: {
  points: Array<{ day: string; value: number }>;
  /** Shared across small multiples so the panels are comparable. */
  max: number;
  fill?: string;
  unitLabel: string;
}) {
  const ceiling = Math.max(max, 1);
  return (
    <div>
      <div className="flex h-20 items-end gap-px" role="img"
           aria-label={`${unitLabel}. ${points.length} days, highest ${max}.`}>
        {points.map((p) => {
          const height = (p.value / ceiling) * 100;
          return (
            <div
              key={p.day}
              // `h-full` matters: the track is `h-20`, but a `flex-1` child
              // under `items-end` is sized to its CONTENT, so a percentage
              // height on the bar resolved against `auto` and every column
              // collapsed to nothing. A definite height here is what the
              // percentage below resolves against.
              className="relative h-full flex-1"
              // Native title: a real tooltip on every column of a 30-day
              // series is a lot of DOM for a value the label already implies.
              title={`${p.day}: ${p.value} ${unitLabel}`}
            >
              <div
                className={`absolute bottom-0 w-full rounded-sm ${
                  p.value > 0 ? fill : "bg-ink-200"
                }`}
                // A zero day still draws 2px, so "nothing happened" is visible
                // rather than an absence a reader must infer from a gap.
                style={{ height: p.value > 0 ? `${Math.max(height, 4)}%` : "2px" }}
              />
            </div>
          );
        })}
      </div>
      <div className="mt-2 flex justify-between text-xs text-ink-600">
        <span className="tnum">{points[0]?.day ?? ""}</span>
        <span className="tnum">{points[points.length - 1]?.day ?? ""}</span>
      </div>
    </div>
  );
}

/** p50 and p90 for one acuity, on a shared scale.
 *
 * Two marks distinguished by POSITION and LABEL, never by hue: the whole
 * panel is one acuity, so colour here would carry no information and would
 * spend a channel urgency needs.
 */
export function WaitBar({
  label,
  stats,
  max,
  fill,
}: {
  label: string;
  stats: { p50_minutes: number; p90_minutes: number; completed: number } | null;
  max: number;
  fill: string;
}) {
  if (!stats) {
    return (
      <div>
        <div className="flex items-baseline justify-between gap-4">
          <span className="text-sm font-medium text-ink-800">{label}</span>
          <span className="text-sm text-ink-600">not measured</span>
        </div>
        <p className="mt-1 text-xs text-ink-600">
          No completed entries at this acuity yet.
        </p>
      </div>
    );
  }
  const ceiling = Math.max(max, 1);
  return (
    <div>
      <div className="flex items-baseline justify-between gap-4">
        <span className="text-sm font-medium text-ink-800">{label}</span>
        <span className="tnum text-sm text-ink-700">
          p50 {Math.round(stats.p50_minutes)} min
          <span className="ml-3">p90 {Math.round(stats.p90_minutes)} min</span>
        </span>
      </div>
      <div className="mt-2 space-y-1">
        <div className="h-2 w-full rounded-full bg-ink-100">
          <div
            className={`h-2 rounded-full ${fill}`}
            style={{ width: `${(stats.p50_minutes / ceiling) * 100}%` }}
            role="img"
            aria-label={`${label} median wait ${Math.round(stats.p50_minutes)} minutes`}
          />
        </div>
        {/* p90 drawn thinner and beneath: same scale, visibly the outer
            measure rather than a second category. */}
        <div className="h-1 w-full rounded-full bg-ink-100">
          <div
            className={`h-1 rounded-full ${fill} opacity-60`}
            style={{ width: `${(stats.p90_minutes / ceiling) * 100}%` }}
            role="img"
            aria-label={`${label} 90th percentile wait ${Math.round(stats.p90_minutes)} minutes`}
          />
        </div>
      </div>
      <p className="mt-1 text-xs text-ink-600">
        over {stats.completed.toLocaleString()} completed
      </p>
    </div>
  );
}
