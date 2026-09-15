/** Server state. TanStack Query owns caching, polling and invalidation.
 *
 * The queue is polled rather than pushed because the API has no websocket. The
 * interval is a clinical decision, not a technical one, and is stated where it
 * is set rather than buried in a constant.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { request } from "./client";
import { auth } from "@/lib/auth";
import {
  toList,
  type CurrentUser, type Doctor, type LanguageBreakdown, type LoginResponse,
  type Patient, type QueueEntry, type QueuePerformance, type QueueStatus,
  type Session, type Summary, type Throughput, type TriageResult,
  type UrgencyBreakdown, type UrgencyOverTime, type WaitByUrgency,
  type Urgency,
  URGENCY_RANK,
} from "./types";

export const keys = {
  queue: ["queue"] as const,
  patients: ["patients"] as const,
  doctors: ["doctors", "on-duty"] as const,
  me: ["me"] as const,
  sessions: ["sessions"] as const,
  summary: ["analytics", "summary"] as const,
  urgency: ["analytics", "urgency"] as const,
  queuePerf: ["analytics", "queue-performance"] as const,
  languages: ["analytics", "language-breakdown"] as const,
  urgencyOverTime: (days: number) => ["analytics", "urgency-over-time", days] as const,
  throughput: (days: number) => ["analytics", "throughput", days] as const,
  waitByUrgency: ["analytics", "wait-by-urgency"] as const,
};

/** Five seconds. A nurse glancing up expects the board to be current; a minute
 *  is long enough for a critical arrival to be missed. Cheap: the queue is
 *  tens of rows, not thousands. */
const QUEUE_POLL_MS = 5_000;

export function useQueue() {
  return useQuery({
    queryKey: keys.queue,
    queryFn: async () => {
      const rows = toList<QueueEntry>(await request<unknown>("/queue"));
      // Sorted here, once, rather than in each view. The API returns clinical
      // priority already; this makes the guarantee explicit and survives an
      // API that stops honouring it.
      return [...rows].sort(
        (a, b) =>
          (URGENCY_RANK[a.urgency_level] ?? 9) - (URGENCY_RANK[b.urgency_level] ?? 9) ||
          a.queue_number - b.queue_number,
      );
    },
    refetchInterval: QUEUE_POLL_MS,
    refetchOnWindowFocus: true,
    enabled: auth.isAuthenticated(),
  });
}

export function usePatients() {
  return useQuery({
    queryKey: keys.patients,
    queryFn: async () => toList<Patient>(await request<unknown>("/patients?limit=200")),
    enabled: auth.isAuthenticated(),
    staleTime: 60_000,
  });
}

export function useOnDutyDoctors() {
  return useQuery({
    queryKey: keys.doctors,
    queryFn: async () => toList<Doctor>(await request<unknown>("/doctors/on-duty")),
    enabled: auth.isAuthenticated(),
    staleTime: 60_000,
  });
}

export function useSubmitTriage() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: { patient_id: number; symptoms_input: string }) =>
      request<TriageResult>("/triage", {
        method: "POST",
        body: JSON.stringify(input),
      }),
    // The submitted case appears in the queue with NO round trip. The API
    // returns queue_id, so a complete QueueEntry can be built -- including the
    // key that /queue/{id}/status and /queue/{id}/assign-doctor address. That
    // id is why this is a cache write rather than a refetch: without it the
    // inserted row would render working buttons that PATCH /queue/undefined.
    onSuccess: (result) => {
      qc.setQueryData<QueueEntry[]>(keys.queue, (current) => {
        const row: QueueEntry = {
          id: result.queue_id,
          queue_number: result.queue_number,
          urgency_level: result.urgency_level,
          status: "WAITING",
          patient_id: result.patient_id,
          patient_name: result.patient_name,
          doctor_name: null,
          estimated_wait: result.estimated_wait,
        };
        // Re-sorted on insert so the new row lands at its clinical position
        // rather than at the end. Same comparator as the fetch path.
        return [...(current ?? []), row].sort(
          (a, b) =>
            (URGENCY_RANK[a.urgency_level] ?? 9) - (URGENCY_RANK[b.urgency_level] ?? 9) ||
            a.queue_number - b.queue_number,
        );
      });
      // The optimistic row is complete but the SERVER's wait estimates for
      // every other row have shifted. Revalidate in the background; the board
      // is already correct for the case just submitted.
      void qc.invalidateQueries({ queryKey: keys.queue });
    },
  });
}

