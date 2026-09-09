# KinyaMed frontend

Three views wired to the real API: triage intake, the live queue, and a doctor
dashboard.

## Why this is plain HTML and JavaScript

No build step, no `node_modules`, no framework. Serve the directory and it runs:

    cd kinyamed/frontend && python3 -m http.server 5173

`CORS_ORIGINS` already allows `http://localhost:5173`, so this works against a
locally running API with no configuration.

The reason is not minimalism for its own sake. A health centre deployment in a
low-connectivity setting is better served by static files than by a bundle that
needs a toolchain to rebuild, and the reference hardware for this project is a
laptop that has been OOM-killed by the test suite. A React app would be more
comfortable to extend and would add a dependency tree nobody here can audit.
If that trade stops being right, the API contract is unchanged and a rewrite
touches nothing server-side.

## THE ONE RULE THIS UI FOLLOWS

**No patient-facing text is written in this frontend.** Not a reassurance, not
an instruction, not a translated label for an urgency level.

The sentence a patient reads comes from `patient_response` in the API response,
which is speaker-authored or absent. When it is absent the API says so with
`response_pending`, and this UI shows that state to STAFF in English rather
than substituting something plausible.

Interface chrome — buttons, column headings, status labels — is English and is
addressed to clinic staff, not to patients. If this UI is ever put in front of
patients directly, that chrome needs authoring by a speaker in the same way the
response templates were, and it is not authored yet.

## Files

| file | view |
|---|---|
| `index.html` | triage intake: submit a symptom description, see the result |
| `queue.html` | live queue, urgency-ordered |
| `dashboard.html` | doctor view: assign, advance status |
| `app.js` | API client, auth, shared rendering |
| `style.css` | one stylesheet |
