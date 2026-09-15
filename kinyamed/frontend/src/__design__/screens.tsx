/* The four account/analytics screens, for rendering. Seeded cache, no network. */
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { keys } from "@/api/hooks";
import { Dashboard } from "@/routes/Dashboard";
import { SignUp } from "@/routes/SignUp";
import { ResetPassword } from "@/routes/ResetPassword";
import { Settings } from "@/routes/Settings";
import "@/styles/index.css";

localStorage.setItem("kinyamed.token", "harness");

const qc = new QueryClient({
  defaultOptions: { queries: { retry: false, refetchInterval: false, staleTime: Infinity } },
});
qc.setQueryData(keys.summary, {
  total_patients: 1284, total_triage_done: 3921,
  critical_cases: 214, urgent_cases: 1180, routine_cases: 2527,
  queue_waiting: 12, queue_in_progress: 3, queue_done: 3844, queue_cancelled: 62,
  sms_sent: 2731, sms_failed: 88, doctors_on_duty: 4,
});
qc.setQueryData(keys.urgency, {
  total: 3921,
  critical: { count: 214, percentage: 5.46 },
  urgent: { count: 1180, percentage: 30.09 },
  routine: { count: 2527, percentage: 64.45 },
});
qc.setQueryData(keys.queuePerf, {
  currently_waiting: 12, currently_in_progress: 3, completed_today: 47,
  average_quoted_wait_minutes: 24.5, average_actual_wait_minutes: 38.2,
});
qc.setQueryData(keys.languages, {
  counts: { rw: 2411, en: 780, fr: 512, sw: 218 }, total: 3921,
});
qc.setQueryData(keys.urgencyOverTime(30), {"days": 30, "points": [{"day": "2026-08-13", "critical": 0, "urgent": 2, "routine": 14}, {"day": "2026-08-14", "critical": 1, "urgent": 4, "routine": 9}, {"day": "2026-08-15", "critical": 4, "urgent": 3, "routine": 24}, {"day": "2026-08-16", "critical": 0, "urgent": 2, "routine": 8}, {"day": "2026-08-17", "critical": 1, "urgent": 10, "routine": 25}, {"day": "2026-08-18", "critical": 4, "urgent": 5, "routine": 28}, {"day": "2026-08-19", "critical": 4, "urgent": 8, "routine": 13}, {"day": "2026-08-20", "critical": 4, "urgent": 6, "routine": 6}, {"day": "2026-08-21", "critical": 1, "urgent": 13, "routine": 19}, {"day": "2026-08-22", "critical": 2, "urgent": 4, "routine": 12}, {"day": "2026-08-23", "critical": 2, "urgent": 3, "routine": 8}, {"day": "2026-08-24", "critical": 0, "urgent": 7, "routine": 17}, {"day": "2026-08-25", "critical": 2, "urgent": 14, "routine": 7}, {"day": "2026-08-26", "critical": 3, "urgent": 10, "routine": 9}, {"day": "2026-08-27", "critical": 3, "urgent": 3, "routine": 23}, {"day": "2026-08-28", "critical": 4, "urgent": 7, "routine": 24}, {"day": "2026-08-29", "critical": 0, "urgent": 2, "routine": 27}, {"day": "2026-08-30", "critical": 2, "urgent": 3, "routine": 13}, {"day": "2026-08-31", "critical": 0, "urgent": 8, "routine": 14}, {"day": "2026-09-01", "critical": 2, "urgent": 4, "routine": 17}, {"day": "2026-09-02", "critical": 1, "urgent": 12, "routine": 14}, {"day": "2026-09-03", "critical": 0, "urgent": 11, "routine": 26}, {"day": "2026-09-04", "critical": 4, "urgent": 13, "routine": 13}, {"day": "2026-09-05", "critical": 3, "urgent": 8, "routine": 14}, {"day": "2026-09-06", "critical": 4, "urgent": 5, "routine": 27}, {"day": "2026-09-07", "critical": 0, "urgent": 5, "routine": 7}, {"day": "2026-09-08", "critical": 2, "urgent": 8, "routine": 14}, {"day": "2026-09-09", "critical": 1, "urgent": 11, "routine": 28}, {"day": "2026-09-10", "critical": 1, "urgent": 12, "routine": 21}, {"day": "2026-09-11", "critical": 3, "urgent": 4, "routine": 14}]});
qc.setQueryData(keys.throughput(30), {"days": 30, "points": [{"day": "2026-08-13", "completed": 11}, {"day": "2026-08-14", "completed": 25}, {"day": "2026-08-15", "completed": 17}, {"day": "2026-08-16", "completed": 10}, {"day": "2026-08-17", "completed": 4}, {"day": "2026-08-18", "completed": 24}, {"day": "2026-08-19", "completed": 18}, {"day": "2026-08-20", "completed": 28}, {"day": "2026-08-21", "completed": 14}, {"day": "2026-08-22", "completed": 34}, {"day": "2026-08-23", "completed": 16}, {"day": "2026-08-24", "completed": 23}, {"day": "2026-08-25", "completed": 27}, {"day": "2026-08-26", "completed": 33}, {"day": "2026-08-27", "completed": 13}, {"day": "2026-08-28", "completed": 10}, {"day": "2026-08-29", "completed": 11}, {"day": "2026-08-30", "completed": 31}, {"day": "2026-08-31", "completed": 18}, {"day": "2026-09-01", "completed": 15}, {"day": "2026-09-02", "completed": 26}, {"day": "2026-09-03", "completed": 9}, {"day": "2026-09-04", "completed": 9}, {"day": "2026-09-05", "completed": 33}, {"day": "2026-09-06", "completed": 14}, {"day": "2026-09-07", "completed": 29}, {"day": "2026-09-08", "completed": 6}, {"day": "2026-09-09", "completed": 14}, {"day": "2026-09-10", "completed": 16}, {"day": "2026-09-11", "completed": 8}], "total_completed": 546});
qc.setQueryData(keys.waitByUrgency, {"critical": {"p50_minutes": 8.5, "p90_minutes": 21.0, "completed": 196}, "urgent": {"p50_minutes": 34.0, "p90_minutes": 96.5, "completed": 1043}, "routine": {"p50_minutes": 71.5, "p90_minutes": 188.0, "completed": 2240}});
qc.setQueryData(keys.me, {
  id: 1, email: "j.mukamana@chuk.rw", full_name: "Dr Joselyne Mukamana",
  role: "ADMIN", is_active: true, patient_id: null, doctor_id: 2,
  last_login_at: "2026-09-11T06:42:00Z", created_at: "2026-02-01T09:00:00Z",
});
qc.setQueryData(keys.sessions, [
  { jti: "a1", created_at: "2026-09-11T06:42:00Z", expires_at: "2026-09-18T06:42:00Z",
    user_agent: "Mozilla/5.0 (Linux; Android 12) AppleWebKit/537.36" },
  { jti: "b2", created_at: "2026-09-09T14:10:00Z", expires_at: "2026-09-16T14:10:00Z",
    user_agent: "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)" },
]);

function Frame({ id, label, children }: { id: string; label: string; children: React.ReactNode }) {
  return (
    <section id={id} data-view={id} className="mb-12">
      <div className="mb-2 border-b-2 border-ink-900 pb-1 text-xs font-bold uppercase tracking-widest text-ink-900">
        {label}
      </div>
      {children}
    </section>
  );
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <Frame id="dashboard" label="Dashboard">
          <main className="mx-auto max-w-5xl px-4 py-6 sm:px-6"><Dashboard /></main>
        </Frame>
        <Frame id="settings" label="Account settings">
          <main className="mx-auto max-w-5xl px-4 py-6 sm:px-6"><Settings /></main>
        </Frame>
        <Frame id="signup" label="Sign up (patient registration)"><SignUp /></Frame>
        <Frame id="reset" label="Password reset"><ResetPassword /></Frame>
      </MemoryRouter>
    </QueryClientProvider>
  </StrictMode>,
);
