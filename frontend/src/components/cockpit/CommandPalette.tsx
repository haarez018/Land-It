import { useState, useEffect, useRef, useCallback } from "react";
import { Search, BarChart2, Scissors, Send, Mic, Compass } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { useThemeStore } from "../../store/useThemeStore";

interface Command {
  id: string;
  label: string;
  shortcut?: string;
  icon: React.ElementType;
  action: string;
  arg?: string;
}

const BASE_COMMANDS: Command[] = [
  { id: "tailor", label: "Tailor my resume for...", shortcut: "T", icon: Scissors, action: "tailor" },
  { id: "discover", label: "Discover jobs for...", shortcut: "D", icon: Compass, action: "discover" },
  { id: "pitch", label: "Draft cold outreach to...", shortcut: "P", icon: Send, action: "pitch" },
  { id: "interview", label: "Start mock interview for...", shortcut: "I", icon: Mic, action: "interview" },
  { id: "analytics", label: "Show analytics", shortcut: "A", icon: BarChart2, action: "navigate", arg: "/analytics" },
  { id: "calibration", label: "Show calibration", shortcut: "C", icon: BarChart2, action: "navigate", arg: "/analytics?tab=calibration" },
];

interface CommandPaletteProps {
  open: boolean;
  onClose: () => void;
  onCommand: (action: string, arg?: string, query?: string) => void;
}

