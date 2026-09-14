/** The single place this app talks to the API.
 *
 * Every request goes through `request()`. That is what makes 401 handling,
 * error surfacing and the base URL one decision each instead of one per call
 * site.
 */
import { auth } from "@/lib/auth";

export const API_BASE =
  (import.meta.env["VITE_API_BASE"] as string | undefined) ??
  "http://localhost:8000/api/v1";

/** An API failure that carries the server's own message.
 *
 * A generic "something went wrong" hides the one detail a clinic needs when
 * telephoning whoever supports this. FastAPI's `detail` is preserved verbatim.
 */
export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
    readonly detail?: unknown,
    /** The API's machine-readable `error.code`, e.g. TRIAGE_MODEL_UNAVAILABLE. */
    readonly code?: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

/** The API's own error envelope: `{"error": {"code", "message", "details"}}`.
 *
 * Every domain error the backend raises uses it. This client used to read only
 * FastAPI's bare `detail`, so every such error -- including the 503 telling a
 * nurse to triage manually -- rendered as "Request failed (503)."
 */
function envelope(body: unknown): { code?: string; message?: string } {
  if (!body || typeof body !== "object" || !("error" in body)) return {};
  const error = (body as { error: unknown }).error;
  if (!error || typeof error !== "object") return {};
  const { code, message } = error as { code?: unknown; message?: unknown };
  return {
    ...(typeof code === "string" ? { code } : {}),
    ...(typeof message === "string" && message ? { message } : {}),
  };
}

function describe(status: number, body: unknown): string {
  const fromEnvelope = envelope(body).message;
  if (fromEnvelope) return fromEnvelope;
  if (body && typeof body === "object" && "detail" in body) {
    const d = (body as { detail: unknown }).detail;
    if (typeof d === "string") return d;
    // 422 arrives as a list of per-field errors; name the fields rather than
    // dumping the structure at a nurse.
    if (Array.isArray(d)) {
      const fields = d
        .map((e) => (e && typeof e === "object" && "loc" in e
          ? String((e as { loc: unknown[] }).loc.at(-1)) : null))
        .filter(Boolean);
      if (fields.length) return `Check these fields: ${fields.join(", ")}`;
    }
  }
  if (status === 0) return "Cannot reach the API. Is the backend running?";
  return `Request failed (${status}).`;
}

export async function request<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const token = auth.get();
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...init.headers,
      },
    });
  } catch (cause) {
    // A network failure and an API error are different problems with different
    // fixes, and collapsing them wastes the reader's time.
    throw new ApiError(0, describe(0, null), cause);
  }

  if (response.status === 401) {
    auth.clear();
    throw new ApiError(401, "Session expired. Sign in again.");
  }

  const body: unknown =
    response.status === 204 ? null : await response.json().catch(() => null);

  if (!response.ok) {
    throw new ApiError(
      response.status,
      describe(response.status, body),
      body,
      envelope(body).code,
    );
  }
  return body as T;
}
