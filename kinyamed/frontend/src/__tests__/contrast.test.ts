/** Every colour pair this interface actually renders meets WCAG AA.
 *
 * This is the contrast guarantee. axe cannot provide it -- jsdom applies no
 * stylesheet, so a11y.test.tsx disables the rule -- and the palette comment in
 * `tailwind.config.js` asserting "Contrast against white checked for AA" was
 * an unverified claim that had already failed: `ink-500` on white renders at
 * 3.94:1, under the 4.5 floor, and shipped as the "unassigned" label.
 *
 * Ratios are computed from the config, not from a copy of it, so changing a
 * hex value fails here rather than in a clinic.
 */
import { describe, expect, it } from "vitest";
// @ts-expect-error - untyped JS config, shape asserted below
import config from "../../tailwind.config.js";

type Palette = Record<string, string | Record<string, string>>;
const colors = (config as { theme: { colors: Palette } }).theme.colors;

function hex(path: string): string {
  const [name, shade] = path.split(".");
  const entry = colors[name!];
  const value = typeof entry === "string" ? entry : entry?.[shade ?? "DEFAULT"];
  if (!value) throw new Error(`no colour at ${path}`);
  return value;
}

function channel(c: number): number {
  const s = c / 255;
  return s <= 0.04045 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
}

function luminance(h: string): number {
  const v = h.replace("#", "");
  const [r, g, b] = [0, 2, 4].map((i) => parseInt(v.slice(i, i + 2), 16));
  return 0.2126 * channel(r!) + 0.7152 * channel(g!) + 0.0722 * channel(b!);
}

export function ratio(fg: string, bg: string): number {
  const [a, b] = [luminance(fg), luminance(bg)];
  return (Math.max(a!, b!) + 0.05) / (Math.min(a!, b!) + 0.05);
}

/** Pairs as they are actually used in the components, not every combination.
 *  A palette can be full of failing pairs that nothing renders. */
const PAIRS: Array<[string, string, string]> = [
  ["CRITICAL badge", "white", "critical.DEFAULT"],
  ["URGENT badge", "white", "urgent.DEFAULT"],
  ["ROUTINE badge", "white", "routine.DEFAULT"],
  ["primary button", "white", "action.DEFAULT"],
  ["quiet button label", "action.DEFAULT", "white"],
  ["danger button label", "ink.800", "white"],
  ["error alert text", "critical.DEFAULT", "critical.soft"],
  ["offline alert text", "urgent.DEFAULT", "urgent.soft"],
  ["ok alert text", "routine.DEFAULT", "routine.soft"],
  ["body text", "ink.900", "ink.50"],
  ["secondary text on white", "ink.700", "white"],
  ["caveat + labels on white", "ink.600", "white"],
  ["caveat on page ground", "ink.600", "ink.50"],
  ["'unassigned' on white", "ink.600", "white"],
  ["field label", "ink.800", "white"],
];

describe("WCAG AA contrast, computed from the palette", () => {
  it.each(PAIRS)("%s", (_name, fg, bg) => {
    expect(ratio(hex(fg), hex(bg))).toBeGreaterThanOrEqual(4.5);
  });

  it("rejects the pair that actually shipped failing", () => {
    // ink-500 on white, the old "unassigned" colour. Pinned so nobody
    // reintroduces it as a "subtle" tone.
    expect(ratio(hex("ink.500"), hex("white"))).toBeLessThan(4.5);
  });
});

/** WCAG 2.1 SC 1.4.11 Non-text Contrast — 3:1 for the visual boundary of a
 *  control, and for a focus indicator.
 *
 *  axe has NO rule for this. A full axe run in a real browser, all WCAG A/AA
 *  tags, reported zero contrast violations at 360, 768 and 1280 while the
 *  focus ring sat at 1.96:1 and every field border at 1.63:1. Automated green
 *  is not the same as accessible, and this block is the difference.
 */
function composite(fg: string, alpha: number, bg: string): string {
  const f = fg.replace("#", "");
  const b = bg.replace("#", "");
  const mix = [0, 2, 4].map((i) => {
    const a = parseInt(f.slice(i, i + 2), 16);
    const c = parseInt(b.slice(i, i + 2), 16);
    return Math.round(alpha * a + (1 - alpha) * c);
  });
  return `#${mix.map((v) => v.toString(16).padStart(2, "0")).join("")}`;
}

describe("WCAG 2.1 non-text contrast (3:1)", () => {
  const GROUNDS: Array<[string, string]> = [
    ["white card", hex("white")],
    ["page ground", hex("ink.50")],
    ["critical row fill", hex("critical.soft")],
    ["urgent row fill", hex("urgent.soft")],
  ];

  it.each(GROUNDS)("focus indicator is visible on %s", (_name, ground) => {
    // The ring is white spacer + solid action. The OUTER tone is what must
    // carry against the surrounding ground.
    expect(ratio(hex("action.DEFAULT"), ground)).toBeGreaterThanOrEqual(3);
  });

  it.each(GROUNDS)("control boundary is visible on %s", (_name, ground) => {
    expect(ratio(hex("ink.500"), ground)).toBeGreaterThanOrEqual(3);
  });

  it("rejects the translucent focus ring that shipped", () => {
    // rgba(27,58,107,0.35) over white. Pinned so nobody restores it as a
    // "softer" focus style.
    const old = composite(hex("action.DEFAULT"), 0.35, hex("white"));
    expect(ratio(old, hex("white"))).toBeLessThan(3);
  });

  it("rejects the ink-300 control boundary that shipped", () => {
    expect(ratio(hex("ink.300"), hex("white"))).toBeLessThan(3);
  });
});
