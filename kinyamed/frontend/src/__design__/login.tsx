/* Sign-in, rendered alone. It is a full-viewport layout and would be clipped
 * inside the stacked multi-view harness. */
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Login } from "@/routes/Login";
import "@/styles/index.css";

const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={qc}>
      <MemoryRouter><Login /></MemoryRouter>
    </QueryClientProvider>
  </StrictMode>,
);
