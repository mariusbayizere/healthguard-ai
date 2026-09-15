import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { useRegister } from "@/api/hooks";
import { Alert, Button, Card, Field, inputClass } from "@/components/ui";

/** Patient registration — and it says so, because the endpoint behind it is
 *  not a general sign-up.
 *
 * `/auth/register` creates a login AND a patient chart together. Its own
 * docstring is explicit that staff accounts are created by an administrator
 * and never here. A screen labelled "Create your account" on a tool whose
 * other three screens are for nurses would therefore be a trap: a nurse who
 * used it would get a PATIENT role, silently lack every permission the job
 * needs, and have a patient chart created in their name.
 *
 * So the heading names who this is for, and the notice names who it is not.
 */
export function SignUp() {
  const register = useRegister();
  const [form, setForm] = useState({
    full_name: "",
    email: "",
    phone: "",
    password: "",
  });

  const set = (key: keyof typeof form) => (e: { target: { value: string } }) =>
    setForm((f) => ({ ...f, [key]: e.target.value }));

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    register.mutate(form, { onSuccess: () => location.assign("/") });
  }

  return (
    <main className="mx-auto w-full max-w-md px-5 py-12 sm:px-0">
      <h1 className="text-xl font-semibold tracking-tight text-ink-900">
        Register a patient
      </h1>
      <p className="mt-1 text-sm text-ink-600">
        Creates a patient record and a login for it.
      </p>

      <div className="mt-6">
        <Alert kind="offline">
          Staff accounts are not created here. A nurse, doctor or administrator
          account is issued by an administrator.
        </Alert>
      </div>

      <div className="mt-6">
        <Card>
          <form onSubmit={onSubmit} className="space-y-5">
            {register.isError && (
              <Alert>{(register.error as Error).message}</Alert>
            )}

            <Field label="Full name">
              <input
                className={inputClass}
                autoComplete="name"
                value={form.full_name}
                onChange={set("full_name")}
                required
                minLength={2}
              />
            </Field>

            <Field label="Email">
              <input
                className={inputClass}
                type="email"
                autoComplete="email"
                autoCapitalize="none"
                spellCheck={false}
                value={form.email}
                onChange={set("email")}
                required
              />
            </Field>

            <Field
              label="Phone"
              hint="Used to send the urgency and queue number by SMS, where that is switched on."
            >
              <input
                className={inputClass}
                type="tel"
                autoComplete="tel"
                inputMode="tel"
                value={form.phone}
                onChange={set("phone")}
                required
                maxLength={20}
              />
            </Field>

            <Field label="Password">
              <input
                className={inputClass}
                type="password"
                autoComplete="new-password"
                value={form.password}
                onChange={set("password")}
                required
              />
            </Field>

            <Button
              type="submit"
              disabled={register.isPending}
              className="w-full"
            >
              {register.isPending ? "Creating…" : "Create patient record"}
            </Button>
          </form>
        </Card>
      </div>

      {/* A WAY BACK. /register and /reset-password were both dead ends: once
          on either, nothing linked to sign-in and the only exit was the
          browser's back button. */}
      <div className="mt-8 text-sm">
        <Link className="inline-flex min-h-11 items-center text-sm font-medium text-action underline" to="/login">
          Back to sign in
        </Link>
      </div>

      <p className="mt-6 text-xs leading-relaxed text-ink-600">
        Age, gender and location are accepted by the API and are not asked for
        here: none of them change the triage result, and a form that collects
        what it does not use is a form people abandon.
      </p>
    </main>
  );
}
