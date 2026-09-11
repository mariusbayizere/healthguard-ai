import { useState, type FormEvent } from "react";
import { useLogin } from "@/api/hooks";
import { Alert, Button, Card, Field, inputClass } from "@/components/ui";

export function Login() {
  const login = useLogin();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    login.mutate({ username, password }, { onSuccess: () => location.assign("/") });
  }

  return (
    <div className="mx-auto max-w-sm py-16">
      <h1 className="mb-6 text-2xl font-semibold tracking-tight">KinyaMed</h1>
      <Card title="Sign in">
        <form onSubmit={onSubmit} className="space-y-4">
          {login.isError && <Alert>{(login.error as Error).message}</Alert>}
          <Field label="Username">
            <input
              className={inputClass}
              autoComplete="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
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
      </Card>
    </div>
  );
}
