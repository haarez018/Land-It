/** Handles the OAuth redirect from Supabase — exchanges code for session then redirects to /. */

import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { supabase } from "../lib/supabase";
import { useAuthStore } from "../store/useAuthStore";

export default function AuthCallback() {
  const navigate = useNavigate();
  const setSession = useAuthStore((s) => s.setSession);

  useEffect(() => {
    if (!supabase) { navigate("/", { replace: true }); return; }
    supabase.auth.getSession().then(({ data }: { data: { session: import("@supabase/supabase-js").Session | null } }) => {
      setSession(data.session);
      navigate("/", { replace: true });
    });
  }, [navigate, setSession]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-[var(--bg-primary)]">
      <div className="flex flex-col items-center gap-4">
        <div className="h-10 w-10 animate-spin rounded-full border-4 border-amber-500 border-t-transparent" />
        <p className="text-sm text-muted-theme">Completing sign-in…</p>
      </div>
    </div>
  );
}
