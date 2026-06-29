import { create } from "zustand";

export type AgentStatus = "idle" | "thinking" | "working" | "output";

export interface Agent {
  id: string;
  name: string;
  status: AgentStatus;
  progress: number;
  lastOutput: string;
  lastUpdated: Date;
}

interface AgentState {
  agents: Agent[];
  activeAgentId: string | null;
  setAgentStatus: (id: string, status: AgentStatus, progress?: number) => void;
  setActiveAgent: (id: string | null) => void;
}

const INITIAL_AGENTS: Agent[] = [
  {
    id: "scout",
    name: "Scout",
    status: "idle",
    progress: 0,
    lastOutput: "Found 12 new roles matching your profile on LinkedIn and Greenhouse.",
    lastUpdated: new Date(),
  },
  {
    id: "tailor",
    name: "Tailor",
    status: "idle",
    progress: 0,
    lastOutput: "Resume tailored for Stripe — ATS score improved from 61 to 84.",
    lastUpdated: new Date(),
  },
  {
    id: "pitcher",
    name: "Pitcher",
    status: "idle",
    progress: 0,
    lastOutput: "Cover letter drafted for Vercel Senior Engineer role. Voice match: 91%.",
    lastUpdated: new Date(),
  },
  {
    id: "coach",
    name: "Coach",
    status: "idle",
    progress: 0,
    lastOutput: "Mock interview complete. Strongest: system design. Weakest: behavioral.",
    lastUpdated: new Date(),
  },
  {
    id: "tracker",
    name: "Tracker",
    status: "idle",
    progress: 0,
    lastOutput: "Pipeline updated — 3 applications moved to interviewing stage.",
    lastUpdated: new Date(),
  },
  {
    id: "planner",
    name: "Planner",
    status: "idle",
    progress: 0,
    lastOutput: "Weekly strategy: focus on Series B companies in SF, target 8 applications.",
    lastUpdated: new Date(),
  },
];

export const useAgentStore = create<AgentState>((set) => ({
  agents: INITIAL_AGENTS,
  activeAgentId: null,

  setAgentStatus: (id, status, progress = 0) =>
    set((state) => ({
      agents: state.agents.map((a) =>
        a.id === id ? { ...a, status, progress, lastUpdated: new Date() } : a
      ),
    })),

  setActiveAgent: (id) => set({ activeAgentId: id }),
}));
