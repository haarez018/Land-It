import { useEffect, useRef } from "react";
import { useAgentStore } from "../store/useAgentStore";
import type { AgentStatus } from "../store/useAgentStore";

const CYCLE_SEQUENCE: Array<{ id: string; statuses: AgentStatus[] }> = [
  { id: "scout", statuses: ["thinking", "working", "output", "idle"] },
  { id: "tailor", statuses: ["working", "output", "idle"] },
  { id: "pitcher", statuses: ["thinking", "output", "idle"] },
  { id: "coach", statuses: ["idle", "thinking", "working"] },
  { id: "tracker", statuses: ["output", "idle", "thinking"] },
  { id: "planner", statuses: ["idle", "working", "output"] },
];

const STATUS_DURATIONS: Record<AgentStatus, number> = {
  idle: 2000,
  thinking: 1800,
  working: 3000,
  output: 1200,
};

export function useDemoAgentCycle() {
  const setAgentStatus = useAgentStore((s) => s.setAgentStatus);
  const frameRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const phaseRef = useRef(0);

  useEffect(() => {
    let agentIndex = 0;
    let statusIndex = 0;

    const tick = () => {
      const agent = CYCLE_SEQUENCE[agentIndex];
      const status = agent.statuses[statusIndex];
      const progress = status === "working" ? Math.random() * 60 + 20 : 0;

      setAgentStatus(agent.id, status, progress);

      statusIndex++;
      if (statusIndex >= agent.statuses.length) {
        statusIndex = 0;
        agentIndex = (agentIndex + 1) % CYCLE_SEQUENCE.length;
      }

      phaseRef.current++;
      frameRef.current = setTimeout(tick, STATUS_DURATIONS[status]);
    };

    frameRef.current = setTimeout(tick, 1200);

    return () => {
      if (frameRef.current) clearTimeout(frameRef.current);
    };
  }, [setAgentStatus]);
}
