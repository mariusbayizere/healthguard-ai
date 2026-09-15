# Roadmap — deferred, not missing

Work that is deliberately not built, with the reason and what unblocks it. The
distinction matters: an item here has been decided about. An item absent from
both the code and this file has been forgotten.

## Deferred

### Google OAuth 2.0 sign-in
**Status:** deferred 2026-09-11. Not started, and the button has been removed.

A "Continue with Google" control shipped briefly on the sign-in screen with a
notice beneath it saying it was not connected. That is a dead control on the
primary screen of a clinical tool, and it was removed rather than left to teach
staff that buttons here may be decorative.

**What it needs:** a Google Cloud project and OAuth client ID, a client secret
held server-side, a registered redirect URI per environment, a consent screen,
and three backend endpoints (start, callback, token exchange) using the
authorization-code flow with PKCE. The token must land in an httpOnly cookie
rather than `localStorage` — see the note in `frontend/src/lib/auth.ts`.

**Design decision already taken:** when it returns it sits BELOW the email and
password form, not above it. Password stays primary because it is the path that
works offline and on a device passed between staff, and because federated
sign-in on a shared terminal leaves an account signed in at the browser layer,
outliving this application's own sign-out.

**Open question first:** Rwanda's Law 058/2021 requires personal data to be
stored in Rwanda or covered by an NCSA certificate for offshore storage.
Whether routing staff identity through Google is compatible with that is a
question for whoever owns the deployment, and it should be answered before the
client ID is created rather than after.

### Ending a single session
`/auth/logout-all` revokes every session for an account; there is no endpoint to
revoke one. Account settings therefore offers "sign out everywhere" and not a
per-row control. Adding one means an endpoint keyed on the refresh token's
`jti`, which the session list already returns.

### Email delivery
Password reset codes go by SMS, reusing the Africa's Talking integration behind
its feature flag. There is no email sender, so an account with no phone number
on file — which is every staff account, since only patients have a chart —
cannot self-serve a reset and needs an administrator. Email would close that.
