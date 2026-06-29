import { Route, Routes, useLocation, Navigate } from "react-router-dom";
import { useEffect, useState } from "react";
import Dashboard from "./pages/Dashboard";
import Jobs from "./pages/Jobs";
import Tailor from "./pages/Tailor";
import Pitcher from "./pages/Pitcher";
import Coach from "./pages/Coach";
import Tracker from "./pages/Tracker";
import Analytics from "./pages/Analytics";
import Onboarding from "./pages/Onboarding";
import Demo from "./pages/Demo";
import Auth from "./pages/Auth";
import AuthCallback from "./pages/AuthCallback";
import Cockpit from "./pages/Cockpit";
import AuthGuard from "./components/shared/AuthGuard";
import { useThemeStore } from "./store/useThemeStore";
import { useAuthStore } from "./store/useAuthStore";
import Tutorial, { STORAGE_KEY } from "./components/shared/Tutorial";

const NAV_LINKS = [
  { href: "/cockpit", label: "Cockpit", icon: "M9 17V7m0 10a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h2a2 2 0 012 2m0 10a2 2 0 002 2h2a2 2 0 002-2M9 7a2 2 0 012-2h2a2 2 0 012 2m0 10V7m0 10a2 2 0 002 2h2a2 2 0 002-2V7a2 2 0 00-2-2h-2a2 2 0 00-2 2" },
  { href: "/tailor", label: "Tailor", icon: "M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" },
  { href: "/pitcher", label: "Pitcher", icon: "M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" },
  { href: "/coach", label: "Coach", icon: "M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" },
  { href: "/tracker", label: "Tracker", icon: "M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" },
  { href: "/analytics", label: "Analytics", icon: "M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" },
  { href: "/jobs", label: "Jobs", icon: "M21 13.255A23.931 23.931 0 0112 15c-3.183 0-6.22-.62-9-1.745M16 6V4a2 2 0 00-2-2h-4a2 2 0 00-2 2v2m4 6h.01M5 20h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" },
];

function ThemeToggle() {
  const { theme, toggle } = useThemeStore();
  return (
    <button
      onClick={toggle}
      className="relative h-8 w-14 rounded-full border border-[var(--border-primary)] bg-[var(--bg-tertiary)] p-0.5 transition-all duration-300 hover:border-amber-500/50"
      aria-label="Toggle theme"
    >
      <div
        className={`flex h-6 w-6 items-center justify-center rounded-full bg-gradient-to-br transition-all duration-300 ${
          theme === "dark"
            ? "translate-x-0 from-indigo-500 to-purple-600"
            : "translate-x-6 from-amber-400 to-orange-500"
        }`}
      >
        {theme === "dark" ? (
          <svg className="h-3.5 w-3.5 text-white" fill="currentColor" viewBox="0 0 20 20">
            <path d="M17.293 13.293A8 8 0 016.707 2.707a8.001 8.001 0 1010.586 10.586z" />
          </svg>
        ) : (
          <svg className="h-3.5 w-3.5 text-white" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M10 2a1 1 0 011 1v1a1 1 0 11-2 0V3a1 1 0 011-1zm4 8a4 4 0 11-8 0 4 4 0 018 0zm-.464 4.95l.707.707a1 1 0 001.414-1.414l-.707-.707a1 1 0 00-1.414 1.414zm2.12-10.607a1 1 0 010 1.414l-.706.707a1 1 0 11-1.414-1.414l.707-.707a1 1 0 011.414 0zM17 11a1 1 0 100-2h-1a1 1 0 100 2h1zm-7 4a1 1 0 011 1v1a1 1 0 11-2 0v-1a1 1 0 011-1zM5.05 6.464A1 1 0 106.465 5.05l-.708-.707a1 1 0 00-1.414 1.414l.707.707zm1.414 8.486l-.707.707a1 1 0 01-1.414-1.414l.707-.707a1 1 0 011.414 1.414zM4 11a1 1 0 100-2H3a1 1 0 000 2h1z" clipRule="evenodd" />
          </svg>
        )}
      </div>
    </button>
  );
}

function NavLink({ href, label, icon, active }: { href: string; label: string; icon: string; active: boolean }) {
  return (
    <a
      href={href}
      className={`group flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-all duration-200 ${
        active
          ? "bg-amber-500/15 text-amber-400"
          : "text-[var(--text-muted)] hover:bg-[var(--bg-tertiary)] hover:text-[var(--text-primary)]"
      }`}
    >
      <svg className="h-4 w-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d={icon} />
      </svg>
      <span className="hidden lg:inline">{label}</span>
    </a>
  );
}

function UserMenu() {
  const { user, signOut } = useAuthStore();
  const [open, setOpen] = useState(false);
  if (!user) return null;
  const initials = (user.user_metadata?.full_name as string | undefined)
    ?.split(" ").map((w: string) => w[0]).join("").slice(0, 2).toUpperCase()
    ?? user.email?.slice(0, 2).toUpperCase() ?? "U";
  const avatar = user.user_metadata?.avatar_url as string | undefined;

  return (
    <div className="relative">
      <button onClick={() => setOpen((o) => !o)} className="flex h-8 w-8 items-center justify-center rounded-full bg-amber-500/20 text-xs font-bold text-amber-400 hover:bg-amber-500/30 transition-colors overflow-hidden">
        {avatar ? <img src={avatar} className="h-full w-full object-cover" alt="" /> : initials}
      </button>
      {open && (
        <div className="absolute right-0 top-10 z-50 w-52 rounded-xl border border-[var(--border-primary)] bg-[var(--bg-card)] shadow-xl p-1">
          <div className="px-3 py-2 border-b border-[var(--border-primary)] mb-1">
            <p className="text-xs font-semibold text-theme truncate">{user.user_metadata?.full_name ?? "User"}</p>
            <p className="text-[10px] text-muted-theme truncate">{user.email}</p>
          </div>
          <button onClick={() => { signOut(); setOpen(false); }}
            className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-xs text-red-400 hover:bg-red-500/10 transition-colors">
            <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
            </svg>
            Sign out
          </button>
        </div>
      )}
    </div>
  );
}

