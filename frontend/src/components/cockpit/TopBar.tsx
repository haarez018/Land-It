import { useState, useEffect, useRef } from "react";
import { Sun, Moon } from "lucide-react";
import { useAuthStore } from "../../store/useAuthStore";
import { useThemeStore } from "../../store/useThemeStore";

interface TopBarProps {
  onCommandPaletteOpen: () => void;
}

export default function TopBar({ onCommandPaletteOpen }: TopBarProps) {
  const { user, signOut } = useAuthStore();
  const { theme, toggle } = useThemeStore();
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const isDark = theme === "dark";

  const initials =
    (user?.user_metadata?.full_name as string | undefined)
      ?.split(" ").map((w: string) => w[0]).join("").slice(0, 2).toUpperCase() ??
    user?.email?.slice(0, 2).toUpperCase() ?? "U";

  const avatar = user?.user_metadata?.avatar_url as string | undefined;

  useEffect(() => {
    function outside(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) setMenuOpen(false);
    }
    document.addEventListener("mousedown", outside);
    return () => document.removeEventListener("mousedown", outside);
  }, []);

  const glassBase = isDark
    ? "bg-white/[0.04] backdrop-blur-xl border-b border-white/[0.08]"
    : "bg-white/60 backdrop-blur-xl border-b border-white/60";

  const pillBase = isDark
    ? "bg-white/[0.06] border border-white/[0.1] text-cp-text-dim hover:border-cp-accent hover:text-cp-accent"
    : "bg-black/[0.04] border border-black/[0.1] text-slate-500 hover:border-cp-accent hover:text-cp-accent";

  const dropdownBg = isDark
    ? "bg-[#0d1117]/90 backdrop-blur-2xl border border-white/[0.1]"
    : "bg-white/90 backdrop-blur-2xl border border-black/[0.1]";

  return (
    <header
      id="cockpit-topbar"
      className={`flex h-12 shrink-0 items-center justify-between px-4 ${glassBase}`}
    >
      {/* Left: Logo */}
      <a
        href="/pipeline"
        className="flex flex-col justify-center cursor-pointer group"
      >
        <span
          className={`font-sans text-sm font-semibold tracking-widest ${isDark ? "text-cp-text" : "text-slate-800"} group-hover:text-cp-accent transition-colors`}
          style={{ letterSpacing: "0.22em" }}
        >
          LAND IT
        </span>
        <span className="font-mono text-[9px] text-cp-text-mute leading-none mt-0.5 group-hover:text-cp-text-dim transition-colors">
          your job search, on autopilot
        </span>
      </a>

      {/* Center: Command palette trigger */}
      <button
        id="cockpit-cmd-trigger"
        onClick={onCommandPaletteOpen}
        className={`flex items-center gap-2 rounded-xl px-4 py-1.5 font-mono text-xs transition-all duration-200 ${pillBase}`}
      >
        <span className="opacity-50">⌘K</span>
        <span>Command</span>
      </button>

      {/* Right: Theme toggle + Avatar */}
      <div className="flex items-center gap-3">
        {/* Theme toggle */}
        <button
          id="cockpit-theme-toggle"
          onClick={toggle}
          className={`flex h-7 w-7 items-center justify-center rounded-xl transition-all duration-200 ${pillBase}`}
          aria-label="Toggle theme"
        >
          {isDark
            ? <Sun size={13} strokeWidth={1.5} />
            : <Moon size={13} strokeWidth={1.5} />
          }
        </button>

        {/* Avatar + dropdown */}
        <div className="relative" ref={menuRef}>
          <button
            id="cockpit-user-avatar"
            onClick={() => setMenuOpen((o) => !o)}
            className="flex h-7 w-7 items-center justify-center rounded-full font-mono text-xs font-semibold text-cp-bg overflow-hidden transition-all hover:scale-105"
            style={{
              background: "linear-gradient(135deg, #00F5A0, #8A2BE2)",
              boxShadow: "0 0 12px rgba(0,245,160,0.3)",
            }}
          >
            {avatar
              ? <img src={avatar} className="h-full w-full object-cover" alt="" />
              : initials
            }
          </button>

          {menuOpen && (
            <div
              className={`absolute right-0 top-9 z-50 w-48 rounded-2xl py-1 ${dropdownBg}`}
              style={{ boxShadow: "0 24px 48px rgba(0,0,0,0.4)" }}
            >
              <div className={`border-b px-3 py-2 mb-1 ${isDark ? "border-white/[0.08]" : "border-black/[0.06]"}`}>
                <p className={`font-sans text-xs font-medium truncate ${isDark ? "text-cp-text" : "text-slate-800"}`}>
                  {user?.user_metadata?.full_name ?? user?.email ?? "User"}
                </p>
                <p className="font-mono text-[10px] text-cp-text-mute truncate mt-0.5">
                  {user?.email ?? ""}
                </p>
              </div>
              <button
                onClick={() => { signOut(); setMenuOpen(false); }}
                className="flex w-full items-center gap-2 px-3 py-1.5 font-sans text-xs text-cp-danger transition-colors hover:bg-cp-danger/10 rounded-xl mx-0"
              >
                Sign out
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
