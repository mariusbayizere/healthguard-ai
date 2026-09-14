/* Design harness — NOT part of the application bundle.
 *
 * Renders the real route components against a seeded query cache so every
 * view can be looked at, at a real viewport width, with no backend and no
 * login. Mounted by design.html, which is not referenced by index.html and is
 * excluded from the production build input.
 *
 * The point is to look at what SHIPS. So it imports the real routes and the
 * real components -- not copies -- and seeds TanStack Query's cache rather
 * than stubbing the hooks, which would let the harness and the app diverge.
 */
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { keys } from "@/api/hooks";
import type { QueueEntry } from "@/api/types";
import { Layout } from "@/components/Layout";
import { QueueTable } from "@/components/QueueTable";
import { PatientMessage } from "@/components/PatientMessage";
import { Queue } from "@/routes/Queue";
import { Doctor } from "@/routes/Doctor";
import { Login } from "@/routes/Login";
import { Triage } from "@/routes/Triage";
import { Alert, Button, Card, Empty, Skeleton } from "@/components/ui";
import "@/styles/index.css";

localStorage.setItem("kinyamed.token", "harness");

const ROWS: QueueEntry[] = [
  { id: 1, queue_number: 12, urgency_level: "CRITICAL", status: "WAITING",
    patient_id: 1, patient_name: "Uwimana Claudine", doctor_name: null,
    estimated_wait: 0 },
  { id: 2, queue_number: 13, urgency_level: "CRITICAL", status: "IN_PROGRESS",
    patient_id: 2, patient_name: "Habimana Jean-Baptiste", doctor_name: "Dr Mukamana",
    estimated_wait: 5 },
  { id: 3, queue_number: 9, urgency_level: "URGENT", status: "WAITING",
    patient_id: 3, patient_name: "Nshimiyimana Eric", doctor_name: null,
    estimated_wait: 25 },
  { id: 4, queue_number: 14, urgency_level: "URGENT", status: "WAITING",
    patient_id: 4, patient_name: "M", doctor_name: null, estimated_wait: 40 },
  { id: 5, queue_number: 7, urgency_level: "ROUTINE", status: "WAITING",
    patient_id: 5, patient_name: "Ingabire Marie-Chantal Nyiraminani", doctor_name: null,
    estimated_wait: 95 },
];

const qc = new QueryClient({
  defaultOptions: { queries: { retry: false, refetchInterval: false, staleTime: Infinity } },
});
qc.setQueryData(keys.queue, ROWS);
qc.setQueryData(keys.patients, [
  { id: 1, name: "Uwimana Claudine", phone: "+250788000001" },
  { id: 2, name: "Habimana Jean-Baptiste", phone: null },
]);
qc.setQueryData(keys.doctors, [
  { id: 1, name: "Dr Mukamana", is_on_duty: true },
  { id: 2, name: "Dr Niyonzima", is_on_duty: true },
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

function Shell({ children }: { children: React.ReactNode }) {
  return (
    <div className="mx-auto max-w-5xl px-4 py-6 sm:px-6 sm:py-8">{children}</div>
  );
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={["/queue"]}>
        <Frame id="chrome" label="Layout chrome (header + footer)">
          <Layout />
        </Frame>
        <Frame id="queue" label="Queue view">
          <Shell><Queue /></Shell>
        </Frame>
        <Frame id="doctor" label="Doctor view">
          <Shell><Doctor /></Shell>
        </Frame>
        <Frame id="triage" label="Triage view (empty form)">
          <Shell><Triage /></Shell>
        </Frame>
        <Frame id="login" label="Login view">
          <Login />
        </Frame>
        <Frame id="states" label="States: loading / empty / errors / response">
          <Shell>
            <div className="space-y-6">
              <Card title="Loading"><QueueTable rows={[]} isLoading /></Card>
              <Card title="Empty"><QueueTable rows={[]} /></Card>
              <Alert>Could not save. The server rejected the request.</Alert>
              <Alert kind="offline" action={<Button variant="quiet">Retry</Button>}>
                No connection. The board below may be out of date.
              </Alert>
              <Alert kind="ok">Saved.</Alert>
              <Card title="Patient message — receipt">
                <PatientMessage
                  text="Your report has been received. Your queue number is 12 and you are number 1 in the queue. If you feel worse or this is an emergency, go to the health centre immediately."
                  language="english"
                />
              </Card>
              <Card title="Patient message — malformed">
                <PatientMessage text="Your queue number is {queue_number}." language="english" />
              </Card>
              <Card title="Skeleton"><Skeleton /></Card>
              <Card title="Empty primitive"><Empty title="Nothing here">Secondary line.</Empty></Card>
            </div>
          </Shell>
        </Frame>
      </MemoryRouter>
    </QueryClientProvider>
  </StrictMode>,
);