export default function App() {
  const theme = useThemeStore((s) => s.theme);
  const location = useLocation();
  const [tutorialOpen, setTutorialOpen] = useState(false);
  const initialize = useAuthStore((s) => s.initialize);

  const isCockpit = location.pathname === "/cockpit";

  useEffect(() => {
    document.documentElement.classList.toggle("light", theme === "light");
    document.documentElement.classList.toggle("dark", theme === "dark");
  }, [theme]);

  useEffect(() => { initialize(); }, [initialize]);

  useEffect(() => {
    if (!localStorage.getItem(STORAGE_KEY)) {
      setTutorialOpen(true);
    }
  }, []);

  // Cockpit gets a full-viewport layout with no outer nav/main wrapper
  if (isCockpit) {
    return (
      <>
        <Routes>
          <Route path="/cockpit" element={<AuthGuard><Cockpit /></AuthGuard>} />
        </Routes>
      </>
    );
  }

  return (
    <div className="relative min-h-screen">
      {/* Ambient background effects */}
      <div className="pointer-events-none fixed inset-0 overflow-hidden">
        <div
          className="absolute -top-40 -right-40 h-96 w-96 rounded-full opacity-20 blur-3xl"
          style={{ background: "radial-gradient(circle, rgba(245,158,11,0.3), transparent 70%)" }}
        />
        <div
          className="absolute -bottom-40 -left-40 h-96 w-96 rounded-full opacity-10 blur-3xl"
          style={{ background: "radial-gradient(circle, rgba(99,102,241,0.4), transparent 70%)" }}
        />
      </div>

      {/* Navigation */}
      <nav className="sticky top-0 z-50 border-b border-[var(--border-primary)] backdrop-blur-xl" style={{ background: "var(--bg-secondary)", opacity: 0.95 }}>
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3">
          {/* Logo */}
          <a href="/cockpit" className="flex items-center gap-2 group">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-amber-400 to-amber-600 shadow-lg shadow-amber-500/20 transition-shadow group-hover:shadow-amber-500/40">
              <svg className="h-4 w-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <span className="text-lg font-bold tracking-tight">
              <span className="text-theme">Land</span>
              <span className="bg-gradient-to-r from-amber-400 to-amber-500 bg-clip-text text-transparent"> It</span>
            </span>
          </a>

          {/* Nav links */}
          <div className="flex items-center gap-1">
            {NAV_LINKS.map((link) => (
              <NavLink
                key={link.href}
                {...link}
                active={location.pathname === link.href}
              />
            ))}
            <a
              href="/demo"
              className={`ml-1 flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm font-bold transition-all duration-200 ${
                location.pathname === "/demo"
                  ? "bg-gradient-to-r from-amber-500 to-amber-600 text-white shadow-lg shadow-amber-500/25"
                  : "border border-amber-500/30 text-amber-400 hover:bg-amber-500/10"
              }`}
            >
              <svg className="h-3.5 w-3.5" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" clipRule="evenodd" />
              </svg>
              Demo
            </a>

            {/* Open Cockpit CTA */}
            <a
              href="/cockpit"
              className="ml-2 flex items-center gap-1.5 rounded-lg bg-gradient-to-r from-emerald-500 to-emerald-600 px-3 py-2 text-sm font-bold text-white shadow-lg shadow-emerald-500/25 transition-all hover:shadow-emerald-500/40"
            >
              Open Cockpit
            </a>
          </div>

          {/* Help + Theme + User */}
          <div className="flex items-center gap-2">
            <button
              onClick={() => setTutorialOpen(true)}
              className="flex h-8 w-8 items-center justify-center rounded-full border border-[var(--border-primary)] text-muted-theme hover:border-amber-500/50 hover:text-amber-400 transition-all"
              aria-label="Open tutorial"
              title="How it works"
            >
              <span className="text-sm font-bold">?</span>
            </button>
            <ThemeToggle />
            <UserMenu />
          </div>
        </div>
      </nav>

      <Tutorial open={tutorialOpen} onClose={() => setTutorialOpen(false)} />

      {/* Page content */}
      <main className="relative mx-auto max-w-7xl px-4 py-8 sm:px-6">
        <div className="animate-fade-in">
          <Routes>
            {/* Public routes */}
            <Route path="/auth" element={<Auth />} />
            <Route path="/auth/callback" element={<AuthCallback />} />
            <Route path="/demo" element={<Demo />} />

            {/* Redirect / to /cockpit */}
            <Route path="/" element={<Navigate to="/cockpit" replace />} />

            {/* Protected routes */}
            <Route path="/dashboard" element={<AuthGuard><Dashboard /></AuthGuard>} />
            <Route path="/jobs" element={<AuthGuard><Jobs /></AuthGuard>} />
            <Route path="/tailor" element={<AuthGuard><Tailor /></AuthGuard>} />
            <Route path="/pitcher" element={<AuthGuard><Pitcher /></AuthGuard>} />
            <Route path="/coach" element={<AuthGuard><Coach /></AuthGuard>} />
            <Route path="/tracker" element={<AuthGuard><Tracker /></AuthGuard>} />
            <Route path="/analytics" element={<AuthGuard><Analytics /></AuthGuard>} />
            <Route path="/onboarding" element={<AuthGuard><Onboarding /></AuthGuard>} />
          </Routes>
        </div>
      </main>
    </div>
  );
}
