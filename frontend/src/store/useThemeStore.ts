import { create } from "zustand";

interface ThemeState {
  theme: "dark" | "light";
  toggle: () => void;
  setTheme: (t: "dark" | "light") => void;
}

const saved = typeof window !== "undefined" ? localStorage.getItem("land-it-theme") : null;

export const useThemeStore = create<ThemeState>((set) => ({
  theme: (saved as "dark" | "light") || "dark",
  toggle: () =>
    set((s) => {
      const next = s.theme === "dark" ? "light" : "dark";
      localStorage.setItem("land-it-theme", next);
      return { theme: next };
    }),
  setTheme: (t) => {
    localStorage.setItem("land-it-theme", t);
    set({ theme: t });
  },
}));
