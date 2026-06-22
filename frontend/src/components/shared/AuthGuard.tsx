/** Redirect unauthenticated users to /auth. Passthrough when Supabase is not configured (local dev). */

import { Navigate } from "react-router-dom";
import { useAuthStore } from "../../store/useAuthStore";
import { supabaseConfigured } from "../../lib/supabase";

export default function AuthGuard({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuthStore();

  // No Supabase configured → skip auth entirely (local dev without .env)
  if (!supabaseConfigured) return <>{children}</>;

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[var(--bg-primary)]">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-amber-500 border-t-transparent" />
      </div>
    );
  }

  if (!user) return <Navigate to="/auth" replace />;

  return <>{children}</>;
}
