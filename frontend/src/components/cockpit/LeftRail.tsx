import { Search, Scissors, Mic, Mail } from "lucide-react";
import { motion } from "framer-motion";
import { DEMO_APPLICATIONS } from "../../lib/demoData";
import { useThemeStore } from "../../store/useThemeStore";

type PipelineStatus = "Discovered" | "Tailored" | "Applied" | "Interviewing" | "Closed";

const PIPELINE_STATUSES: PipelineStatus[] = [
  "Discovered", "Tailored", "Applied", "Interviewing", "Closed",
];

const QUICK_ACTIONS = [
  { label: "Discover Jobs", icon: Search, action: "discover" },
  { label: "Tailor a Resume", icon: Scissors, action: "tailor" },
  { label: "Mock Interview", icon: Mic, action: "coach" },
  { label: "Write Cover Letter", icon: Mail, action: "pitcher" },
];

const STATUS_DOT_COLORS: Record<PipelineStatus, string> = {
  Discovered: "#8892A6",
  Tailored: "#8892A6",
  Applied: "#FFB020",
  Interviewing: "#00F5A0",
  Closed: "#475569",
};

interface LeftRailProps {
  activeFilter: PipelineStatus | null;
  onFilterChange: (status: PipelineStatus | null) => void;
  onQuickAction: (action: string) => void;
}

export default function LeftRail({ activeFilter, onFilterChange, onQuickAction }: LeftRailProps) {
  const theme = useThemeStore((s) => s.theme);
  const isDark = theme === "dark";

  const counts = PIPELINE_STATUSES.reduce<Record<PipelineStatus, number>>(
    (acc, s) => { acc[s] = DEMO_APPLICATIONS.filter((a) => a.status === s).length; return acc; },
    { Discovered: 0, Tailored: 0, Applied: 0, Interviewing: 0, Closed: 0 }
  );
  const maxCount = Math.max(...Object.values(counts), 1);

  const glassPanel = isDark
    ? "bg-white/[0.04] backdrop-blur-xl border border-white/[0.08] rounded-2xl"
    : "bg-white/55 backdrop-blur-xl border border-white/60 rounded-2xl";

  const panelShadow = isDark
    ? { boxShadow: "inset 0 1px 0 rgba(255,255,255,0.06), 0 20px 40px rgba(0,0,0,0.35)" }
    : { boxShadow: "inset 0 1px 0 rgba(255,255,255,0.9), 0 8px 24px rgba(99,102,241,0.07)" };

  const textPrimary = isDark ? "#f0f4ff" : "#111827";
  const textDim = isDark ? "#94a3b8" : "#475569";
  const textMute = isDark ? "#475569" : "#94a3b8";
  const hoverBg = isDark ? "hover:bg-white/[0.06]" : "hover:bg-black/[0.04]";
  const dividerColor = isDark ? "rgba(255,255,255,0.06)" : "rgba(0,0,0,0.06)";

  return (
    <aside
      id="cockpit-left-rail"
      className={`flex w-60 shrink-0 flex-col overflow-y-auto ${glassPanel}`}
      style={panelShadow}
    >
      {/* Pipeline section */}
      <div className="px-4 pt-4">
        <p className="font-mono text-[10px] uppercase tracking-wider mb-3" style={{ color: textMute }}>
          Pipeline
        </p>
        <div className="space-y-0.5">
          {PIPELINE_STATUSES.map((status) => {
            const count = counts[status];
            const barPct = count === 0 ? 0 : (count / maxCount) * 100;
            const isActive = activeFilter === status;

            return (
              <motion.button
                key={status}
                id={`cockpit-filter-${status.toLowerCase()}`}
                whileHover={{ x: 2 }}
                onClick={() => onFilterChange(isActive ? null : status)}
                className={`relative w-full flex items-center justify-between rounded-xl px-3 py-2 text-left transition-all ${hoverBg}`}
                style={{
                  backgroundColor: isActive
                    ? isDark ? "rgba(0,245,160,0.08)" : "rgba(0,245,160,0.1)"
                    : undefined,
                  boxShadow: isActive ? "inset 1px 0 0 rgba(0,245,160,0.5)" : undefined,
                }}
              >
                <div className="flex items-center gap-2">
                  <span
                    className="h-1.5 w-1.5 rounded-full shrink-0"
                    style={{
                      backgroundColor: STATUS_DOT_COLORS[status],
                      boxShadow: isActive ? "0 0 6px rgba(0,245,160,0.6)" : undefined,
                    }}
                  />
                  <span
                    className="font-sans text-[13px]"
                    style={{ color: isActive ? "#00F5A0" : textPrimary }}
                  >
                    {status}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  {count > 0 && (
                    <div
                      className="h-0.5 rounded-full"
                      style={{
                        width: `${Math.max(barPct * 0.32, 4)}px`,
                        backgroundColor: isActive ? "#00F5A0" : "#475569",
                        opacity: isActive ? 1 : 0.5,
                      }}
                    />
                  )}
                  <span className="font-mono text-[12px]" style={{ color: textDim }}>{count}</span>
                </div>
              </motion.button>
            );
          })}
        </div>
      </div>

      {/* Divider */}
      <div className="mx-4 my-4" style={{ borderTop: `1px solid ${dividerColor}` }} />

      {/* Quick actions */}
      <div className="px-4">
        <p className="font-mono text-[10px] uppercase tracking-wider mb-3" style={{ color: textMute }}>
          Quick Actions
        </p>
        <div className="space-y-0.5">
          {QUICK_ACTIONS.map(({ label, icon: Icon, action }) => (
            <motion.button
              key={action}
              id={`cockpit-action-${action}`}
              whileHover={{ x: 2 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => onQuickAction(action)}
              className={`flex w-full items-center gap-2.5 rounded-xl px-3 h-9 text-left transition-all ${hoverBg}`}
            >
              <Icon size={14} strokeWidth={1.5} style={{ color: textMute }} />
              <span className="font-sans text-xs" style={{ color: textDim }}>{label}</span>
            </motion.button>
          ))}
        </div>
      </div>

      <div className="flex-1" />

      {/* Lemma pod */}
      <div
        className="px-4 py-3 mx-2 mb-2 rounded-xl"
        style={{
          background: isDark ? "rgba(138,43,226,0.08)" : "rgba(138,43,226,0.06)",
          border: "1px solid rgba(138,43,226,0.2)",
        }}
      >
        <p className="font-mono text-[10px] leading-relaxed" style={{ color: textMute }}>
          pod: mission-control
          <br />
          <span style={{ color: "#00F5A0" }}>●</span> synced 2s ago
        </p>
      </div>
    </aside>
  );
}
