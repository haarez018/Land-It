import { useState, useEffect, useRef } from "react";
import { ChevronRight, ArrowLeft, Zap, Briefcase } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { DEMO_APPLICATIONS } from "../../lib/demoData";
import type { DemoApplication } from "../../lib/demoData";
import CallbackGauge from "./CallbackGauge";
import { useThemeStore } from "../../store/useThemeStore";

type PipelineStatus = "Discovered" | "Tailored" | "Applied" | "Interviewing" | "Closed";

const STATUS_COLORS: Record<PipelineStatus, string> = {
  Discovered: "#8892A6",
  Tailored: "#8892A6",
  Applied: "#FFB020",
  Interviewing: "#00F5A0",
  Closed: "#475569",
};

const MOCK_STREAM_WORDS = `Designed and shipped a distributed payment infrastructure handling 2M transactions per day with 99.99% uptime across 15 global regions. Led the TypeScript migration of 3 critical services with zero downtime deployment. Reduced p99 API latency by 40% through query optimization connection pooling and intelligent caching layers. Collaborated cross-functionally with product and design to deliver user-facing features used by 500K active merchants.`.split(" ");

function HeatmapTooltip({ name, score, isDark }: { name: string; score: number; isDark: boolean }) {
  return (
    <div
      className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 z-50 whitespace-nowrap rounded-xl px-2 py-1.5 pointer-events-none backdrop-blur-xl"
      style={{
        background: isDark ? "rgba(13,17,23,0.95)" : "rgba(255,255,255,0.95)",
        border: `1px solid ${isDark ? "rgba(255,255,255,0.1)" : "rgba(0,0,0,0.08)"}`,
        boxShadow: "0 8px 24px rgba(0,0,0,0.3)",
      }}
    >
      <p className="font-mono text-[10px]" style={{ color: isDark ? "#f0f4ff" : "#111827" }}>{name}</p>
      <p className="font-mono text-[10px] text-center" style={{ color: "#00F5A0" }}>{score}</p>
    </div>
  );
}

