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
  type Doctor, type LoginResponse, type Patient,
  type QueueEntry, type QueueStatus, type TriageResult, type Urgency,
} from "./types";

export const keys = {
  queue: ["queue"] as const,
  patients: ["patients"] as const,
  doctors: ["doctors", "on-duty"] as const,
};

/** Five seconds. A nurse glancing up expects the board to be current; a minute
 *  is long enough for a critical arrival to be missed. Cheap: the queue is
 *  tens of rows, not thousands. */
const QUEUE_POLL_MS = 5_000;

export function useQueue() {
  return useQuery({
    queryKey: keys.queue,
    // Returned in the API's order and NOT re-sorted. The server orders the
    // queue by band and arrival (item 2d). A client re-sort by urgency was a
    // second source of truth for who is seen next, and it put a case the model
    // could not classify below every URGENT patient.
    queryFn: async () => toList<QueueEntry>(await request<unknown>("/queue")),
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
        // Band and position are the SERVER's: `band` and `queue_position` come
        // back on the triage response, so the client never re-derives the band
        // rule or sorts. Read at runtime because `TriageResult` in types.ts
        // predates them.
        const fields = result as unknown as Record<string, unknown>;
        const position = typeof fields["queue_position"] === "number" ? fields["queue_position"] : Infinity;
        const row = {
          id: result.queue_id,
          queue_number: result.queue_number,
          urgency_level: result.urgency_level,
          status: "WAITING",
          patient_id: result.patient_id,
          patient_name: result.patient_name,
          doctor_name: null,
          estimated_wait: result.estimated_wait,
          band: fields["band"],
          queue_position: fields["queue_position"],
          requires_human_review: fields["requires_human_review"],
        } as QueueEntry;
        const rows = [...(current ?? [])];
        rows.splice(Math.min(Math.max(position - 1, 0), rows.length), 0, row);
        return rows;
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
    mutationFn: async (input: { username: string; password: string }) => {
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
