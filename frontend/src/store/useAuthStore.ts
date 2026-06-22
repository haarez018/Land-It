import { create } from "zustand";
import { persist } from "zustand/middleware";
import { supabase } from "../lib/supabase";
import type { Session, User } from "@supabase/supabase-js";

interface AuthState {
  user: User | null;
  session: Session | null;
  loading: boolean;
  setSession: (session: Session | null) => void;
  signInWithEmail: (email: string, password: string) => Promise<string | null>;
  signUpWithEmail: (email: string, password: string) => Promise<string | null>;
  signInWithOAuth: (provider: "google" | "github") => Promise<void>;
  signOut: () => Promise<void>;
  initialize: () => Promise<void>;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      session: null,
      loading: true,

      setSession: (session) =>
        set({ session, user: session?.user ?? null, loading: false }),

      initialize: async () => {
        if (!supabase) { set({ loading: false }); return; }
        set({ loading: true });
        const { data } = await supabase.auth.getSession();
        set({
          session: data.session,
          user: data.session?.user ?? null,
          loading: false,
        });
        supabase.auth.onAuthStateChange((_event: string, session: import("@supabase/supabase-js").Session | null) => {
          set({ session, user: session?.user ?? null, loading: false });
        });
      },

      signInWithEmail: async (email, password) => {
        if (!supabase) return "Supabase not configured — add env vars to frontend/.env";
        const { data, error } = await supabase.auth.signInWithPassword({ email, password });
        if (error) return error.message;
        set({ session: data.session, user: data.user });
        return null;
      },

      signUpWithEmail: async (email, password) => {
        if (!supabase) return "Supabase not configured — add env vars to frontend/.env";
        const { data, error } = await supabase.auth.signUp({ email, password });
        if (error) return error.message;
        if (data.session) set({ session: data.session, user: data.user });
        return null;
      },

      signInWithOAuth: async (provider) => {
        if (!supabase) return;
        const redirectTo = `${window.location.origin}/auth/callback`;
        await supabase.auth.signInWithOAuth({ provider, options: { redirectTo } });
      },

      signOut: async () => {
        if (supabase) await supabase.auth.signOut();
        set({ session: null, user: null });
      },
    }),
    {
      name: "landit-auth",
      partialize: (state) => ({ session: state.session, user: state.user }),
    }
  )
);
