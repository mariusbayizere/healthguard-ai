/* The REAL application shell, for landmark auditing.
 *
 * The multi-view harness stacks every view in bare <section>s so they can be
 * screenshotted side by side, which puts content outside any landmark and
 * makes axe's `region` rule fire on the harness rather than on the app. This
 * page renders exactly what a user loads -- Layout (header/main/footer) with
 * one route inside it -- so the landmark result is about the product.
 */
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { keys } from "@/api/hooks";
import type { QueueEntry } from "@/api/types";
import { Layout } from "@/components/Layout";
import { Queue } from "@/routes/Queue";
import "@/styles/index.css";

localStorage.setItem("kinyamed.token", "harness");

const ROWS: QueueEntry[] = [
  { id: 1, queue_number: 12, urgency_level: "CRITICAL", status: "WAITING",
    patient_id: 1, patient_name: "Uwimana Claudine", doctor_name: null,
    estimated_wait: 0 },
  { id: 2, queue_number: 9, urgency_level: "URGENT", status: "WAITING",
    patient_id: 2, patient_name: "Nshimiyimana Eric", doctor_name: null,
    estimated_wait: 25 },
];

const qc = new QueryClient({
  defaultOptions: { queries: { retry: false, refetchInterval: false, staleTime: Infinity } },
});
qc.setQueryData(keys.queue, ROWS);
qc.setQueryData(keys.doctors, []);
qc.setQueryData(keys.patients, []);

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={["/queue"]}>
        <Routes>
          <Route element={<Layout />}>
            <Route path="/queue" element={<Queue />} />
          </Route>
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  </StrictMode>,
);
