import { useState, type FormEvent } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useConfirmPasswordReset, useValidateResetToken } from "@/api/hooks";
import { Alert, Button, Card, Field, Skeleton, inputClass } from "@/components/ui";

/** Step two of two: redeem the code and set a new password.
 *
 * THE TOKEN IS CHECKED BEFORE THE FORM IS SHOWN. `/auth/password-reset/validate`
 * says whether a code would be accepted without spending it, so an expired
 * link says so immediately rather than after someone has typed a password
 * twice and pressed submit. That one round trip is the difference between an
 * error state and an insult.
 *
 * THE CONFIRMATION FIELD IS CHECKED HERE, NOT BY THE SERVER. The server takes
 * one password; a mistyped new password that both parties accept locks the
 * user out of the account they were in the middle of recovering, so the match
 * is enforced before anything is sent.
 *
 * The code may arrive in the URL (`?token=`) or be typed from an SMS. Both
 * paths land on the same form.
 */
export function NewPassword() {
  const [params] = useSearchParams();
  const [token, setToken] = useState(params.get("token") ?? "");
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [mismatch, setMismatch] = useState(false);

  const validation = useValidateResetToken(token);
  const confirm = useConfirmPasswordReset();

  const tokenRejected = validation.data?.valid === false;

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (password !== confirmation) {
      setMismatch(true);
      return;
    }
    setMismatch(false);
    confirm.mutate({ token, new_password: password });
  }

  // ── Done ────────────────────────────────────────────────────────────────
  if (confirm.isSuccess) {
    return (
      <main className="mx-auto w-full max-w-md px-5 py-16 sm:px-0">
        <h1 className="text-2xl font-semibold tracking-tight text-ink-900">
          Password changed
        </h1>
        <div className="mt-8">
          <Card>
            <div className="space-y-4">
              <Alert kind="ok">You can sign in with your new password.</Alert>
              {/* Stated because it is surprising and because it is a safety
                  feature: a reset usually follows a lost device. */}
              <p className="text-sm leading-relaxed text-ink-700">
                Every other device signed into this account has been signed out.
              </p>
              <Button className="w-full" onClick={() => location.assign("/login")}>
                Go to sign in
              </Button>
            </div>
          </Card>
        </div>
      </main>
    );
  }

  return (
    <main className="mx-auto w-full max-w-md px-5 py-16 sm:px-0">
      <h1 className="text-2xl font-semibold tracking-tight text-ink-900">
        Set a new password
      </h1>
      <p className="mt-2 text-sm leading-relaxed text-ink-600">
        Enter the code from the SMS, then choose a new password.
      </p>

      <div className="mt-8">
        <Card>
          <form onSubmit={onSubmit} className="space-y-5">
            {/* Every failure mode gets its own sentence. "Something went
                wrong" would leave the reader unable to tell an expired code
                from a typo from an outage. */}
            {tokenRejected && (
              <Alert>
                That code is not valid, or it has expired. Codes last 30
                minutes — ask for a new one.
              </Alert>
            )}
            {mismatch && <Alert>The two passwords do not match.</Alert>}
            {confirm.isError && <Alert>{(confirm.error as Error).message}</Alert>}

            <Field label="Reset code" hint="From the SMS sent to your phone.">
              <input
                className={inputClass}
                value={token}
                onChange={(e) => setToken(e.target.value.trim())}
                autoCapitalize="none"
                spellCheck={false}
                required
              />
            </Field>

            {validation.isFetching && token.length > 0 && (
              <div aria-live="polite">
                <Skeleton rows={1} />
              </div>
            )}

            <Field label="New password">
              <input
                className={inputClass}
                type="password"
                autoComplete="new-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </Field>

            <Field label="Confirm new password">
              <input
                className={inputClass}
                type="password"
                autoComplete="new-password"
                value={confirmation}
                onChange={(e) => setConfirmation(e.target.value)}
                required
              />
            </Field>

            <Button
              type="submit"
              // Disabled only for a code the server has ALREADY rejected or
              // while a request is in flight. Not disabled on an empty form:
              // a submit that does nothing with no explanation is the control
              // this screen replaced.
              disabled={confirm.isPending || tokenRejected}
              className="w-full"
            >
              {confirm.isPending ? "Changing…" : "Change password"}
            </Button>
          </form>
        </Card>
      </div>

      <div className="mt-8 flex flex-wrap gap-x-6 gap-y-2 text-sm">
        <Link className="inline-flex min-h-11 items-center text-sm font-medium text-action underline" to="/reset-password">
          Send a new code
        </Link>
        <Link className="inline-flex min-h-11 items-center text-sm font-medium text-action underline" to="/login">
          Back to sign in
        </Link>
      </div>
    </main>
  );
}
