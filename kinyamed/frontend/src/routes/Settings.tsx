import { useState, type FormEvent } from "react";
import {
  useChangePassword,
  useLogoutEverywhere,
  useMe,
  useSessions,
  useUpdateProfile,
} from "@/api/hooks";
import { Alert, Button, Card, Field, inputClass } from "@/components/ui";
import { Skeleton } from "@/components/ui";

/** Account settings. Almost all of this already existed on the server.
 *
 * `/auth/me`, `/auth/change-password` and `/auth/sessions` were built and
 * nothing in the frontend had ever called them. The session list is the
 * reason this screen is worth having: this tool runs on devices passed
 * between staff during a shift, and the ability to see every place your
 * account is still signed in -- and to end them -- is the single most useful
 * security control available to someone who has just handed a tablet back.
 */

function when(iso: string): string {
  // Fixed locale and an explicit 24-hour clock: a clinic reads times off a
  // wall, and "7:45" without a marker is ambiguous on a handover.
  return new Date(iso).toLocaleString("en-GB", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

/** A user agent is not a device name, and pretending otherwise misleads.
 *  This shortens it to something recognisable without inventing certainty. */
function device(agent: string | null): string {
  if (!agent) return "Unknown device";
  const match = /(Android|iPhone|iPad|Windows|Macintosh|Linux)/.exec(agent);
  return match ? match[1]! : agent.slice(0, 40);
}

/** The profile, editable.
 *
 * It was a read-only definition list because no endpoint existed to change
 * anything; `PATCH /auth/me` now takes the name. Only the name: role, active
 * state and the patient/doctor links decide what the account can REACH, and an
 * account that can grant itself a role is not an account.
 */
function Profile({ user }: { user: NonNullable<ReturnType<typeof useMe>["data"]> }) {
  const update = useUpdateProfile();
  const [name, setName] = useState(user.full_name);
  const dirty = name.trim() !== user.full_name;

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    update.mutate({ full_name: name.trim() });
  }

  return (
    <Card title="Account">
      <form onSubmit={onSubmit} className="space-y-5">
        {update.isError && <Alert>{(update.error as Error).message}</Alert>}
        {update.isSuccess && !dirty && <Alert kind="ok">Name updated.</Alert>}

        <div className="grid gap-x-8 gap-y-5 sm:grid-cols-2">
          <Field label="Name">
            <input
              className={inputClass}
              autoComplete="name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              minLength={2}
            />
          </Field>

          {/* The rest is shown, not edited. Each is read-only for a reason
              worth reading, so they are not simply omitted. */}
          <div>
            <span className="block text-sm font-semibold text-ink-800">Email</span>
            <p className="mt-1 min-h-11 text-base text-ink-900">{user.email}</p>
            <p className="text-xs text-ink-600">
              Changing this changes how you sign in — ask an administrator.
            </p>
          </div>
          <div>
            <span className="block text-sm font-semibold text-ink-800">Role</span>
            <p className="mt-1 text-base text-ink-900">{user.role.toLowerCase()}</p>
            <p className="text-xs text-ink-600">
              Decides what you can open. Only an administrator can change it.
            </p>
          </div>
          <div>
            <span className="block text-sm font-semibold text-ink-800">
              Last signed in
            </span>
            <p className="tnum mt-1 text-base text-ink-900">
              {user.last_login_at ? when(user.last_login_at) : "—"}
            </p>
          </div>
        </div>

        <Button type="submit" disabled={!dirty || update.isPending}>
          {update.isPending ? "Saving…" : "Save name"}
        </Button>
      </form>
    </Card>
  );
}

function ChangePassword() {
  const change = useChangePassword();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    change.mutate(
      { current_password: current, new_password: next },
      {
        onSuccess: () => {
          setCurrent("");
          setNext("");
        },
      },
    );
  }

  return (
    <Card title="Password">
      <form onSubmit={onSubmit} className="max-w-sm space-y-5">
        {change.isError && <Alert>{(change.error as Error).message}</Alert>}
        {change.isSuccess && <Alert kind="ok">Password changed.</Alert>}

        <Field label="Current password">
          <input
            className={inputClass}
            type="password"
            autoComplete="current-password"
            value={current}
            onChange={(e) => setCurrent(e.target.value)}
            required
          />
        </Field>
        <Field
          label="New password"
          hint="Changing this signs your account out of other devices."
        >
          <input
            className={inputClass}
            type="password"
            autoComplete="new-password"
            value={next}
            onChange={(e) => setNext(e.target.value)}
            required
          />
        </Field>
        <Button type="submit" disabled={change.isPending}>
          {change.isPending ? "Changing…" : "Change password"}
        </Button>
      </form>
    </Card>
  );
}

function Sessions() {
  const sessions = useSessions();
  const signOutAll = useLogoutEverywhere();

  return (
    <Card
      title="Where you are signed in"
      actions={
        <span className="text-xs text-ink-600">
          {sessions.data ? `${sessions.data.length} active` : ""}
        </span>
      }
    >
      {sessions.isLoading ? (
        <Skeleton rows={2} />
      ) : sessions.isError ? (
        <Alert>{(sessions.error as Error).message}</Alert>
      ) : (sessions.data ?? []).length === 0 ? (
        <p className="text-sm text-ink-600">No other active sessions.</p>
      ) : (
        <ul className="divide-y divide-ink-200">
          {(sessions.data ?? []).map((s) => (
            <li
              key={s.jti}
              className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-1 py-3 first:pt-0 last:pb-0"
            >
              <span className="text-sm font-medium text-ink-900">
                {device(s.user_agent)}
              </span>
              <span className="tnum text-xs text-ink-600">
                started {when(s.created_at)} · expires {when(s.expires_at)}
              </span>
            </li>
          ))}
        </ul>
      )}
      <div className="mt-6 border-t border-ink-200 pt-5">
        {signOutAll.isError && (
          <Alert>{(signOutAll.error as Error).message}</Alert>
        )}
        <p className="text-sm leading-relaxed text-ink-700">
          Signing out everywhere ends every session on every device, including
          this one. Use it if a device has been lost or handed on.
        </p>
        <Button
          variant="danger"
          className="mt-4"
          disabled={signOutAll.isPending}
          onClick={() =>
            signOutAll.mutate(undefined, {
              onSuccess: () => location.assign("/login"),
            })
          }
        >
          {signOutAll.isPending ? "Signing out…" : "Sign out everywhere"}
        </Button>
      </div>
    </Card>
  );
}

export function Settings() {
  const me = useMe();

  if (me.isLoading) return <Skeleton rows={4} />;
  if (me.isError) return <Alert>{(me.error as Error).message}</Alert>;

  const user = me.data;

  return (
    <div className="space-y-6">
      {user && <Profile user={user} />}

      <ChangePassword />
      <Sessions />
    </div>
  );
}
