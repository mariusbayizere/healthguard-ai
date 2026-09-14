import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import { TriageOfflineBanner } from "./components/TriageOfflineBanner";
import "./styles/index.css";

const root = document.getElementById("root");
if (!root) throw new Error("#root is missing from index.html");
createRoot(root).render(
  <StrictMode>
    <TriageOfflineBanner />
    <App />
  </StrictMode>,
);
