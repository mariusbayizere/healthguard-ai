/** Design tokens for a clinical triage tool.
 *
 * THE CONSTRAINT EVERY DECISION FOLLOWS FROM: a nurse scanning a full waiting
 * room must read urgency in well under a second, on a cheap screen, possibly in
 * bright light, possibly colour-blind.
 *
 * Three rules fall out of that and they are why this does not look like a
 * generic dashboard:
 *
 * 1. URGENCY IS THE ONLY SATURATED COLOUR IN THE INTERFACE. Everything else is
 *    neutral. A palette that decorates buttons and headers in brand colour
 *    competes with the one signal that matters and destroys it.
 * 2. COLOUR IS NEVER THE ONLY CHANNEL. Around 8% of men have red-green
 *    deficiency. Urgency is carried by colour AND a text label AND border
 *    weight AND sort position -- four redundant channels, so losing one costs
 *    nothing.
 * 3. NUMBERS ARE TABULAR. Queue numbers are read as a column; proportional
 *    digits make them ragged and slow to scan.
 */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    // Replaced, not extended: the default palette's 22 hues are exactly the
    // temptation this design must not have.
    colors: {
      transparent: "transparent",
      current: "currentColor",
      white: "#ffffff",
      // Warm-shifted neutrals. Pure grey next to clinical red reads cold and
      // slightly dead; a few degrees of warmth keeps the page calm.
      ink: {
        900: "#16150f", 800: "#2b2a22", 700: "#45443a",
        600: "#5f5d51", 500: "#83816f", 400: "#a9a795",
        300: "#cdcbba", 200: "#e4e2d5", 100: "#f2f1e9", 50: "#faf9f4",
      },
      // The three that matter. Contrast against white checked for AA at text
      // sizes; the badge pairs white text on these fills.
      critical: { DEFAULT: "#a2120b", soft: "#fdecea", edge: "#7d0e08" },
      urgent:   { DEFAULT: "#8a4b00", soft: "#fdf1e0", edge: "#6b3a00" },
      routine:  { DEFAULT: "#12592c", soft: "#e8f4ea", edge: "#0d4321" },
      // Interactive colour, deliberately distinct from all three urgencies so a
      // button is never mistaken for a status.
      //
      // Medical blue, not corporate navy. The previous #1b3a6b read as a
      // generic web button; the primary action on this tool is a clinical act
      // -- "seeing now" moves a patient -- and should look like one. Chosen at
      // 211deg, the furthest hue in the interface from CRITICAL (3deg), URGENT
      // (33deg) and ROUTINE (142deg), so it cannot be misread as a status even
      // by someone with a red-green deficiency.
      //
      // Verified: white on it 8.8:1, it on white 8.8:1, on action-soft 7.7:1,
      // and as the focus ring it holds 7.7-8.8:1 against every ground it can
      // land on including the tinted CRITICAL and URGENT row fills. Floors are
      // 4.5 for text and 3 for the ring; `contrast.test.ts` enforces both.
      action:   { DEFAULT: "#0b4a8f", soft: "#e8f1fb", edge: "#083a71" },
    },
    // A 1.25 modular scale from 14px. No 10px or 11px: this is read standing
    // up, at arm's length, on a screen that may be smeared.
    fontSize: {
      xs:   ["0.8125rem", { lineHeight: "1.15rem", letterSpacing: "0.01em" }],
      sm:   ["0.875rem",  { lineHeight: "1.25rem" }],
      base: ["1rem",      { lineHeight: "1.5rem" }],
      lg:   ["1.25rem",   { lineHeight: "1.75rem", letterSpacing: "-0.01em" }],
      xl:   ["1.5rem",    { lineHeight: "1.9rem",  letterSpacing: "-0.015em" }],
      "2xl":["1.875rem",  { lineHeight: "2.25rem", letterSpacing: "-0.02em" }],
      // Queue number: large enough to read across a desk.
      queue:["2.25rem",   { lineHeight: "2.4rem",  letterSpacing: "-0.03em" }],
      // FRONT DOOR ONLY. The one display size, for the single statement on the
      // sign-in panel. It is deliberately absent from every clinical surface:
      // inside the app the largest thing on screen is an urgency badge or a
      // queue number, and a 48px heading would outrank both.
      display:["3rem",    { lineHeight: "3.25rem", letterSpacing: "-0.035em" }],
    },
    // 4px base. Every gap in the UI is a multiple; nothing is eyeballed.
    //
    // THIS MAP IS REPLACED, NOT EXTENDED, and that is a trap worth naming: any
    // step missing here makes the corresponding utility silently produce NO
    // CSS. Tailwind does not warn; the class just does nothing.
    //
    // It had already happened. `11` was absent while `min-h-11` sat on every
    // button, nav link and input under a comment promising a 44px touch
    // target -- so the shipped stylesheet contained exactly one min-height
    // rule (`.min-h-screen`) and 25 of 26 controls measured 20-22px on a
    // phone. `32` and `24` were missing the same way, which left the symptom
    // textarea with no minimum height and collapsed the skeleton's badge.
    //
    // `src/__tests__/spacing-scale.test.ts` now fails if any spacing utility
    // used in the source has no step here, so this cannot recur silently.
    spacing: {
      0: "0", px: "1px",
      // Half steps. `UrgencyBadge size="sm"` carries px-2.5 / py-0.5 and both
      // were dead too -- that variant shipped with no padding at all. Found by
      // the scale test, not by looking.
      0.5: "0.125rem", 2.5: "0.625rem",
      1: "0.25rem", 2: "0.5rem", 3: "0.75rem", 4: "1rem",
      5: "1.25rem", 6: "1.5rem", 8: "2rem", 10: "2.5rem",
      // 44px. The WHO of touch targets: below this, a standing user with wet
      // or gloved hands mis-taps, and on this screen a mis-tap changes a
      // patient's queue status.
      11: "2.75rem",
      12: "3rem", 16: "4rem", 20: "5rem", 24: "6rem", 32: "8rem",
    },
    borderRadius: { none: "0", sm: "3px", DEFAULT: "5px", lg: "8px", full: "9999px" },
    extend: {
      fontFamily: {
        // System stack: no webfont round trip on a slow connection, and the
        // first paint carries the queue rather than a fallback.
        sans: ["ui-sans-serif", "system-ui", "-apple-system", "Segoe UI",
               "Roboto", "Helvetica Neue", "Arial", "sans-serif"],
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
      fontVariantNumeric: { tabular: "tabular-nums" },
      boxShadow: {
        // One elevation only. A tool with five shadow levels is decorating.
        card: "0 1px 2px rgba(22,21,15,0.06), 0 1px 3px rgba(22,21,15,0.04)",
        // WCAG 2.1 SC 1.4.11 needs 3:1 for a focus indicator. The previous
        // value, rgba(27,58,107,0.35), composites to #afbacb over white --
        // 1.96:1, and axe never flagged it because axe has no rule for
        // non-text contrast. Two tones: a white spacer so the ring reads on
        // the tinted CRITICAL/URGENT row fills, then solid action at 11.3:1.
        focus: "0 0 0 2px #ffffff, 0 0 0 4px #0b4a8f",
      },
      transitionDuration: { fast: "120ms" },
    },
  },
  plugins: [],
};
