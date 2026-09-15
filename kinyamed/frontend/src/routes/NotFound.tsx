import { Link } from "react-router-dom";
import { Button } from "@/components/ui";

/** Any URL the router does not know.
 *
 * Without this route an unknown path rendered a COMPLETELY BLANK PAGE: no
 * heading, no navigation, no way back. A mistyped URL, a stale bookmark or a
 * link from an old SMS all landed on nothing at all, which is
 * indistinguishable from the application being down.
 */
export function NotFound() {
  return (
    <main className="mx-auto w-full max-w-md px-5 py-20 text-center sm:px-0">
      <p className="text-xs font-semibold uppercase tracking-widest text-ink-600">
        Page not found
      </p>
      <h1 className="mt-4 text-2xl font-semibold tracking-tight text-ink-900">
        That page does not exist
      </h1>
      <p className="mt-3 text-sm leading-relaxed text-ink-700">
        The address may be mistyped, or the page may have moved.
      </p>
      <div className="mt-8 flex flex-col items-center gap-3">
        <Link to="/">
          <Button>Go to triage</Button>
        </Link>
        <Link className="inline-flex min-h-11 items-center text-sm font-medium text-action underline" to="/login">
          Sign in
        </Link>
      </div>
    </main>
  );
}
