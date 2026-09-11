import "@testing-library/jest-dom/vitest";
import { vi } from "vitest";

/** jsdom implements no `matchMedia`, and `useMediaQuery` depends on it.
 *
 * Defaulting every query to NOT matching means components under test render
 * their small-screen layout, which is the one that has to be right on the
 * device this tool runs on. A test that needs the dense layout sets this
 * explicitly -- see `setViewportMatches` below -- so the wide case is always
 * an opt-in rather than an accident of the default.
 */
let currentMatches = false;

export function setViewportMatches(matches: boolean): void {
  currentMatches = matches;
}

Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: vi.fn((query: string) => ({
    media: query,
    get matches() {
      return currentMatches;
    },
    onchange: null,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    addListener: vi.fn(),
    removeListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});
