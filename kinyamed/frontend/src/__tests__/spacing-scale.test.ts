/** Every spacing utility used in the source must exist in the scale.
 *
 * WHY THIS TEST EXISTS. `tailwind.config.js` REPLACES `theme.spacing` rather
 * than extending it. A step that is missing from that map does not raise, does
 * not warn and does not appear in the build log -- the utility simply emits no
 * CSS and the element gets no rule.
 *
 * That is not hypothetical. `min-h-11` sat on every button, nav link and input
 * in this app, under a comment asserting a 44px minimum touch target, while
 * `11` was absent from the scale. The shipped stylesheet contained exactly one
 * min-height rule. Measured in a real browser at 360px, 25 of 26 interactive
 * elements were 20-22px tall -- a mis-tap on a control that changes a
 * patient's queue status.
 *
 * A comment cannot catch that and a type checker cannot either, because these
 * are strings in a className. This test is the only thing between that class
 * of bug and a health centre, so it reads the config and the source and
 * compares them.
 */
import { describe, expect, it } from "vitest";
import { readFileSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";
// The Tailwind config is plain JS with no types, which is how Tailwind ships
// them. Importing it is the point of this test -- reading the real scale
// rather than a copy of it -- so the import is asserted rather than avoided.
// @ts-expect-error - untyped JS config, shape asserted below
import config from "../../tailwind.config.js";

const SRC = join(__dirname, "..");

/** Utility prefixes whose numeric suffix is resolved from `theme.spacing`. */
const SPACING_PREFIXES = [
  "min-h", "min-w", "max-h",
  "gap-x", "gap-y", "gap",
  "space-x", "space-y",
  "p", "px", "py", "pt", "pr", "pb", "pl",
  "m", "mx", "my", "mt", "mr", "mb", "ml",
  "w", "h", "size",
  "top", "right", "bottom", "left", "inset",
];

// Longest first: `px` must match before `p`, or `px-4` reads as p-x4.
const PREFIX_RE = SPACING_PREFIXES.sort((a, b) => b.length - a.length).join("|");

/**
 * Matches a spacing utility with a NUMERIC step, allowing a responsive or
 * state prefix and a leading `-` for negative margins.
 *
 * Deliberately does not match `w-full`, `h-screen`, `max-w-5xl` or `w-1/2`:
 * those resolve from other scales, or from no scale at all, and flagging them
 * would make this test noisy enough to be switched off.
 */
const UTILITY = new RegExp(
  String.raw`(?:^|[\s"'\`])-?(?:[a-z]+:)*(${PREFIX_RE})-(\d+(?:\.\d+)?|px)(?=$|[\s"'\`])`,
  "g",
);

function sourceFiles(dir: string): string[] {
  const out: string[] = [];
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry);
    if (statSync(full).isDirectory()) {
      if (entry === "__tests__" || entry === "__design__") continue;
      out.push(...sourceFiles(full));
    } else if (/\.tsx?$/.test(entry)) {
      out.push(full);
    }
  }
  return out;
}

const scale = (config as { theme: { spacing: Record<string, string> } }).theme.spacing;

describe("the spacing scale covers every utility the source uses", () => {
  const files = sourceFiles(SRC);

  it("finds source files to check", () => {
    expect(files.length).toBeGreaterThan(5);
  });

  it.each(files.map((f) => [f.slice(SRC.length + 1), f]))(
    "%s uses only steps that exist",
    (_label, file) => {
      const text = readFileSync(file, "utf8");
      const missing: string[] = [];
      for (const match of text.matchAll(UTILITY)) {
        const prefix = match[1];
        const step = match[2];
        if (step === undefined) continue;
        if (!(step in scale)) missing.push(`${prefix}-${step}`);
      }
      expect(
        missing,
        `these utilities resolve to NO CSS because theme.spacing has no such ` +
          `step -- add it to tailwind.config.js or change the class: ` +
          `${[...new Set(missing)].join(", ")}`,
      ).toEqual([]);
    },
  );

  it("still defines 11, the 44px touch target", () => {
    // Named explicitly because this is the one whose absence shipped, and
    // because a future tidy-up of "unused" steps would remove it first.
    expect(scale["11"]).toBe("2.75rem");
  });
});
