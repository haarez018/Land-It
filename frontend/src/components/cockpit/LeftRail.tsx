import { Radio, History } from "lucide-react";
import { motion } from "framer-motion";
import { DEMO_APPLICATIONS } from "../../lib/demoData";
import { useThemeStore } from "../../store/useThemeStore";
import { useAgentStore } from "../../store/useAgentStore";

type PipelineStatus = "Discovered" | "Tailored" | "Applied" | "Interviewing" | "Closed";

const PIPELINE_STATUSES: PipelineStatus[] = [
  "Discovered", "Tailored", "Applied", "Interviewing", "Closed",
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
}

export default function LeftRail({ activeFilter, onFilterChange }: LeftRailProps) {
  const theme = useThemeStore((s) => s.theme);
  const isDark = theme === "dark";
  const agents = useAgentStore((s) => s.agents);

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

  const recentActivities = agents
    .map((agent) => ({
      id: agent.id,
      title: agent.name,
      desc: agent.lastOutput,
      time: "Active",
    }))
    .slice(0, 4);

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

      {/* Lemma Pod Connection Status */}
      <div className="px-4">
        <p className="font-mono text-[10px] uppercase tracking-wider mb-3" style={{ color: textMute }}>
          Pod Connection
        </p>

        <div
          className="rounded-xl p-3 border transition-all"
          style={{
            backgroundColor: isDark ? "rgba(138,43,226,0.04)" : "rgba(138,43,226,0.02)",
            borderColor: isDark ? "rgba(138,43,226,0.15)" : "rgba(138,43,226,0.1)",
          }}
        >
          <div className="flex items-center gap-2 mb-2">
            <Radio size={14} className="animate-pulse shrink-0" style={{ color: "#00F5A0" }} />
            <span className="font-sans text-xs font-semibold truncate" style={{ color: textPrimary }}>
              land-it-mission-control
            </span>
          </div>

          <div className="space-y-1 text-[11px] font-mono" style={{ color: textDim }}>
            <div className="flex justify-between">
              <span>Status:</span>
              <span className="flex items-center gap-1 font-semibold" style={{ color: "#00F5A0" }}>
                Connected
              </span>
            </div>
            <div className="flex justify-between">
              <span>ID:</span>
              <span className="text-[10px] opacity-80" title="019f1286-4259-72fe-8f28-b43a4a567390">
                019f1286...
              </span>
            </div>
            <div className="flex justify-between">
              <span>Org:</span>
              <span className="text-[10px] opacity-80 truncate max-w-[100px]">
                Haarez_018
              </span>
            </div>
            <div className="flex justify-between">
              <span>Engine:</span>
              <span className="text-[10px] opacity-80">
                lemma-sdk
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Divider */}
      <div className="mx-4 my-4" style={{ borderTop: `1px solid ${dividerColor}` }} />

      {/* Recent Activity Section */}
      <div className="px-4 pb-4">
        <p className="font-mono text-[10px] uppercase tracking-wider mb-3 flex items-center gap-1.5" style={{ color: textMute }}>
          <History size={11} className="shrink-0" />
          Recent Activity
        </p>

        <div className="space-y-3">
          {recentActivities.map((act) => (
            <div key={act.id} className="text-[11px] leading-snug">
              <div className="flex items-center justify-between mb-0.5">
                <span className="font-semibold uppercase tracking-wider font-mono text-[9px]" style={{ color: "#00F5A0" }}>
                  {act.title}
                </span>
                <span className="font-mono text-[9px] opacity-50" style={{ color: textMute }}>
                  {act.time}
                </span>
              </div>
              <p className="line-clamp-2" style={{ color: textDim }}>
                {act.desc}
              </p>
            </div>
          ))}
        </div>
      </div>
    </aside>
  );
}
