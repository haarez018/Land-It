import { createClient } from "@supabase/supabase-js";

const url = import.meta.env.VITE_SUPABASE_URL;
const key = import.meta.env.VITE_SUPABASE_ANON_KEY;

export const supabaseConfigured = Boolean(url && key);

if (!supabaseConfigured) {
  console.warn(
    "[Land It] Supabase not configured — copy frontend/.env.example → frontend/.env and fill in your keys."
  );
}

// Only initialise when both vars are present. If not, we export null and the
// auth store / API client handle that gracefully.
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const supabase = supabaseConfigured ? createClient(url, key) : (null as any);