export default function CommandPalette({ open, onClose, onCommand }: CommandPaletteProps) {
  const [query, setQuery] = useState("");
  const [selectedIdx, setSelectedIdx] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const theme = useThemeStore((s) => s.theme);
  const isDark = theme === "dark";

  const filtered = BASE_COMMANDS.filter((c) =>
    c.label.toLowerCase().includes(query.toLowerCase())
  );

  useEffect(() => {
    if (open) {
      setQuery("");
      setSelectedIdx(0);
      setTimeout(() => inputRef.current?.focus(), 60);
    }
  }, [open]);

  useEffect(() => { setSelectedIdx(0); }, [query]);

  const handleKey = useCallback(
    (e: KeyboardEvent) => {
      if (!open) return;
      if (e.key === "Escape") { onClose(); return; }
      if (e.key === "ArrowDown") { e.preventDefault(); setSelectedIdx((i) => Math.min(i + 1, filtered.length - 1)); }
      if (e.key === "ArrowUp") { e.preventDefault(); setSelectedIdx((i) => Math.max(i - 1, 0)); }
      if (e.key === "Enter" && filtered[selectedIdx]) {
        const cmd = filtered[selectedIdx];
        onCommand(cmd.action, cmd.arg, query);
        onClose();
      }
    },
    [open, filtered, selectedIdx, query, onClose, onCommand]
  );

  useEffect(() => {
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [handleKey]);

  const glassBg = isDark
    ? "rgba(13,17,23,0.92)"
    : "rgba(255,255,255,0.92)";

  const glassBorder = isDark ? "rgba(255,255,255,0.1)" : "rgba(0,0,0,0.1)";
  const inputDivider = isDark ? "rgba(255,255,255,0.07)" : "rgba(0,0,0,0.07)";
  const textPrimary = isDark ? "#f0f4ff" : "#111827";
  const textDim = isDark ? "#94a3b8" : "#475569";
  const textMute = isDark ? "#475569" : "#94a3b8";
  const rowActive = isDark ? "rgba(0,245,160,0.06)" : "rgba(0,245,160,0.08)";


  return (
    <AnimatePresence>
      {open && (
        <motion.div
          id="cockpit-command-palette"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.15 }}
          className="fixed inset-0 z-50 flex items-center justify-center"
          style={{
            backgroundColor: isDark ? "rgba(6,9,20,0.8)" : "rgba(230,234,242,0.75)",
            backdropFilter: "blur(20px)",
            WebkitBackdropFilter: "blur(20px)",
          }}
          onClick={(e) => e.target === e.currentTarget && onClose()}
        >
          <motion.div
            initial={{ opacity: 0, scale: 0.94, y: -20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.94, y: -10 }}
            transition={{ type: "spring", stiffness: 350, damping: 28 }}
            className="w-[560px] max-h-[60vh] flex flex-col rounded-2xl overflow-hidden"
            style={{
              backgroundColor: glassBg,
              border: `1px solid ${glassBorder}`,
              boxShadow: isDark
                ? "0 40px 80px rgba(0,0,0,0.7), 0 0 0 1px rgba(255,255,255,0.05), inset 0 1px 0 rgba(255,255,255,0.08)"
                : "0 24px 48px rgba(99,102,241,0.15), 0 0 0 1px rgba(0,0,0,0.06), inset 0 1px 0 rgba(255,255,255,0.9)",
              backdropFilter: "blur(40px)",
              WebkitBackdropFilter: "blur(40px)",
            }}
          >
            {/* Input */}
            <div
              className="flex items-center gap-3 px-4 py-3.5"
              style={{ borderBottom: `1px solid ${inputDivider}` }}
            >
              <Search size={15} strokeWidth={1.5} style={{ color: textMute, flexShrink: 0 }} />
              <input
                id="cockpit-cmd-input"
                ref={inputRef}
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="type a command or paste a JD URL..."
                className="flex-1 bg-transparent font-mono text-sm outline-none"
                style={{
                  color: textPrimary,
                  caretColor: "#00F5A0",
                }}
              />
              <span
                className="font-mono text-[10px] rounded-lg px-2 py-0.5"
                style={{
                  color: textMute,
                  background: isDark ? "rgba(255,255,255,0.05)" : "rgba(0,0,0,0.05)",
                  border: `1px solid ${isDark ? "rgba(255,255,255,0.08)" : "rgba(0,0,0,0.08)"}`,
                }}
              >
                Esc
              </span>
            </div>

            {/* Commands */}
            <div className="overflow-y-auto">
              {filtered.length === 0 ? (
                <div className="px-4 py-8 text-center font-mono text-[11px]" style={{ color: textMute }}>
                  no matching commands
                </div>
              ) : (
                filtered.map((cmd, i) => {
                  const Icon = cmd.icon;
                  const isSelected = i === selectedIdx;
                  return (
                    <motion.button
                      key={cmd.id}
                      id={`cockpit-cmd-${cmd.id}`}
                      onClick={() => { onCommand(cmd.action, cmd.arg, query); onClose(); }}
                      onMouseEnter={() => setSelectedIdx(i)}
                      whileHover={{ x: 3 }}
                      className="flex w-full items-center gap-3 px-4 py-3 text-left transition-colors"
                      style={{
                        backgroundColor: isSelected ? rowActive : undefined,
                        borderLeft: isSelected ? "2px solid #00F5A0" : "2px solid transparent",
                      }}
                    >
                      <div
                        className="flex h-7 w-7 items-center justify-center rounded-xl shrink-0"
                        style={{
                          background: isSelected
                            ? "linear-gradient(135deg, rgba(0,245,160,0.2), rgba(138,43,226,0.15))"
                            : isDark ? "rgba(255,255,255,0.05)" : "rgba(0,0,0,0.04)",
                          border: `1px solid ${isSelected ? "rgba(0,245,160,0.3)" : isDark ? "rgba(255,255,255,0.08)" : "rgba(0,0,0,0.08)"}`,
                        }}
                      >
                        <Icon
                          size={13}
                          strokeWidth={1.5}
                          style={{ color: isSelected ? "#00F5A0" : textMute }}
                        />
                      </div>
                      <span
                        className="flex-1 font-sans text-[13px]"
                        style={{ color: isSelected ? textPrimary : textDim }}
                      >
                        {cmd.label}
                      </span>
                      {cmd.shortcut && (
                        <span
                          className="font-mono text-[10px] rounded px-1.5 py-0.5"
                          style={{
                            color: textMute,
                            background: isDark ? "rgba(255,255,255,0.05)" : "rgba(0,0,0,0.04)",
                          }}
                        >
                          {cmd.shortcut}
                        </span>
                      )}
                    </motion.button>
                  );
                })
              )}
            </div>

            {/* Footer */}
            <div
              className="flex items-center justify-end gap-4 px-4 py-2"
              style={{ borderTop: `1px solid ${inputDivider}` }}
            >
              <span className="font-mono text-[9px]" style={{ color: textMute }}>↑↓ navigate</span>
              <span className="font-mono text-[9px]" style={{ color: textMute }}>↵ select</span>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