function Heatmap({ heatmap, isDark }: { heatmap: DemoApplication["heatmap"]; isDark: boolean }) {
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null);
  const ats = heatmap.filter((d) => d.type === "ats");
  const standout = heatmap.filter((d) => d.type === "standout");
  const textMute = isDark ? "#475569" : "#94a3b8";

  return (
    <div id="cockpit-heatmap" className="space-y-2">
      {[{ label: "ATS", items: ats, offset: 0 }, { label: "STD", items: standout, offset: ats.length }].map(({ label, items, offset }) => (
        <div key={label} className="flex items-center gap-2">
          <span className="font-mono text-[9px] uppercase tracking-wider w-6" style={{ color: textMute }}>{label}</span>
          <div className="flex gap-1">
            {items.map((d, i) => {
              const gi = offset + i;
              const isHigh = d.score >= 80;
              return (
                <div
                  key={d.name}
                  className="relative"
                  onMouseEnter={() => setHoveredIdx(gi)}
                  onMouseLeave={() => setHoveredIdx(null)}
                >
                  <div
                    className="h-2 w-2 rounded-sm cursor-default transition-transform hover:scale-125"
                    style={{
                      backgroundColor: "#00F5A0",
                      opacity: d.score / 100,
                      filter: isHigh ? "drop-shadow(0 0 4px rgba(0,245,160,0.7))" : undefined,
                    }}
                  />
                  {hoveredIdx === gi && (
                    <HeatmapTooltip name={d.name} score={d.score} isDark={isDark} />
                  )}
                </div>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}



function LiveDiff({ app, isDark }: { app: DemoApplication; isDark: boolean }) {
  const [words, setWords] = useState<string[]>([]);
  const [streaming, setStreaming] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const idxRef = useRef(0);

  const startStream = () => {
    setWords([]);
    idxRef.current = 0;
    setStreaming(true);
  };

  useEffect(() => {
    if (!streaming) return;
    const tick = () => {
      if (idxRef.current >= MOCK_STREAM_WORDS.length) { setStreaming(false); return; }
      setWords((prev) => [...prev, MOCK_STREAM_WORDS[idxRef.current]]);
      idxRef.current++;
      timerRef.current = setTimeout(tick, 40);
    };
    timerRef.current = setTimeout(tick, 40);
    return () => { if (timerRef.current) clearTimeout(timerRef.current); };
  }, [streaming]);

  const surfaceBg = isDark ? "rgba(255,255,255,0.03)" : "rgba(0,0,0,0.03)";
  const surfaceBorder = isDark ? "rgba(255,255,255,0.07)" : "rgba(0,0,0,0.07)";

  return (
    <div id="cockpit-live-diff" className="flex-1 flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <span className="font-mono text-[10px] uppercase tracking-wider" style={{ color: isDark ? "#475569" : "#94a3b8" }}>
          Live Diff
        </span>
        <motion.button
          id="cockpit-diff-stream-btn"
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.97 }}
          onClick={startStream}
          disabled={streaming}
          className="flex items-center gap-1.5 rounded-xl px-3 py-1 font-mono text-[10px] transition-all disabled:opacity-50"
          style={{
            background: streaming ? "rgba(0,245,160,0.1)" : "linear-gradient(135deg, rgba(0,245,160,0.15), rgba(138,43,226,0.1))",
            border: "1px solid rgba(0,245,160,0.3)",
            color: "#00F5A0",
          }}
        >
          <Zap size={10} strokeWidth={1.5} />
          {streaming ? "Streaming..." : "Stream Tailor"}
        </motion.button>
      </div>

      <div
        className="flex-1 overflow-y-auto rounded-2xl p-3 font-mono text-xs leading-relaxed backdrop-blur-sm"
        style={{
          minHeight: "120px",
          backgroundColor: surfaceBg,
          border: `1px solid ${surfaceBorder}`,
        }}
      >
        {words.length === 0 ? (
          <span style={{ color: isDark ? "#475569" : "#94a3b8" }}>
            Press "Stream Tailor" to see live resume rewriting...
          </span>
        ) : (
          <>
            {words.map((w, i) => (
              <motion.span
                key={i}
                initial={{ opacity: 0 }}
                animate={{ opacity: i === words.length - 1 ? 0.7 : 1 }}
                transition={{ duration: 0.08 }}
                style={{ color: "#00F5A0" }}
              >
                {w}{" "}
              </motion.span>
            ))}
            {streaming && (
              <span
                className="inline-block h-3 w-0.5 align-middle animate-dot-pulse"
                style={{ backgroundColor: "#00F5A0" }}
              />
            )}
          </>
        )}
      </div>

      <div className="font-mono text-[10px]" style={{ color: isDark ? "#475569" : "#94a3b8" }}>
        Source resume excerpt
      </div>
      <div
        className="rounded-2xl p-3 font-mono text-xs leading-relaxed"
        style={{
          backgroundColor: surfaceBg,
          border: `1px solid ${surfaceBorder}`,
          color: isDark ? "#475569" : "#94a3b8",
        }}
      >
        {app.resumeSample.split("\n").slice(0, 8).join("\n")}
      </div>
    </div>
  );
}

function ApplicationDetail({ app, onBack, isDark }: { app: DemoApplication; onBack: () => void; isDark: boolean }) {
  const [diffMode, setDiffMode] = useState(false);
  const textPrimary = isDark ? "#f0f4ff" : "#111827";
  const textDim = isDark ? "#94a3b8" : "#475569";
  const divider = isDark ? "rgba(255,255,255,0.06)" : "rgba(0,0,0,0.06)";

  return (
    <div id="cockpit-app-detail" className="flex h-full flex-col overflow-hidden">
      {/* Detail header */}
      <div className="flex shrink-0 items-center gap-3 px-4 py-2.5" style={{ borderBottom: `1px solid ${divider}` }}>
        <motion.button
          id="cockpit-detail-back"
          whileHover={{ x: -2 }}
          onClick={onBack}
          className="flex items-center gap-1 font-mono text-[10px] transition-colors hover:text-cp-accent"
          style={{ color: isDark ? "#475569" : "#94a3b8" }}
        >
          <ArrowLeft size={12} strokeWidth={1.5} />
          Back
        </motion.button>
        <div className="h-3 w-px" style={{ backgroundColor: divider }} />
        <div className="flex-1 min-w-0">
          <span className="font-sans text-sm font-semibold" style={{ color: textPrimary }}>{app.company}</span>
          <span className="font-sans text-sm mx-2" style={{ color: textDim }}>—</span>
          <span className="font-sans text-sm" style={{ color: textDim }}>{app.role}</span>
        </div>
        <motion.button
          id="cockpit-diff-toggle"
          whileHover={{ scale: 1.04 }}
          onClick={() => setDiffMode((d) => !d)}
          className="flex items-center gap-1.5 rounded-xl px-3 py-1 font-mono text-[10px] transition-all"
          style={{
            background: diffMode ? "linear-gradient(135deg, rgba(0,245,160,0.15), rgba(138,43,226,0.1))" : "transparent",
            border: `1px solid ${diffMode ? "rgba(0,245,160,0.5)" : isDark ? "rgba(255,255,255,0.1)" : "rgba(0,0,0,0.1)"}`,
            color: diffMode ? "#00F5A0" : isDark ? "#475569" : "#94a3b8",
            boxShadow: diffMode ? "0 0 12px rgba(0,245,160,0.15)" : undefined,
          }}
        >
          <Zap size={10} strokeWidth={1.5} />
          Live Diff
        </motion.button>
      </div>

      {/* Heatmap */}
      <div className="shrink-0 px-4 py-3" style={{ borderBottom: `1px solid ${divider}` }}>
        <div className="flex items-center justify-between mb-2">
          <span className="font-mono text-[10px] uppercase tracking-wider" style={{ color: isDark ? "#475569" : "#94a3b8" }}>
            22-Dimension Heatmap
          </span>
          <span className="font-mono text-[10px]" style={{ color: textDim }}>
            Fit: <span style={{ color: "#00F5A0", textShadow: "0 0 8px rgba(0,245,160,0.5)" }}>{app.fitScore}%</span>
          </span>
        </div>
        <Heatmap heatmap={app.heatmap} isDark={isDark} />
      </div>

      {/* Body */}
      <div className="flex flex-1 overflow-hidden">
        <div className="w-1/2 overflow-y-auto p-4" style={{ borderRight: `1px solid ${divider}` }}>
          <p className="font-mono text-[10px] uppercase tracking-wider mb-3" style={{ color: isDark ? "#475569" : "#94a3b8" }}>
            Job Description
          </p>
          <div className="font-sans text-xs leading-relaxed whitespace-pre-wrap" style={{ color: textDim }}>{app.jd}</div>
        </div>
        <div className="w-1/2 overflow-y-auto p-4 flex flex-col gap-4">
          {diffMode ? (
            <LiveDiff app={app} isDark={isDark} />
          ) : (
            <>
              <div className="flex justify-center pt-4">
                <CallbackGauge value={app.callbackPct} confidenceLow={Math.max(0, app.callbackPct - 8)} confidenceHigh={Math.min(100, app.callbackPct + 8)} />
              </div>
              <div>
                <p className="font-mono text-[10px] uppercase tracking-wider mb-2" style={{ color: isDark ? "#475569" : "#94a3b8" }}>
                  Resume Excerpt
                </p>
                <pre className="font-mono text-[11px] whitespace-pre-wrap" style={{ color: textDim }}>{app.resumeSample}</pre>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

const COLUMNS = ["Company", "Role", "Status", "Fit %", "Callback %", "Last activity"];

interface CenterStageProps {
  filter: PipelineStatus | null;
  selectedAppId: string | null;
  onSelectApp: (id: string | null) => void;
}

export default function CenterStage({ filter, selectedAppId, onSelectApp }: CenterStageProps) {
  const theme = useThemeStore((s) => s.theme);
  const isDark = theme === "dark";

  const filtered = filter
    ? DEMO_APPLICATIONS.filter((a) => a.status === filter)
    : DEMO_APPLICATIONS;

  const selectedApp = selectedAppId
    ? DEMO_APPLICATIONS.find((a) => a.id === selectedAppId) ?? null
    : null;

  const glassPanel = isDark
    ? "bg-white/[0.04] backdrop-blur-xl border border-white/[0.08] rounded-2xl"
    : "bg-white/55 backdrop-blur-xl border border-white/60 rounded-2xl";

  const panelShadow = isDark
    ? { boxShadow: "inset 0 1px 0 rgba(255,255,255,0.06), 0 20px 40px rgba(0,0,0,0.35)" }
    : { boxShadow: "inset 0 1px 0 rgba(255,255,255,0.9), 0 8px 24px rgba(99,102,241,0.07)" };

  const textMute = isDark ? "#475569" : "#94a3b8";
  const divider = isDark ? "rgba(255,255,255,0.06)" : "rgba(0,0,0,0.06)";
  const headerBg = isDark ? "rgba(255,255,255,0.02)" : "rgba(0,0,0,0.02)";
  const rowHover = isDark ? "rgba(255,255,255,0.04)" : "rgba(0,0,0,0.03)";

  if (selectedApp) {
    return (
      <main id="cockpit-center-stage" className={`flex-1 overflow-hidden ${glassPanel}`} style={panelShadow}>
        <ApplicationDetail app={selectedApp} onBack={() => onSelectApp(null)} isDark={isDark} />
      </main>
    );
  }

  return (
    <main id="cockpit-center-stage" className={`flex-1 overflow-hidden flex flex-col ${glassPanel}`} style={panelShadow}>
      {/* Table header */}
      <div
        className="flex shrink-0 px-4 rounded-t-2xl"
        style={{ backgroundColor: headerBg, borderBottom: `1px solid ${divider}` }}
      >
        {COLUMNS.map((col) => (
          <div
            key={col}
            className={`py-2.5 font-mono text-[9px] uppercase tracking-widest ${
              col === "Company" ? "w-40" :
              col === "Role" ? "flex-1" :
              col === "Status" ? "w-28" :
              col === "Fit %" ? "w-20 text-right" :
              col === "Callback %" ? "w-24 text-right" :
              "w-28 text-right"
            }`}
            style={{ color: textMute }}
          >
            {col}
          </div>
        ))}
        <div className="w-6" />
      </div>

      {/* Rows */}
      <div className="flex-1 overflow-y-auto">
        {filtered.length === 0 ? (
          <div className="flex items-center justify-center py-16">
            <span className="font-mono text-[11px]" style={{ color: textMute }}>
              no applications in this stage
            </span>
          </div>
        ) : (
          <AnimatePresence mode="sync">
            {filtered.map((app, i) => (
              <motion.button
                key={app.id}
                id={`cockpit-app-row-${app.id}`}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.04, duration: 0.2 }}
                onClick={() => onSelectApp(app.id)}
                className="row-hover flex w-full items-center px-4 text-left transition-all"
                style={{ borderBottom: `1px solid ${divider}` }}
                onMouseEnter={(e) => { e.currentTarget.style.backgroundColor = rowHover; }}
                onMouseLeave={(e) => { e.currentTarget.style.backgroundColor = ""; }}
              >
                {/* Company */}
                <div className="flex w-40 items-center gap-2.5 py-3">
                  <div
                    className="flex h-7 w-7 shrink-0 items-center justify-center rounded-xl"
                    style={{
                      backgroundColor: isDark ? "rgba(255,255,255,0.06)" : "rgba(0,0,0,0.04)",
                      border: `1px solid ${isDark ? "rgba(255,255,255,0.1)" : "rgba(0,0,0,0.08)"}`,
                    }}
                  >
                    <Briefcase size={12} style={{ color: "#00F5A0" }} />
                  </div>
                  <span className="font-sans text-[13px] font-medium truncate" style={{ color: isDark ? "#f0f4ff" : "#111827" }}>
                    {app.company}
                  </span>
                </div>

                {/* Role */}
                <div className="flex-1 py-3 pr-4">
                  <span className="font-sans text-[13px] truncate" style={{ color: isDark ? "#94a3b8" : "#475569" }}>
                    {app.role}
                  </span>
                </div>

                {/* Status */}
                <div className="w-28 py-3">
                  <span className="font-mono text-[11px]" style={{ color: STATUS_COLORS[app.status] }}>
                    {app.status}
                  </span>
                </div>

                {/* Fit % */}
                <div className="w-20 py-3 text-right">
                  <span
                    className="font-mono text-[13px] font-semibold"
                    style={{
                      color: app.fitScore >= 80 ? "#00F5A0" : isDark ? "#f0f4ff" : "#111827",
                      textShadow: app.fitScore >= 80 ? "0 0 10px rgba(0,245,160,0.4)" : undefined,
                    }}
                  >
                    {app.fitScore}%
                  </span>
                </div>

                {/* Callback % */}
                <div className="w-24 py-3 text-right">
                  <span className="font-mono text-[13px]" style={{ color: isDark ? "#94a3b8" : "#475569" }}>
                    {app.callbackPct}%
                  </span>
                </div>

                {/* Last activity */}
                <div className="w-28 py-3 text-right">
                  <span className="font-mono text-[10px]" style={{ color: textMute }}>{app.lastActivity}</span>
                </div>

                {/* Arrow */}
                <div className="w-6 flex justify-end py-3">
                  <ChevronRight size={14} strokeWidth={1.5} style={{ color: textMute }} />
                </div>
              </motion.button>
            ))}
          </AnimatePresence>
        )}
      </div>
    </main>
  );
}
