import { useState, useEffect, useCallback } from "react";
import { useNavigate, useSearchParams, useLocation } from "react-router-dom";
import { motion } from "framer-motion";
import TopBar from "./TopBar";
import AgentStrip from "./AgentStrip";
import LeftRail from "./LeftRail";
import ApprovalInbox from "./ApprovalInbox";
import CommandPalette from "./CommandPalette";
import { useAgentStore } from "../../store/useAgentStore";
import { useDemoAgentCycle } from "../../hooks/useDemoAgentCycle";
import { useThemeStore } from "../../store/useThemeStore";

interface LayoutProps {
  children: React.ReactNode;
}

type PipelineStatus = "Discovered" | "Tailored" | "Applied" | "Interviewing" | "Closed";

const INTRO_DONE_KEY = "cockpit_intro_done";

export default function Layout({ children }: LayoutProps) {
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [introPlayed, setIntroPlayed] = useState(() =>
    sessionStorage.getItem(INTRO_DONE_KEY) === "true"
  );

  const setActiveAgent = useAgentStore((s) => s.setActiveAgent);
  const theme = useThemeStore((s) => s.theme);

  // Run the background agent demo status cycling
  useDemoAgentCycle();

  // Apply theme class to HTML root
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
    (agentId: string) => {
      setActiveAgent(agentId);
      const routes: Record<string, string> = {
        scout: "/jobs",
        tailor: "/tailor",
        pitcher: "/pitcher",
        coach: "/coach",
        tracker: "/tracker",
        planner: "/planner",
      };
      if (routes[agentId]) {
        navigate(routes[agentId]);
      }
    },
    [setActiveAgent, navigate]
  );

  const handleQuickAction = useCallback(
    (action: string) => {
      const routes: Record<string, string> = {
        discover: "/jobs",
        tailor: "/tailor",
        coach: "/coach",
        pitcher: "/pitcher",
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

  const handleFilterChange = useCallback(
    (status: PipelineStatus | null) => {
      if (status) {
        navigate(`/pipeline?filter=${status}`);
      } else {
        navigate("/pipeline");
      }
    },
    [navigate]
  );

  const activeFilter = (location.pathname === "/pipeline" || location.pathname === "/")
    ? (searchParams.get("filter") as PipelineStatus | null)
    : null;

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

      {/* Main 3-column layout — center container is the page router child */}
      <motion.div
        className="flex flex-1 overflow-hidden gap-3 px-3 pb-3 pt-0"
        initial={showIntro ? { opacity: 0, y: 12 } : false}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35, delay: 0.45, ease: "easeOut" }}
      >
        <LeftRail
          activeFilter={activeFilter}
          onFilterChange={handleFilterChange}
          onQuickAction={handleQuickAction}
        />
        
        {/* Replaced fixed CenterStage component with glassy wrapper for children routes */}
        <main
          className="flex-1 overflow-y-auto glass-panel p-4"
          style={{
            scrollbarWidth: "thin",
            backgroundColor: isDark ? "rgba(255,255,255,0.04)" : "rgba(255,255,255,0.55)",
            borderColor: isDark ? "rgba(255,255,255,0.08)" : "rgba(0,0,0,0.08)",
            boxShadow: isDark
              ? "inset 0 1px 0 rgba(255,255,255,0.06), 0 20px 40px rgba(0,0,0,0.35)"
              : "inset 0 1px 0 rgba(255,255,255,0.9), 0 8px 24px rgba(99,102,241,0.07)"
          }}
        >
          {children}
        </main>

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
