/** Whether automated triage is available, from the API's readiness probe.
 *
 * `/health/ready` sits at the API's root, outside `/api/v1`, so its URL is
 * derived from `API_BASE` rather than configured twice.
 */
import { API_BASE } from "@/api/client";

export const HEALTH_READY_URL = `${API_BASE.replace(/\/api\/v1\/?$/, "")}/health/ready`;

/** Probes that hang are treated as failures after this long. */
const PROBE_TIMEOUT_MS = 5_000;

/** True only when the API positively reports a loaded model.
 *
 * Anything else -- `model: false`, an unreachable API, a malformed body, a
 * timeout -- is false. Staff are told to triage manually unless the system can
 * show that automated triage is available: the banner fails closed.
 */
export async function isTriageModelLoaded(): Promise<boolean> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), PROBE_TIMEOUT_MS);
  try {
    const response = await fetch(HEALTH_READY_URL, { signal: controller.signal });
    if (!response.ok) return false;
    const body: unknown = await response.json();
    return Boolean(body && typeof body === "object" && (body as { model?: unknown }).model === true);
  } catch {
    return false;
  } finally {
    clearTimeout(timer);
  }
}
