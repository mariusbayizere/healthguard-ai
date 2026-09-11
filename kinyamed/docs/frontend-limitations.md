# Frontend limitations

Stated rather than solved. Each entry says what the behaviour actually is, what
it costs the person in front of the screen, and what fixing it would take —
because a limitation a reader can act on is worth more than one that is merely
confessed.

---

## 1. The client requires a live connection to the API. There is no offline mode.

**This is the significant one, and it is a real constraint on the deployment
setting.** A health centre with intermittent connectivity is the environment
this system is intended for, and the client does not survive it.

### What actually happens

The behaviour differs by moment, and the differences matter, so they are not
collapsed into "it breaks":

| Moment | Behaviour today |
|---|---|
| Connection drops **mid-session** | The queue **keeps showing the last rows it fetched** and displays an offline banner with a Retry action. It does not blank. |
| **Reload** while offline | The app does not load at all. There is no service worker, so the HTML and JS bundle are fetched from the network like anything else. |
| **First load** of a view while offline | Blank view under an offline banner. There is nothing cached to show. |
| **Submitting** a triage while offline | The request fails, the banner names the network as the cause, and the typed symptoms stay in the form. Nothing is queued for later. |
| **Doctor actions** (assign, status change) while offline | Same: the request fails, nothing is stored, nothing retries. |

Two of those deserve enlarging.

**Stale rows do not announce their age.** TanStack Query preserves the last
successful `data` when a refetch errors (`query.js`: the error branch spreads
prior state and never resets `data`), so a nurse looking at the board during an
outage sees a queue that is still legible and still wrong. The banner says the
connection failed; the rows do not say *"as of four minutes ago"*. A patient who
arrived during the outage is absent from a board that looks current. Of
everything on this page, this is the failure most likely to reach a patient,
because it is the one that does not look like a failure.

**Classification is server-side, unconditionally.** The model is a 449 MB
transformer served by the API. There is no client-side inference and there is no
plausible path to one at that size on the hardware a health centre has. So even
a perfect offline shell could not triage; it could only capture symptoms for
later. Any offline story here is a *capture-and-sync* story, not a
*keep-working* story.

### What is not the problem

Authentication survives an outage: the token is in `localStorage`, so a reload
does not force a re-login once the network returns. The polling interval is not
the issue either — at 5 s a reconnect recovers the board within seconds without
any intervention.

### What fixing it would take

Not built, and deliberately so — the cost is real work, not a flag:

1. **Age the data.** Render `dataUpdatedAt` as a visible "last updated HH:MM"
   whenever the query is in an error state, so stale rows are readable as
   stale. Roughly an hour, and it removes the sharpest edge above.
2. **Cache the shell.** A service worker (Workbox via `vite-plugin-pwa`)
   precaching the built assets, so a reload offline reaches a working app
   rather than a browser error page.
3. **Persist the cache.** `@tanstack/query-persist-client` writing the queue to
   IndexedDB, so the shell has rows to render at first paint.
4. **Queue the writes.** An outbox for triage submissions and doctor actions,
   replayed on reconnect. This is the expensive one and the one with clinical
   consequences: a triage submitted offline and synced twenty minutes later
   enters a queue whose ordering assumed it was not there, and two devices
   replaying independently can assign the same patient twice. It needs a
   server-side idempotency key and a conflict rule, neither of which exists.

Item 1 is cheap and item 4 is a design problem, not a sprint. Nothing here is
started.

### Why it is stated instead of built

Building a plausible offline mode in two days would produce something that
looks like it works — a cached board, a submit button that accepts input — and
whose failure mode is a patient's triage sitting unsynced in a browser nobody
reopens. A documented gap makes the deployment decision visible to whoever makes
it. A half-built one hides it inside the product.

---

## 2. No push, so the board is up to 5 seconds stale by design

The API has no websocket, so the queue polls (`hooks.ts`, `QUEUE_POLL_MS`). Five
seconds was chosen against the clinical read — a nurse glancing up expects a
current board — and it is a per-client poll: 12 requests a minute per open tab
against an endpoint returning tens of rows. That is fine for one clinic and is
not a design that scales to many, and the fix is server push rather than a
shorter interval.

## 3. One viewport family is untested on real hardware

Layouts were checked at 360, 414, 768 and 1024 px in a browser. No test ran on a
physical low-end Android device, which is the actual target: touch accuracy,
font rendering and scroll behaviour under a real finger are not verified.

## 4. No end-to-end test covers the browser

Component tests (Vitest + Testing Library) cover the queue table's rendering
guarantees. Nothing drives a real browser through login → triage → queue, so
routing, token expiry mid-session and the mutation cache write are covered by
reading, not by running.

## 5. Accessibility is reasoned, not audited

Urgency is carried in text as well as colour, targets meet 44 px, and states
are distinct. No screen reader session has been run and no automated axe pass
is wired into CI, so the accessibility claim is a design intention with one
test behind it, not an audit result.
