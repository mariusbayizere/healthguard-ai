/* Shared API client and rendering helpers.
 *
 * DESIGN NOTE, and it is the important one: this file renders what the API
 * returns and never invents patient-facing language. `patient_response` is
 * speaker-authored or absent, and when absent we show the pending state rather
 * than a placeholder. See README.md.
 */
"use strict";

const API = localStorage.getItem("kinyamed_api") || "http://localhost:8000/api/v1";

const Auth = {
  token: () => localStorage.getItem("kinyamed_token"),
  set: (t) => localStorage.setItem("kinyamed_token", t),
  clear: () => localStorage.removeItem("kinyamed_token"),
  headers() {
    const h = { "Content-Type": "application/json" };
    const t = this.token();
    if (t) h["Authorization"] = `Bearer ${t}`;
    return h;
  },
};

async function api(path, options = {}) {
  const res = await fetch(`${API}${path}`, { headers: Auth.headers(), ...options });
  if (res.status === 401) {
    Auth.clear();
    throw new Error("Session expired. Sign in again.");
  }
  const body = res.status === 204 ? null : await res.json().catch(() => null);
  if (!res.ok) {
    // Surface the API's own message. A generic "something went wrong" hides
    // exactly the detail a clinic needs to tell a support person.
    const detail = body && (body.detail || body.message);
    throw new Error(detail ? JSON.stringify(detail) : `${res.status} ${res.statusText}`);
  }
  return body;
}

const URGENCY_ORDER = { CRITICAL: 0, URGENT: 1, ROUTINE: 2 };

function urgencyBadge(level) {
  const el = document.createElement("span");
  el.className = `badge badge-${(level || "").toLowerCase()}`;
  el.textContent = level || "—";
  return el;
}

/* Render the patient-facing response, or the reason there isn't one.
 *
 * The pending branch is deliberately conspicuous and deliberately in English:
 * it is addressed to staff, telling them the system has nothing authored to
 * say to this patient in this language. It must never look like advice. */
function renderPatientResponse(result, into) {
  into.innerHTML = "";
  if (result.response_pending || !result.patient_response) {
    const box = document.createElement("div");
    box.className = "pending";
    const h = document.createElement("strong");
    h.textContent = "No patient response available";
    const p = document.createElement("p");
    p.textContent =
      result.response_pending_reason ||
      "No speaker-authored response template exists for this language.";
    const note = document.createElement("p");
    note.className = "muted";
    note.textContent =
      "Tell the patient their urgency and queue number in person. " +
      "Nothing has been written for this language, and the system will not " +
      "invent it.";
    box.append(h, p, note);
    into.appendChild(box);
    return;
  }
  const box = document.createElement("div");
  box.className = "response";
  box.textContent = result.patient_response;
  into.appendChild(box);
}

function fmtWait(minutes) {
  if (minutes === null || minutes === undefined) return "—";
  return `~${minutes} min`;
}

function flash(message, kind = "error") {
  const bar = document.getElementById("flash");
  if (!bar) return;
  bar.textContent = message;
  bar.className = `flash flash-${kind}`;
  bar.hidden = false;
  if (kind !== "error") setTimeout(() => (bar.hidden = true), 4000);
}

function requireAuth() {
  if (!Auth.token()) {
    document.getElementById("login-panel").hidden = false;
    document.getElementById("main-panel").hidden = true;
    return false;
  }
  document.getElementById("login-panel").hidden = true;
  document.getElementById("main-panel").hidden = false;
  return true;
}

async function doLogin(event) {
  event.preventDefault();
  const form = event.target;
  try {
    const body = await api("/auth/login", {
      method: "POST",
      body: JSON.stringify({
        username: form.username.value,
        password: form.password.value,
      }),
    });
    Auth.set(body.access_token || body.token);
    location.reload();
  } catch (err) {
    flash(err.message);
  }
}
