import { motion } from "framer-motion";
import { Radar, Scissors, Send, Mic, BarChart2, Calendar } from "lucide-react";
import { useAgentStore } from "../../store/useAgentStore";
import type { AgentStatus } from "../../store/useAgentStore";
import { useThemeStore } from "../../store/useThemeStore";

const AGENT_ICONS = {
  scout: Radar, tailor: Scissors, pitcher: Send,
  coach: Mic, tracker: BarChart2, planner: Calendar,
};

function StatusDot({ status }: { status: AgentStatus }) {
  const colors: Record<AgentStatus, string> = {
    idle: "#475569",
    thinking: "#8892A6",
    working: "#00F5A0",
    output: "#00F5A0",
  };
  return (
    <span
      className={`inline-block h-1.5 w-1.5 rounded-full shrink-0 ${status === "thinking" ? "animate-dot-pulse" : ""}`}
      style={{
        backgroundColor: colors[status],
        boxShadow: (status === "working" || status === "output")
          ? "0 0 6px rgba(0,245,160,0.8)"
          : undefined,
      }}
    />
  );
}

interface AgentStripProps {
  onAgentClick: (agentId: string) => void;
}

export default function AgentStrip({ onAgentClick }: AgentStripProps) {
  const agents = useAgentStore((s) => s.agents);
  const activeAgentId = useAgentStore((s) => s.activeAgentId);
  const theme = useThemeStore((s) => s.theme);
  const isDark = theme === "dark";

  const stripBg = isDark
    ? "bg-white/[0.02] backdrop-blur-xl border-b border-white/[0.06]"
    : "bg-white/40 backdrop-blur-xl border-b border-white/50";

  return (
    <div
      id="cockpit-agent-strip"
      className={`flex h-14 shrink-0 items-center gap-2 px-3 pb-1 ${stripBg}`}
    >
      {agents.map((agent, i) => {
        const Icon = AGENT_ICONS[agent.id as keyof typeof AGENT_ICONS];
        const isActive = activeAgentId === agent.id;
        const isWorking = agent.status === "working";
        const isOutput = agent.status === "output";

        const pillBg = isDark
          ? isActive
            ? "rgba(0,245,160,0.08)"
            : isWorking
            ? "rgba(0,245,160,0.05)"
            : "rgba(255,255,255,0.04)"
          : isActive
          ? "rgba(0,245,160,0.12)"
          : "rgba(255,255,255,0.55)";

        const borderColor = isActive
          ? "rgba(0,245,160,0.6)"
          : isWorking
          ? "rgba(0,245,160,0.35)"
          : isDark
          ? "rgba(255,255,255,0.08)"
          : "rgba(0,0,0,0.08)";

        return (
          <motion.button
            key={agent.id}
            id={`cockpit-agent-${agent.id}`}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.07, duration: 0.25, ease: "easeOut" }}
            whileHover={{ y: -2, scale: 1.02 }}
            whileTap={{ scale: 0.97 }}
            onClick={() => onAgentClick(agent.id)}
            className={`relative flex flex-1 items-center justify-center gap-2 overflow-hidden rounded-xl border h-10 transition-colors cursor-pointer backdrop-blur-sm ${isWorking ? "pill-working" : ""}`}
            style={{
              backgroundColor: pillBg,
              borderColor,
              boxShadow: isActive
                ? "0 0 20px rgba(0,245,160,0.15), inset 0 1px 0 rgba(255,255,255,0.1)"
                : isWorking
                ? undefined
                : isDark
                ? "inset 0 1px 0 rgba(255,255,255,0.05)"
                : "inset 0 1px 0 rgba(255,255,255,0.8)",
            }}
          >
            {Icon && (
              <Icon
                size={14}
                strokeWidth={1.5}
                style={{
                  color: isActive || isWorking || isOutput ? "#00F5A0" : isDark ? "#8892A6" : "#64748b",
                }}
              />
            )}
            <span
              className="font-mono text-[10px] uppercase tracking-wider"
              style={{
                color: isActive || isWorking || isOutput ? "#00F5A0" : isDark ? "#8892A6" : "#64748b",
              }}
            >
              {agent.name}
            </span>
            <StatusDot status={agent.status} />

            {/* Working shimmer sweep */}
            {isWorking && (
              <span
                className="absolute inset-0 rounded-xl pointer-events-none"
                style={{
                  background: "linear-gradient(90deg, transparent 0%, rgba(0,245,160,0.08) 50%, transparent 100%)",
                  backgroundSize: "200% 100%",
                  animation: "shimmerSweep 2s linear infinite",
                }}
              />
            )}
          </motion.button>
        );
      })}
    </div>
  );
}
