import { NavLink, Outlet, useLocation } from "react-router-dom";
import { auth } from "@/lib/auth";
import { Button } from "./ui";

const TABS = [
  { to: "/", label: "Triage", end: true },
  { to: "/queue", label: "Queue", end: false },
  { to: "/doctor", label: "Doctor", end: false },
];

export function Layout() {
  const { pathname } = useLocation();
  // Every page needs exactly one h1, and it should say which page. The brand
  // was a <span> and views begin at h2 (Card titles), so an authenticated page
  // had NO level-one heading at all -- a screen-reader user navigating by
  // heading found nothing to land on and no way to tell the queue from the
  // doctor board. axe: page-has-heading-one, confirmed on the real shell.
  //
  // The visible mark is unchanged. The view name is appended for assistive
  // technology only, so the h1 is distinct per page without a design change.
  const current = TABS.find((t) => (t.end ? pathname === t.to : pathname.startsWith(t.to)));

  return (
    <div className="min-h-screen">
      <header className="border-b border-ink-200 bg-white">
        <div className="mx-auto flex max-w-5xl flex-wrap items-center gap-x-6 gap-y-2 px-4 py-3 sm:px-6">
          <h1 className="text-lg font-semibold tracking-tight text-ink-900">
            KinyaMed
            {current && <span className="sr-only"> — {current.label}</span>}
          </h1>
          <nav className="flex gap-1" aria-label="Main">
            {TABS.map((t) => (
              <NavLink
                key={t.to}
                to={t.to}
                end={t.end}
                className={({ isActive }) =>
                  [
                    "inline-flex min-h-11 items-center rounded px-3 text-sm font-medium transition-colors duration-fast",
                    isActive
                      ? "bg-action-soft text-action"
                      : "text-ink-700 hover:bg-ink-100",
                  ].join(" ")
                }
              >
                {t.label}
              </NavLink>
            ))}
          </nav>
          <div className="ml-auto">
            <Button
              variant="quiet"
              onClick={() => {
                auth.clear();
                location.assign("/");
              }}
            >
              Sign out
            </Button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-5xl px-4 py-6 sm:px-6 sm:py-8">
        <Outlet />
      </main>
      {/* Stated on every screen. This system does not meet its own acceptance
          gate, and a tool that hides that from the person using it is worse
          than one that never claimed to be clinical. */}
      <footer className="mx-auto max-w-5xl px-4 pb-10 text-xs text-ink-600 sm:px-6">
        Decision support only. The model does not currently meet its acceptance
        threshold for critical recall and is not cleared for clinical use.
        Clinical judgement overrides every suggestion shown here.
      </footer>
    </div>
  );
}
