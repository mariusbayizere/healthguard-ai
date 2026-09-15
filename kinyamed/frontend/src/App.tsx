import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { auth } from "@/lib/auth";
import { Layout } from "@/components/Layout";
import { Dashboard } from "@/routes/Dashboard";
import { Doctor } from "@/routes/Doctor";
import { Login } from "@/routes/Login";
import { NewPassword } from "@/routes/NewPassword";
import { NotFound } from "@/routes/NotFound";
import { Queue } from "@/routes/Queue";
import { ResetPassword } from "@/routes/ResetPassword";
import { Settings } from "@/routes/Settings";
import { SignUp } from "@/routes/SignUp";
import { Triage } from "@/routes/Triage";

const client = new QueryClient({
  defaultOptions: {
    queries: {
      // A 401 clears the token; retrying it three times just delays the login
      // screen and hammers the API while a clinic waits.
      retry: (failureCount, error) =>
        (error as { status?: number }).status === 401 ? false : failureCount < 2,
      staleTime: 2_000,
    },
  },
});

function Protected({ children }: { children: React.ReactNode }) {
  return auth.isAuthenticated() ? <>{children}</> : <Navigate to="/login" replace />;
}

export default function App() {
  return (
    <QueryClientProvider client={client}>
      <BrowserRouter>
        <Routes>
          {/* Unauthenticated. Sign-up and reset sit outside Protected because
              the people who need them cannot sign in by definition. */}
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<SignUp />} />
          <Route path="/reset-password" element={<ResetPassword />} />
          <Route path="/new-password" element={<NewPassword />} />
          <Route element={<Protected><Layout /></Protected>}>
            <Route index element={<Triage />} />
            <Route path="queue" element={<Queue />} />
            <Route path="doctor" element={<Doctor />} />
            <Route path="dashboard" element={<Dashboard />} />
            <Route path="settings" element={<Settings />} />
          </Route>
          {/* Catch-all. Without it an unknown URL rendered a blank page. */}
          <Route path="*" element={<NotFound />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
