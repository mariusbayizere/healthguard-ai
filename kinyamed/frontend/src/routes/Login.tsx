import { useState, type FormEvent } from "react";
import { useLogin } from "@/api/hooks";
import { Alert, Button, Field, inputClass } from "@/components/ui";

/** Sign-in. The front door, and the only screen allowed to explain itself.
 *
 * OSCAR'S PRINCIPLE, which is the one this follows: things further from the
 * front door may flex away from the core identity; things inside the house
 * stay true to it. So this screen carries a dark panel and a display-sized
 * statement, and the queue behind it carries none of that -- there, urgency is
 * still the only saturated colour and the interface still recedes.
 *
 * WHY A STATEMENT AND NOT AN INSTRUMENT READOUT. A dense status panel is the
 * right answer for someone who uses this daily and the wrong one for someone
 * meeting it for the first time. Doctolib and Oscar both put a plain sentence
 * about what the product is next to the form, and that is what an audience who
 * has never seen this system needs: what it does, in whose words, and what it
 * is not cleared to do.
 *
 * THE PANEL IS TYPOGRAPHIC ONLY, and that was measured rather than chosen.
 * A legend of the three urgency colours was the obvious thing to put here;
 * on ink-900 they land at 2.17-2.69:1 against the 3:1 floor for non-text
 * contrast, so they would have been decoration a colour-blind or
 * bright-light reader could not resolve. Type on this ground runs 4.65:1
 * (ink-500) to 18.3:1 (white), so the panel says it in words.
 *
 * NO FEDERATED SIGN-IN, AND THAT IS RECORDED RATHER THAN FORGOTTEN. A
 * "Continue with Google" button shipped here briefly with a notice under it
 * saying it did not work. A dead control on the primary screen is worse than
 * no control: it costs a tap, teaches that buttons here may be decorative, and
 * puts build state in front of a clinician.
 *
 * It is DEFERRED, not abandoned -- see docs/roadmap.md. Wiring it needs a
 * Google client ID, a secret on the server, a registered redirect URI and a
 * consent screen, none of which exist yet. When they do, the button returns
 * BELOW the password form: a shared health-centre terminal is the documented
 * worst case for federated sign-in, because "Continue with Google" leaves an
 * account signed in at the browser layer, outliving this app's own sign-out.
 */

export function Login() {
  const login = useLogin();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    login.mutate({ email, password }, { onSuccess: () => location.assign("/") });
  }

  return (
    <div className="min-h-screen lg:grid lg:grid-cols-[1fr_1.1fr]">
      {/* ── The form. First in the DOM so it is first for a screen reader and
             first on a phone; the statement panel follows rather than making
             someone scroll past marketing to reach the thing they came for. */}
      {/* <main>, not <div>. This route renders OUTSIDE Layout, so it does not
             inherit Layout's landmarks -- axe flagged landmark-one-main and
             content outside any region at all three widths. A screen-reader
             user navigating by landmark had nothing to jump to on the one
             screen where they cannot proceed without finding the form. The
             <aside> below is already a complementary landmark. */}
      <main className="flex min-h-screen flex-col justify-center px-5 py-12 sm:px-10 lg:px-16">
        <div className="mx-auto w-full max-w-sm">
          <h1 className="text-xl font-semibold tracking-tight text-ink-900">
            KinyaMed
          </h1>
          <p className="mt-1 text-sm text-ink-600">Sign in to continue</p>

          <form onSubmit={onSubmit} className="mt-8 space-y-5">
            {login.isError && <Alert>{(login.error as Error).message}</Alert>}

            <Field label="Email">
              <input
                className={inputClass}
                type="email"
                autoComplete="email"
                autoCapitalize="none"
                spellCheck={false}
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </Field>

            <Field label="Password">
              <input
                className={inputClass}
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </Field>

            <Button type="submit" disabled={login.isPending} className="w-full">
              {login.isPending ? "Signing in…" : "Sign in"}
            </Button>
          </form>

          <div className="mt-10 flex flex-col gap-3 border-t border-ink-200 pt-6">
            <a
              className="inline-flex min-h-11 items-center text-sm font-medium text-action underline"
              href="/reset-password"
            >
              Trouble signing in?
            </a>
            {/* THE SIGN-UP LINK. /register existed as a route and nothing in
                the application linked to it -- the only way to reach patient
                registration was to type the URL. */}
            <p className="flex min-h-11 flex-wrap items-center gap-x-1 text-sm text-ink-700">
              Registering a patient?{" "}
              <a
                className="font-medium text-action underline"
                href="/register"
              >
                Create a patient record
              </a>
            </p>
          </div>

          {/* Below `lg` the statement panel is display:none, so without this
              the purpose AND the safety limit would be absent from the sign-in
              screen on every phone and tablet -- the devices this actually
              runs on. The limit is not a desktop-only disclosure. Condensed,
              not omitted. */}
          <div className="mt-10 border-t border-ink-300 pt-6 lg:hidden">
            <p className="text-sm leading-relaxed text-ink-700">
              KinyaMed orders a waiting room by clinical urgency from what the
              patient actually said, in Kinyarwanda, English, French or
              Kiswahili.
            </p>
            <p className="mt-3 text-xs leading-relaxed text-ink-600">
              Decision support only. The model does not currently meet its
              acceptance threshold for critical recall and is not cleared for
              clinical use.
            </p>
          </div>
        </div>
      </main>

      {/* ── The statement. Hidden below `lg`, where a condensed version of the
             same two facts sits under the form instead: on a phone this panel
             would be a scroll between a nurse and their shift, but its CONTENT
             must not disappear with it.
             Not `aria-hidden` at `lg` and up -- it explains what the system is,
             and a screen-reader user reaches it after the form rather than
             having to wade through it first. */}
      <aside className="hidden bg-ink-900 px-16 py-20 lg:flex lg:flex-col lg:justify-center">
        <div className="max-w-xl">
          <p className="text-xs font-semibold uppercase tracking-widest text-ink-400">
            Clinical triage
          </p>

          {/* The one display-sized line. Tight tracking and a hanging measure:
              this is the only place in the product typography is allowed to be
              expressive rather than functional. */}
          <h2 className="mt-6 text-display font-semibold text-white">
            Triage in the patient&rsquo;s own words.
          </h2>

          <p className="mt-6 text-base leading-relaxed text-ink-300">
            KinyaMed orders a waiting room by clinical urgency from what the
            patient actually said — not from a translated summary. It reads
            Kinyarwanda, English, French and Kiswahili, and it puts the most
            urgent person first.
          </p>

          {/* The honest line, and it stays on the front door on purpose. Every
              other product's sign-in screen makes a claim; this one states the
              limit before anyone signs in. It is also simply true. */}
          <p className="mt-10 border-t border-ink-700 pt-6 text-sm leading-relaxed text-ink-400">
            Decision support only. The model does not currently meet its
            acceptance threshold for critical recall and is not cleared for
            clinical use. Clinical judgement overrides every suggestion it
            makes.
          </p>
        </div>
      </aside>
    </div>
  );
}
