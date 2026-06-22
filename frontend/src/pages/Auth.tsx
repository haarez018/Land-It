/** Sign-in / Sign-up page — email+password + Google OAuth. */

import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuthStore } from "../store/useAuthStore";

type Mode = "login" | "signup";

export default function Auth() {
  const navigate = useNavigate();
  const { user, signInWithEmail, signUpWithEmail, signInWithOAuth } = useAuthStore();

  const [mode, setMode] = useState<Mode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");
  const [loading, setLoading] = useState(false);

  // Already logged in → go to dashboard
  useEffect(() => {
    if (user) navigate("/", { replace: true });
  }, [user, navigate]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setInfo("");
    setLoading(true);

    const err =
      mode === "login"
        ? await signInWithEmail(email, password)
        : await signUpWithEmail(email, password);

    setLoading(false);
    if (err) {
      setError(err);
    } else if (mode === "signup") {
      setInfo("Check your email to confirm your account, then sign in.");
    }
  };

  const handleOAuth = async (provider: "google" | "github") => {
    setError("");
    await signInWithOAuth(provider);
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-[var(--bg-primary)] px-4">
      {/* Ambient glow */}
      <div className="pointer-events-none fixed inset-0 overflow-hidden">
        <div className="absolute -top-40 -right-40 h-96 w-96 rounded-full opacity-20 blur-3xl"
          style={{ background: "radial-gradient(circle, rgba(245,158,11,0.3), transparent 70%)" }} />
        <div className="absolute -bottom-40 -left-40 h-96 w-96 rounded-full opacity-10 blur-3xl"
          style={{ background: "radial-gradient(circle, rgba(99,102,241,0.4), transparent 70%)" }} />
      </div>

      <div className="relative w-full max-w-sm">
        {/* Logo */}
        <div className="mb-8 flex flex-col items-center gap-3">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-amber-400 to-amber-600 shadow-lg shadow-amber-500/30">
            <svg className="h-6 w-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <div className="text-center">
            <h1 className="text-2xl font-bold">
              <span className="text-theme">Land</span>
              <span className="bg-gradient-to-r from-amber-400 to-amber-500 bg-clip-text text-transparent"> It</span>
            </h1>
            <p className="mt-1 text-sm text-muted-theme">Your AI-powered job search co-pilot</p>
          </div>
        </div>

        {/* Card */}
        <div className="rounded-2xl border border-[var(--border-primary)] bg-[var(--bg-card)] p-6 shadow-2xl shadow-black/20">
          {/* Tab toggle */}
          <div className="mb-6 flex rounded-lg bg-[var(--bg-tertiary)] p-1">
            {(["login", "signup"] as Mode[]).map((m) => (
              <button
                key={m}
                onClick={() => { setMode(m); setError(""); setInfo(""); }}
                className={`flex-1 rounded-md py-1.5 text-sm font-semibold transition-all ${
                  mode === m
                    ? "bg-[var(--bg-card)] text-theme shadow-sm"
                    : "text-muted-theme hover:text-theme"
                }`}
              >
                {m === "login" ? "Sign In" : "Sign Up"}
              </button>
            ))}
          </div>

          {/* OAuth buttons */}
          <div className="space-y-2">
            <button
              onClick={() => handleOAuth("google")}
              className="flex w-full items-center justify-center gap-3 rounded-lg border border-[var(--border-primary)] bg-[var(--bg-tertiary)] px-4 py-2.5 text-sm font-semibold text-theme transition-all hover:border-[var(--border-hover)] hover:bg-[var(--bg-card)]"
            >
              <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none">
                <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
                <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
                <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
                <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
              </svg>
              Continue with Google
            </button>

            <button
              onClick={() => handleOAuth("github")}
              className="flex w-full items-center justify-center gap-3 rounded-lg border border-[var(--border-primary)] bg-[var(--bg-tertiary)] px-4 py-2.5 text-sm font-semibold text-theme transition-all hover:border-[var(--border-hover)] hover:bg-[var(--bg-card)]"
            >
              <svg viewBox="0 0 24 24" className="h-4 w-4 fill-current text-theme">
                <path d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" />
              </svg>
              Continue with GitHub
            </button>
          </div>

          <div className="my-5 flex items-center gap-3">
            <div className="flex-1 border-t border-[var(--border-primary)]" />
            <span className="text-xs text-muted-theme">or</span>
            <div className="flex-1 border-t border-[var(--border-primary)]" />
          </div>

          {/* Email / password form */}
          <form onSubmit={handleSubmit} className="space-y-3">
            <div>
              <label className="mb-1 block text-xs font-semibold text-theme-secondary">Email</label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                className="w-full input-theme rounded-lg px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-semibold text-theme-secondary">Password</label>
              <input
                type="password"
                required
                minLength={6}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full input-theme rounded-lg px-3 py-2 text-sm"
              />
            </div>

            {error && (
              <div className="rounded-lg bg-red-500/10 border border-red-500/30 px-3 py-2 text-xs text-red-400">
                {error}
              </div>
            )}
            {info && (
              <div className="rounded-lg bg-emerald-500/10 border border-emerald-500/30 px-3 py-2 text-xs text-emerald-400">
                {info}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full rounded-lg bg-gradient-to-r from-amber-500 to-amber-600 py-2.5 text-sm font-bold text-white shadow-md shadow-amber-500/20 transition-all hover:opacity-90 disabled:opacity-50"
            >
              {loading ? "Please wait..." : mode === "login" ? "Sign In" : "Create Account"}
            </button>
          </form>

          <p className="mt-4 text-center text-[11px] text-muted-theme">
            By continuing you agree to our{" "}
            <span className="text-amber-400 cursor-pointer hover:underline">Terms</span> and{" "}
            <span className="text-amber-400 cursor-pointer hover:underline">Privacy Policy</span>
          </p>
        </div>
      </div>
    </div>
  );
}
