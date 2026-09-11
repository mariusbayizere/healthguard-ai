import { useEffect, useState } from "react";

/** Subscribe to a CSS media query from React.
 *
 * This exists so a layout choice can be made in JAVASCRIPT rather than by
 * rendering both layouts and hiding one with CSS.
 *
 * The difference is not cosmetic on the device this tool targets. Hiding with
 * `display:none` still builds every node: a 40-patient queue meant 40 cards
 * AND 40 table rows in the DOM, roughly 500 elements rendered and reconciled
 * on every one of the 5-second polls, on a low-end Android phone, so that half
 * could be painted. Choosing means one layout exists at a time.
 *
 * `useState` + `useEffect` rather than `useSyncExternalStore` so the first
 * render is deterministic: it returns `false` before the effect runs, which
 * means the CARD layout paints first. That is the right default -- cards are
 * legible at every width, the table is not legible below its breakpoint, so a
 * momentary wrong guess degrades to "correct but less dense" rather than to a
 * table overflowing a phone.
 */
export function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState(false);

  useEffect(() => {
    // Absent in jsdom without a polyfill, and in any non-browser renderer.
    // Falling back to `false` keeps the card layout, per the note above.
    if (typeof window === "undefined" || !window.matchMedia) return;

    const list = window.matchMedia(query);
    setMatches(list.matches);

    const onChange = (event: MediaQueryListEvent) => setMatches(event.matches);
    // `addListener` is the deprecated form, still the only one on older
    // WebKit -- which is exactly the browser a cheap Android ships.
    if (list.addEventListener) {
      list.addEventListener("change", onChange);
      return () => list.removeEventListener("change", onChange);
    }
    list.addListener(onChange);
    return () => list.removeListener(onChange);
  }, [query]);

  return matches;
}
