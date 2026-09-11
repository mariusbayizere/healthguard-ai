import type { ButtonHTMLAttributes, ReactNode } from "react";

/** Three primitives. Not a component library: a component library brings a
 *  design language with it, and the point of this system is that urgency is
 *  the only thing shouting.
 *
 *  TOUCH TARGETS. Every interactive element is at least 44px tall (`min-h-11`).
 *  This is a tool used standing up, on a phone, possibly with gloves.
 *
 *  That sentence was FALSE from the first commit until 2026-09-11 and nothing
 *  caught it: `theme.spacing` is replaced rather than extended in
 *  `tailwind.config.js` and had no `11`, so `min-h-11` emitted no CSS and
 *  these controls measured 20-22px in a browser. The comment described the
 *  intent and the build shipped the opposite. `src/__tests__/spacing-scale.test.ts`
 *  now fails if any spacing utility used here has no step in the scale, which
 *  is what makes the sentence above checkable rather than aspirational.
 */

export function Card({
  title,
  children,
  actions,
}: {
  title?: string;
  children: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <section className="rounded-lg border border-ink-200 bg-white shadow-card">
      {(title ?? actions) && (
        <header className="flex flex-wrap items-baseline justify-between gap-3 border-b border-ink-200 px-4 py-4 sm:px-6">
          {title && <h2 className="text-lg font-semibold text-ink-900">{title}</h2>}
          {actions}
        </header>
      )}
      <div className="px-4 py-5 sm:px-6">{children}</div>
    </section>
  );
}

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "quiet" | "danger";
};

/** Three weights, and the third is the reason this is not two.
 *
 * `danger` is for an action that cannot be undone. The doctor board previously
 * made "Done" -- which removes a patient from the queue with no undo -- the
 * filled primary in every row, while "Seeing now", taken many times a shift,
 * was the quiet one: the emphasis exactly inverted, putting the most dangerous
 * control under the thumb five times on a board of five patients.
 *
 * IT IS NOT RED, and that was a deliberate reversal. The first version of this
 * variant used `critical` red for the outline and text, which is what a danger
 * button conventionally looks like -- and it broke rule 1 of this design
 * system: urgency is the ONLY saturated colour in the interface. Rendered, it
 * put a red control on every row of a board whose entire job is that red means
 * one thing. A nurse scanning for critical patients would have found five
 * buttons.
 *
 * So it recedes instead: neutral outline, dark ink, no new meaning for colour.
 * What makes it safe is the confirmation it triggers, not its paint.
 */
export function Button({ variant = "primary", className = "", ...rest }: ButtonProps) {
  const base =
    "inline-flex min-h-11 items-center justify-center rounded px-4 text-sm " +
    "font-semibold transition-colors duration-fast disabled:cursor-not-allowed " +
    "disabled:opacity-50";
  const tone = {
    primary: "bg-action text-white hover:bg-action-edge",
    quiet: "border border-ink-500 bg-white text-action hover:bg-action-soft",
    danger: "border border-ink-500 bg-white text-ink-800 hover:bg-ink-100",
  }[variant];
  return <button className={`${base} ${tone} ${className}`} {...rest} />;
}

export function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: ReactNode;
}) {
  // The hint sits ABOVE the control, not below it. It is an instruction, not a
  // footnote: "record their own words, not a summary" under the textarea is
  // read after the summary has been typed, which is too late to act on.
  return (
    <label className="block">
      <span className="block text-sm font-semibold text-ink-800">{label}</span>
      {hint && <span className="mt-1 mb-2 block text-xs text-ink-600">{hint}</span>}
      {!hint && <span className="mb-1 block" />}
      {children}
    </label>
  );
}

/** ink-500, not ink-300, for the boundary.
 *
 * WCAG 2.1 SC 1.4.11 requires 3:1 for the visual boundary of a control.
 * `ink-300` on white is 1.63:1 -- the field edge was effectively invisible in
 * bright light, which is the condition this whole palette was chosen for.
 * `ink-500` is 3.94:1. It stays below the 4.5 text floor and must not be used
 * for text; `contrast.test.ts` pins both facts.
 */
export const inputClass =
  "w-full min-h-11 rounded border border-ink-500 bg-white px-3 py-2 text-base " +
  "placeholder:text-ink-600 focus:border-action";

/** Errors are not all the same, and the difference decides what the reader does
 *  next. A validation failure means "correct something"; a connection failure
 *  means "try again, nothing you typed was wrong". Rendering both identically
 *  costs the reader the diagnosis. */
export function Alert({
  kind = "error",
  children,
  action,
}: {
  kind?: "error" | "offline" | "ok";
  children: ReactNode;
  action?: ReactNode;
}) {
  const tone = {
    error: "border-critical bg-critical-soft text-critical",
    offline: "border-urgent bg-urgent-soft text-urgent",
    ok: "border-routine bg-routine-soft text-routine",
  }[kind];
  return (
    <div
      role="alert"
      className={`flex flex-wrap items-center justify-between gap-3 rounded-r border-l-4 px-4 py-3 text-sm font-medium ${tone}`}
    >
      <span>{children}</span>
      {action}
    </div>
  );
}

/** An empty state names the next action. "Nobody is waiting" alone is correct
 *  and inert; a reader who expected rows needs to know whether that is normal. */
export function Empty({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="py-10 text-center">
      <p className="text-base font-medium text-ink-700">{title}</p>
      {children && <p className="mt-1 text-sm text-ink-600">{children}</p>}
    </div>
  );
}

/** Loading is NOT empty, and conflating them made the queue announce
 *  "Nobody is waiting" before its first fetch returned -- a false clinical
 *  statement on a slow connection. */
export function Skeleton({ rows = 3 }: { rows?: number }) {
  return (
    <div className="space-y-3 py-2" aria-busy="true" aria-live="polite">
      <span className="sr-only">Loading the queue…</span>
      {Array.from({ length: rows }, (_, i) => (
        <div key={i} className="flex items-center gap-4">
          <div className="h-10 w-12 animate-pulse rounded bg-ink-200" />
          <div className="h-6 w-24 animate-pulse rounded-full bg-ink-200" />
          <div className="h-5 flex-1 animate-pulse rounded bg-ink-100" />
        </div>
      ))}
    </div>
  );
}