export function useSetQueueStatus() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, status }: { id: number; status: QueueStatus }) =>
      request<QueueEntry>(`/queue/${id}/status`, {
        method: "PATCH",
        body: JSON.stringify({ status }),
      }),
    onSuccess: () => void qc.invalidateQueries({ queryKey: keys.queue }),
  });
}

export function useAssignDoctor() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, doctorId }: { id: number; doctorId: number }) =>
      request<QueueEntry>(`/queue/${id}/assign-doctor`, {
        method: "PATCH",
        body: JSON.stringify({ doctor_id: doctorId }),
      }),
    onSuccess: () => void qc.invalidateQueries({ queryKey: keys.queue }),
  });
}

export function useLogin() {
  return useMutation({
    // `email`, NOT `username`. The backend's LoginRequest requires an EmailStr
    // and this sent {username, password}, so every sign-in attempt was
    // rejected 422 before any credential was checked -- the form could not
    // work at all. Nothing caught it: the component tests never cross the
    // network and the backend tests build their own payloads. AUDIT 3.1 is the
    // real fix (generate the client from the schema); until then
    // backend/tests/unit/test_login_contract.py asserts the two agree.
    mutationFn: async (input: { email: string; password: string }) => {
      const body = await request<LoginResponse>("/auth/login", {
        method: "POST",
        body: JSON.stringify(input),
      });
      const token = body.access_token ?? body.token;
      if (!token) throw new Error("Login succeeded but returned no token.");
      auth.set(token);
      return token;
    },
  });
}

export type { Urgency };


/* ── Account and analytics ──────────────────────────────────────────────────
 *
 * The analytics endpoints are ADMIN-ONLY on the server. These do not retry:
 * a 403 is a settled answer about who you are, and retrying it three times
 * only delays the dashboard telling you so.
 */

export function useMe() {
  return useQuery({
    queryKey: keys.me,
    queryFn: () => request<CurrentUser>("/auth/me"),
    enabled: auth.isAuthenticated(),
    retry: false,
  });
}

export function useSessions() {
  return useQuery({
    queryKey: keys.sessions,
    queryFn: async () => toList<Session>(await request<unknown>("/auth/sessions")),
    enabled: auth.isAuthenticated(),
    retry: false,
  });
}

export function useChangePassword() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: { current_password: string; new_password: string }) =>
      request<{ message: string }>("/auth/change-password", {
        method: "POST",
        body: JSON.stringify(input),
      }),
    // Changing a password revokes other sessions server-side, so the list on
    // screen is stale the moment this succeeds.
    onSuccess: () => void qc.invalidateQueries({ queryKey: keys.sessions }),
  });
}

export function useRegister() {
  return useMutation({
    // `auth.set` is the whole reason this differs from a bare request. Without
    // it a SUCCESSFUL registration redirected to "/" with no token, `Protected`
    // bounced straight back to /login, and sign-up was indistinguishable from
    // failure. `useLogin` always stored the token; this never did.
    // Matches RegisterRequest exactly. This endpoint creates a PATIENT chart
    // alongside the login; staff accounts are made by an administrator and
    // never here, which is why the form says so.
    mutationFn: (input: {
      email: string;
      password: string;
      full_name: string;
      phone: string;
      age?: number | null;
      gender?: string | null;
      location?: string | null;
    }) =>
      request<LoginResponse>("/auth/register", {
        method: "POST",
        body: JSON.stringify(input),
      }).then((body) => {
        const token = body.access_token ?? body.token;
        if (!token) throw new Error("Registration succeeded but returned no token.");
        auth.set(token);
        return token;
      }),
  });
}

