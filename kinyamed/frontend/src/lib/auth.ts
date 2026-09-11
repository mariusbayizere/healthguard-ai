/** Token storage.
 *
 * localStorage, with the tradeoff stated rather than hidden: it is readable by
 * any script on this origin, so an XSS becomes a token theft. The alternative
 * -- an httpOnly cookie -- is the right answer for production and requires the
 * API to set it, which it does not today. Recorded here so the choice is
 * visible to whoever hardens this rather than discovered during a review.
 */
const KEY = "kinyamed.token";

export const auth = {
  get: (): string | null => {
    try { return localStorage.getItem(KEY); } catch { return null; }
  },
  set: (token: string): void => {
    try { localStorage.setItem(KEY, token); } catch { /* private mode */ }
  },
  clear: (): void => {
    try { localStorage.removeItem(KEY); } catch { /* private mode */ }
  },
  isAuthenticated: (): boolean => Boolean(auth.get()),
};
