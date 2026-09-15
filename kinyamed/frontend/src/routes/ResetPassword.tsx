import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { useRequestPasswordReset } from "@/api/hooks";
import { Alert, Button, Card, Field, inputClass } from "@/components/ui";

/** Step one of two: ask for a reset link.
 *
 * NO ACCOUNT ENUMERATION ON SCREEN EITHER. The server answers identically for
 * a known and an unknown address, and so does this: the success state says
 * "if that address has an account", never "we've sent you an email". A screen
 * that confirms the address exists undoes the server's careful silence, and
 * for this system the account list is the staff of a named health centre.
 *
 * The code arrives by SMS to the number on the account. Staff accounts have no
 * patient chart and therefore no number, which is why the success state names
 * the administrator as the fallback rather than pretending a message is on its
 * way to everyone.
 */
export function ResetPassword() {
  const requestReset = useRequestPasswordReset();
  const [email, setEmail] = useState("");

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    requestReset.mutate({ email });
  }

  return (
    <main className="mx-auto w-full max-w-md px-5 py-16 sm:px-0">
      <h1 className="text-2xl font-semibold tracking-tight text-ink-900">
        Reset your password
      </h1>
      <p className="mt-2 text-sm leading-relaxed text-ink-600">
        We&rsquo;ll send a code to the phone number on your account.
      </p>

      <div className="mt-8">
        {requestReset.isSuccess ? (
          <Card>
            <div className="space-y-4">
              <Alert kind="ok">
                If that address has an account, a code is on its way by SMS.
              </Alert>
              <p className="text-sm leading-relaxed text-ink-700">
                The code lasts 30 minutes. Enter it on the next screen together
                with your new password.
              </p>
              <Button
                className="w-full"
                onClick={() => location.assign("/new-password")}
              >
                I have a code
              </Button>
              <p className="text-sm leading-relaxed text-ink-600">
                Nothing arrived? Staff accounts do not always have a phone
                number on file — an administrator can set your password
                directly.
              </p>
            </div>
          </Card>
        ) : (
          <Card>
            <form onSubmit={onSubmit} className="space-y-5">
              {requestReset.isError && (
                <Alert>{(requestReset.error as Error).message}</Alert>
              )}
              <Field label="Email" hint="The address your account was created with.">
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
              <Button
                type="submit"
                disabled={requestReset.isPending}
                className="w-full"
              >
                {requestReset.isPending ? "Sending…" : "Send a reset code"}
              </Button>
            </form>
          </Card>
        )}
      </div>

      <div className="mt-8 flex flex-wrap gap-x-6 gap-y-2 text-sm">
        <Link className="inline-flex min-h-11 items-center text-sm font-medium text-action underline" to="/login">
          Back to sign in
        </Link>
        <Link className="inline-flex min-h-11 items-center text-sm font-medium text-action underline" to="/new-password">
          I already have a code
        </Link>
      </div>
    </main>
  );
}