const ADMIN_ONLY = { enabled: auth.isAuthenticated(), retry: false, staleTime: 30_000 };

export function useSummary() {
  return useQuery({
    queryKey: keys.summary,
    queryFn: () => request<Summary>("/analytics/summary"),
    ...ADMIN_ONLY,
  });
}

export function useUrgencyBreakdown() {
  return useQuery({
    queryKey: keys.urgency,
    queryFn: () => request<UrgencyBreakdown>("/analytics/urgency-breakdown"),
    ...ADMIN_ONLY,
  });
}

export function useQueuePerformance() {
  return useQuery({
    queryKey: keys.queuePerf,
    queryFn: () => request<QueuePerformance>("/analytics/queue-performance"),
    ...ADMIN_ONLY,
  });
}

export function useLanguageBreakdown() {
  return useQuery({
    queryKey: keys.languages,
    queryFn: () => request<LanguageBreakdown>("/analytics/language-breakdown"),
    ...ADMIN_ONLY,
  });
}


export function useUrgencyOverTime(days = 30) {
  return useQuery({
    queryKey: keys.urgencyOverTime(days),
    queryFn: () =>
      request<UrgencyOverTime>(`/analytics/urgency-over-time?days=${days}`),
    ...ADMIN_ONLY,
  });
}

export function useThroughput(days = 30) {
  return useQuery({
    queryKey: keys.throughput(days),
    queryFn: () => request<Throughput>(`/analytics/throughput?days=${days}`),
    ...ADMIN_ONLY,
  });
}

export function useWaitByUrgency() {
  return useQuery({
    queryKey: keys.waitByUrgency,
    queryFn: () => request<WaitByUrgency>("/analytics/wait-by-urgency"),
    ...ADMIN_ONLY,
  });
}


/** Sign out on the SERVER, not just in this tab.
 *
 * `Layout` used to call `auth.clear()` and reload. That drops the access token
 * locally and leaves the refresh token live, so on a device passed between
 * staff the next person's browser can still mint a fresh access token for the
 * previous user. `/auth/logout` revokes it.
 *
 * Resolves even when the request fails: a clinician pressing Sign out must end
 * up signed out of this browser whatever the network is doing.
 */
export function useLogout() {
  return useMutation({
    mutationFn: async () => {
      try {
        await request<{ message: string }>("/auth/logout", { method: "POST" });
      } catch {
        // Deliberately swallowed -- see above.
      }
      auth.clear();
    },
  });
}

/** End every session for this account, everywhere. */
export function useLogoutEverywhere() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () =>
      request<{ message: string }>("/auth/logout-all", { method: "POST" }),
    onSuccess: () => void qc.invalidateQueries({ queryKey: keys.sessions }),
  });
}

export function useUpdateProfile() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: { full_name: string }) =>
      request<CurrentUser>("/auth/me", {
        method: "PATCH",
        body: JSON.stringify(input),
      }),
    onSuccess: (user) => qc.setQueryData(keys.me, user),
  });
}

export function useRequestPasswordReset() {
  return useMutation({
    mutationFn: (input: { email: string }) =>
      request<{ message: string }>("/auth/password-reset/request", {
        method: "POST",
        body: JSON.stringify(input),
      }),
  });
}

/** Whether a reset link is still good, checked BEFORE showing the form.
 *
 * Asking the server first is what lets an expired link say so immediately,
 * instead of after someone has typed a new password twice. */
export function useValidateResetToken(token: string) {
  return useQuery({
    queryKey: ["password-reset", "validate", token] as const,
    queryFn: () =>
      request<{ valid: boolean }>(
        `/auth/password-reset/validate?token=${encodeURIComponent(token)}`,
      ),
    enabled: token.length > 0,
    retry: false,
  });
}

export function useConfirmPasswordReset() {
  return useMutation({
    mutationFn: (input: { token: string; new_password: string }) =>
      request<{ message: string }>("/auth/password-reset/confirm", {
        method: "POST",
        body: JSON.stringify(input),
      }),
  });
}
