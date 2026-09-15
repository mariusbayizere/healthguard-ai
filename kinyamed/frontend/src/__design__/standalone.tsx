/* The unauthenticated screens, each as it actually ships: outside Layout,
 * providing its own <main>. Selected by ?view=. */
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { SignUp } from "@/routes/SignUp";
import { ResetPassword } from "@/routes/ResetPassword";
import { NewPassword } from "@/routes/NewPassword";
import { NotFound } from "@/routes/NotFound";
import "@/styles/index.css";

const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
const view = new URLSearchParams(location.search).get("view") ?? "signup";
const SCREENS: Record<string, React.ReactNode> = {
  signup: <SignUp />,
  reset: <ResetPassword />,
  newpassword: <NewPassword />,
  notfound: <NotFound />,
};

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={qc}>
      <MemoryRouter>{SCREENS[view] ?? <SignUp />}</MemoryRouter>
    </QueryClientProvider>
  </StrictMode>,
);
