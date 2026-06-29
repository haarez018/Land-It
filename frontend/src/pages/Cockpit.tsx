import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import TopBar from "../components/cockpit/TopBar";
import AgentStrip from "../components/cockpit/AgentStrip";
import LeftRail from "../components/cockpit/LeftRail";
import CenterStage from "../components/cockpit/CenterStage";
import ApprovalInbox from "../components/cockpit/ApprovalInbox";
import CommandPalette from "../components/cockpit/CommandPalette";
import { useAgentStore } from "../store/useAgentStore";
import { useDemoAgentCycle } from "../hooks/useDemoAgentCycle";
import { useThemeStore } from "../store/useThemeStore";

type PipelineStatus = "Discovered" | "Tailored" | "Applied" | "Interviewing" | "Closed";

const INTRO_DONE_KEY = "cockpit_intro_done";

export default function Cockpit() {
  const navigate = useNavigate();
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [pipelineFilter, setPipelineFilter] = useState<PipelineStatus | null>(null);
  const [selectedAppId, setSelectedAppId] = useState<string | null>(null);
  const [introPlayed, setIntroPlayed] = useState(() =>
    sessionStorage.getItem(INTRO_DONE_KEY) === "true"
  );

  const setActiveAgent = useAgentStore((s) => s.setActiveAgent);
  const theme = useThemeStore((s) => s.theme);

  useDemoAgentCycle();

  // Apply theme class to html root
  useEffect(() => {
    const root = document.documentElement;
    root.classList.remove("dark", "light");
    root.classList.add(theme);
  }, [theme]);

  useEffect(() => {
    if (!introPlayed) {
      sessionStorage.setItem(INTRO_DONE_KEY, "true");
      setIntroPlayed(true);
    }
  }, [introPlayed]);

  // Global Cmd/Ctrl+K listener
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setPaletteOpen((o) => !o);
      }
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, []);

  const handleAgentClick = useCallback(
    (agentId: string) => { setActiveAgent(agentId); },
    [setActiveAgent]
  );

  const handleQuickAction = useCallback(
    (action: string) => {
      const routes: Record<string, string> = {
        discover: "/jobs", tailor: "/tailor", coach: "/coach", pitcher: "/pitcher",
      };
      if (routes[action]) navigate(routes[action]);
    },
    [navigate]
  );

  const handleCommand = useCallback(
    (action: string, arg?: string) => {
      if (action === "navigate" && arg) navigate(arg);
      else if (action === "tailor") navigate("/tailor");
      else if (action === "discover") navigate("/jobs");
      else if (action === "pitch") navigate("/pitcher");
      else if (action === "interview") navigate("/coach");
    },
    [navigate]
  );

  const showIntro = !introPlayed;
  const isDark = theme === "dark";

  return (
    <div
      id="cockpit-root"
      className={`flex h-screen flex-col overflow-hidden ${isDark ? "cockpit-bg-dark" : "cockpit-bg-light"}`}
      style={{ fontFamily: "'Inter Tight', 'Inter', system-ui, sans-serif" }}
    >
      {/* Top bar */}
      <motion.div
        initial={showIntro ? { opacity: 0, y: -8 } : false}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, ease: "easeOut" }}
      >
        <TopBar onCommandPaletteOpen={() => setPaletteOpen(true)} />
      </motion.div>

      {/* Agent strip */}
      <AgentStrip onAgentClick={handleAgentClick} />

      {/* Main 3-column layout — panels float with gap */}
      <motion.div
        className="flex flex-1 overflow-hidden gap-3 px-3 pb-3 pt-0"
        initial={showIntro ? { opacity: 0, y: 12 } : false}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35, delay: 0.45, ease: "easeOut" }}
      >
        <LeftRail
          activeFilter={pipelineFilter}
          onFilterChange={setPipelineFilter}
          onQuickAction={handleQuickAction}
        />
        <CenterStage
          filter={pipelineFilter}
          selectedAppId={selectedAppId}
          onSelectApp={setSelectedAppId}
        />
        <ApprovalInbox />
      </motion.div>

      {/* Command palette */}
      <CommandPalette
        open={paletteOpen}
        onClose={() => setPaletteOpen(false)}
        onCommand={handleCommand}
      />
    </div>
  );
}
