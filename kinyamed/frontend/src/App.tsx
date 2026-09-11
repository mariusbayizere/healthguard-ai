import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { auth } from "@/lib/auth";
import { Layout } from "@/components/Layout";
import { Doctor } from "@/routes/Doctor";
import { Login } from "@/routes/Login";
import { Queue } from "@/routes/Queue";
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
          <Route path="/login" element={<Login />} />
          <Route element={<Protected><Layout /></Protected>}>
            <Route index element={<Triage />} />
            <Route path="queue" element={<Queue />} />
            <Route path="doctor" element={<Doctor />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
