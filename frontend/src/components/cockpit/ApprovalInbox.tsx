import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Check, Edit2, X } from "lucide-react";
import { DEMO_APPROVALS } from "../../lib/demoData";
import type { DemoApproval } from "../../lib/demoData";
import { useAgentStore } from "../../store/useAgentStore";
import { useThemeStore } from "../../store/useThemeStore";

const _API_BASE = import.meta.env.VITE_API_URL ? `${import.meta.env.VITE_API_URL}/api` : "/api";

async function _lemmaApprove(id: string) {
  try { await fetch(`${_API_BASE}/lemma/approvals/${id}/approve`, { method: "POST" }); } catch { /* pod offline */ }
}
async function _lemmaSkip(id: string) {
  try { await fetch(`${_API_BASE}/lemma/approvals/${id}/skip`, { method: "POST" }); } catch { /* pod offline */ }
}

interface ApprovalCardProps {
  approval: DemoApproval;
  onApprove: (id: string) => void;
  onSkip: (id: string) => void;
  isDark: boolean;
}

function ApprovalCard({ approval, onApprove, onSkip, isDark }: ApprovalCardProps) {
  const cardBg = isDark
    ? "rgba(255,255,255,0.04)"
    : "rgba(255,255,255,0.7)";
  const cardBorder = isDark
    ? "rgba(255,255,255,0.08)"
    : "rgba(0,0,0,0.08)";
  const textPrimary = isDark ? "#f0f4ff" : "#111827";
  const textMute = isDark ? "#475569" : "#94a3b8";

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 20, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, x: 60, scale: 0.92, transition: { duration: 0.25 } }}
      transition={{ type: "spring", stiffness: 300, damping: 28 }}
      className="rounded-2xl p-3 backdrop-blur-sm"
      style={{
        backgroundColor: cardBg,
        border: `1px solid ${cardBorder}`,
        boxShadow: isDark
          ? "inset 0 1px 0 rgba(255,255,255,0.06)"
          : "inset 0 1px 0 rgba(255,255,255,0.9), 0 4px 12px rgba(0,0,0,0.04)",
      }}
    >
      {/* Top row */}
      <div className="flex items-center justify-between mb-2">
        <span
          className="font-mono text-[10px] uppercase tracking-wider font-semibold"
          style={{
            color: "#00F5A0",
            textShadow: "0 0 10px rgba(0,245,160,0.4)",
          }}
        >
          {approval.agentName}
        </span>
        <span className="font-mono text-[10px]" style={{ color: textMute }}>{approval.time}</span>
      </div>

      {/* Summary */}
      <p
        className="font-sans text-[13px] leading-snug line-clamp-2 mb-3"
        style={{ color: textPrimary }}
      >
        {approval.summary}
      </p>

      {/* Actions */}
      <div className="flex items-center gap-1.5">
        <motion.button
          id={`cockpit-approve-${approval.id}`}
          whileHover={{ scale: 1.04 }}
          whileTap={{ scale: 0.97 }}
          onClick={() => onApprove(approval.id)}
          className="flex h-7 items-center gap-1.5 rounded-xl px-3 font-sans text-xs font-semibold transition-all"
          style={{
            background: "linear-gradient(135deg, #00F5A0, #00c47f)",
            color: "#060914",
            boxShadow: "0 4px 14px rgba(0,245,160,0.3)",
          }}
        >
          <Check size={11} strokeWidth={2.5} />
          Approve
        </motion.button>
        <motion.button
          id={`cockpit-edit-${approval.id}`}
          whileHover={{ scale: 1.04 }}
          className="flex h-7 items-center gap-1.5 rounded-xl border px-3 font-sans text-xs transition-all"
          style={{
            borderColor: isDark ? "rgba(255,255,255,0.12)" : "rgba(0,0,0,0.12)",
            color: isDark ? "#94a3b8" : "#475569",
          }}
        >
          <Edit2 size={11} strokeWidth={1.5} />
          Edit
        </motion.button>
        <motion.button
          id={`cockpit-skip-${approval.id}`}
          whileHover={{ scale: 1.04 }}
          onClick={() => onSkip(approval.id)}
          className="flex h-7 items-center gap-1 rounded-xl px-2 font-sans text-xs transition-all"
          style={{ color: textMute }}
        >
          <X size={11} strokeWidth={1.5} />
          Skip
        </motion.button>
      </div>
    </motion.div>
  );
}

export default function ApprovalInbox() {
  const [approvals, setApprovals] = useState<DemoApproval[]>(DEMO_APPROVALS);
  const setAgentStatus = useAgentStore((s) => s.setAgentStatus);
  const theme = useThemeStore((s) => s.theme);
  const isDark = theme === "dark";

  const handleApprove = (id: string) => {
    const approval = approvals.find((a) => a.id === id);
    if (approval) {
      setAgentStatus(approval.agentId, "output");
      setTimeout(() => setAgentStatus(approval.agentId, "idle"), 1200);
    }
    setApprovals((prev) => prev.filter((a) => a.id !== id));
    _lemmaApprove(id);
  };

  const handleSkip = (id: string) => {
    setApprovals((prev) => prev.filter((a) => a.id !== id));
    _lemmaSkip(id);
  };

  const glassPanel = isDark
    ? "bg-white/[0.04] backdrop-blur-xl border border-white/[0.08] rounded-2xl"
    : "bg-white/55 backdrop-blur-xl border border-white/60 rounded-2xl";

  const panelShadow = isDark
    ? { boxShadow: "inset 0 1px 0 rgba(255,255,255,0.06), 0 20px 40px rgba(0,0,0,0.35)" }
    : { boxShadow: "inset 0 1px 0 rgba(255,255,255,0.9), 0 8px 24px rgba(99,102,241,0.07)" };

  const textMute = isDark ? "#475569" : "#94a3b8";

  return (
    <aside
      id="cockpit-approval-inbox"
      className={`flex w-80 shrink-0 flex-col ${glassPanel}`}
      style={panelShadow}
    >
      {/* Header */}
      <div
        className="flex shrink-0 items-center justify-between px-4 py-3"
        style={{ borderBottom: `1px solid ${isDark ? "rgba(255,255,255,0.06)" : "rgba(0,0,0,0.06)"}` }}
      >
        <span className="font-mono text-[10px] uppercase tracking-wider" style={{ color: textMute }}>
          Approvals
        </span>
        {approvals.length > 0 && (
          <motion.span
            key={approvals.length}
            initial={{ scale: 0.7 }}
            animate={{ scale: 1 }}
            className="flex h-5 min-w-5 items-center justify-center rounded-full px-1.5 font-mono text-[10px] font-bold"
            style={{
              background: "linear-gradient(135deg, #00F5A0, #00c47f)",
              color: "#060914",
              boxShadow: "0 0 10px rgba(0,245,160,0.4)",
            }}
          >
            {approvals.length}
          </motion.span>
        )}
      </div>

      {/* Cards */}
      <div className="flex-1 overflow-y-auto p-3">
        {approvals.length === 0 ? (
          <div className="flex h-full items-center justify-center">
            <span className="font-mono text-[11px] text-center" style={{ color: textMute }}>
              no approvals — agents are quiet
            </span>
          </div>
        ) : (
          <div className="space-y-2">
            <AnimatePresence mode="popLayout">
              {approvals.map((approval) => (
                <ApprovalCard
                  key={approval.id}
                  approval={approval}
                  onApprove={handleApprove}
                  onSkip={handleSkip}
                  isDark={isDark}
                />
              ))}
            </AnimatePresence>
          </div>
        )}
      </div>
    </aside>
  );
}
