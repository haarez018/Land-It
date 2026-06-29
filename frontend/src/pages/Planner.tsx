import { useState, useEffect } from "react";
import { CheckSquare, Square, Plus, Trash2, Milestone, ArrowRight, Award } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { useThemeStore } from "../store/useThemeStore";

interface Goal {
  id: string;
  text: string;
  completed: boolean;
}

const DEFAULT_GOALS: Goal[] = [
  { id: "1", text: "Tailor resume for 5 target Senior Frontend roles", completed: true },
  { id: "2", text: "Complete 3 mock coaching sessions on tech system design", completed: false },
  { id: "3", text: "Draft outreach pitch for Vercel staff engineers", completed: false },
];

const TIMELINE_STEPS = [
  { title: "Stage 1: Scout & Target", description: "Collect 20 high-fit job descriptions and run ATS calibration", icon: Milestone, target: "Week 1-2" },
  { title: "Stage 2: Tailor & Pitch", description: "Optimize resume bullet points and draft voice-matched pitches", icon: ArrowRight, target: "Week 3-4" },
  { title: "Stage 3: Interview Prep", description: "Run mock coding & leadership loops in Coach panel", icon: Award, target: "Week 5-6" },
];

export default function Planner() {
  const [goals, setGoals] = useState<Goal[]>(() => {
    const saved = localStorage.getItem("land_it_planner_goals");
    return saved ? JSON.parse(saved) : DEFAULT_GOALS;
  });
  const [newGoalText, setNewGoalText] = useState("");
  const theme = useThemeStore((s) => s.theme);
  const isDark = theme === "dark";

  useEffect(() => {
    localStorage.setItem("land_it_planner_goals", JSON.stringify(goals));
  }, [goals]);

  const handleToggleGoal = (id: string) => {
    setGoals((prev) =>
      prev.map((g) => (g.id === id ? { ...g, completed: !g.completed } : g))
    );
  };

  const handleAddGoal = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newGoalText.trim()) return;
    const newGoal: Goal = {
      id: Date.now().toString(),
      text: newGoalText.trim(),
      completed: false,
    };
    setGoals((prev) => [...prev, newGoal]);
    setNewGoalText("");
  };

  const handleDeleteGoal = (id: string) => {
    setGoals((prev) => prev.filter((g) => g.id !== id));
  };

  const inputBg = isDark ? "rgba(255,255,255,0.05)" : "rgba(0,0,0,0.03)";
  const inputBorder = isDark ? "rgba(255,255,255,0.1)" : "rgba(0,0,0,0.1)";

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight" style={{ color: isDark ? "#f0f4ff" : "#111827" }}>
          Career Planner
        </h1>
        <p className="mt-2 text-sm" style={{ color: isDark ? "#94a3b8" : "#475569" }}>
          Chart your professional growth roadmap, track weekly targets, and prepare for success.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Weekly Goals Section */}
        <div
          className="rounded-2xl p-6 backdrop-blur-xl border"
          style={{
            backgroundColor: isDark ? "rgba(255,255,255,0.04)" : "rgba(255,255,255,0.6)",
            borderColor: isDark ? "rgba(255,255,255,0.08)" : "rgba(0,0,0,0.08)",
            boxShadow: "0 8px 32px rgba(0,0,0,0.05)",
          }}
        >
          <div className="flex items-center gap-2 mb-4">
            <CheckSquare size={18} style={{ color: "#00F5A0" }} />
            <h2 className="text-lg font-semibold" style={{ color: isDark ? "#f0f4ff" : "#111827" }}>
              Weekly Strategy Targets
            </h2>
          </div>

          <form onSubmit={handleAddGoal} className="flex gap-2 mb-4">
            <input
              type="text"
              value={newGoalText}
              onChange={(e) => setNewGoalText(e.target.value)}
              placeholder="Add new planner target..."
              className="flex-1 rounded-xl px-3 py-2 text-sm outline-none transition-all font-mono"
              style={{
                backgroundColor: inputBg,
                border: `1px solid ${inputBorder}`,
                color: isDark ? "#f0f4ff" : "#111827",
              }}
            />
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              type="submit"
              className="flex h-9 w-9 items-center justify-center rounded-xl"
              style={{
                background: "linear-gradient(135deg, #00F5A0, #00c47f)",
                color: "#060914",
              }}
            >
              <Plus size={16} strokeWidth={2.5} />
            </motion.button>
          </form>

          <div className="space-y-2">
            <AnimatePresence initial={false}>
              {goals.map((goal) => (
                <motion.div
                  key={goal.id}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 10 }}
                  className="flex items-center justify-between p-3 rounded-xl transition-all"
                  style={{
                    backgroundColor: isDark ? "rgba(255,255,255,0.02)" : "rgba(0,0,0,0.02)",
                    border: `1px solid ${isDark ? "rgba(255,255,255,0.04)" : "rgba(0,0,0,0.04)"}`,
                  }}
                >
                  <button
                    onClick={() => handleToggleGoal(goal.id)}
                    className="flex items-center gap-3 text-left flex-1"
                  >
                    {goal.completed ? (
                      <CheckSquare size={16} style={{ color: "#00F5A0" }} />
                    ) : (
                      <Square size={16} style={{ color: isDark ? "#8892A6" : "#64748b" }} />
                    )}
                    <span
                      className="text-xs transition-all"
                      style={{
                        color: goal.completed ? (isDark ? "#475569" : "#94a3b8") : (isDark ? "#f0f4ff" : "#111827"),
                        textDecoration: goal.completed ? "line-through" : "none",
                      }}
                    >
                      {goal.text}
                    </span>
                  </button>
                  <button
                    onClick={() => handleDeleteGoal(goal.id)}
                    className="text-xs hover:text-red-400 p-1"
                    style={{ color: isDark ? "#475569" : "#94a3b8" }}
                  >
                    <Trash2 size={13} />
                  </button>
                </motion.div>
              ))}
            </AnimatePresence>
          </div>
        </div>

        {/* Career Timeline Roadmap */}
        <div
          className="rounded-2xl p-6 backdrop-blur-xl border"
          style={{
            backgroundColor: isDark ? "rgba(255,255,255,0.04)" : "rgba(255,255,255,0.6)",
            borderColor: isDark ? "rgba(255,255,255,0.08)" : "rgba(0,0,0,0.08)",
            boxShadow: "0 8px 32px rgba(0,0,0,0.05)",
          }}
        >
          <div className="flex items-center gap-2 mb-4">
            <Milestone size={18} style={{ color: "#8A2BE2" }} />
            <h2 className="text-lg font-semibold" style={{ color: isDark ? "#f0f4ff" : "#111827" }}>
              Visual Calibration Roadmap
            </h2>
          </div>

          <div className="relative border-l pl-4 ml-2 space-y-6" style={{ borderColor: isDark ? "rgba(255,255,255,0.08)" : "rgba(0,0,0,0.08)" }}>
            {TIMELINE_STEPS.map((step, idx) => {
              const StepIcon = step.icon;
              return (
                <div key={idx} className="relative">
                  <div
                    className="absolute -left-[25px] top-0.5 flex h-4 w-4 items-center justify-center rounded-full border text-[9px] font-bold"
                    style={{
                      background: isDark ? "#111827" : "#fff",
                      borderColor: idx === 0 ? "#00F5A0" : "#8A2BE2",
                      color: idx === 0 ? "#00F5A0" : "#8A2BE2",
                    }}
                  >
                    {idx + 1}
                  </div>
                  <div>
                    <div className="flex justify-between items-center gap-4">
                      <h3 className="text-xs font-semibold flex items-center gap-1.5" style={{ color: isDark ? "#f0f4ff" : "#111827" }}>
                        <StepIcon size={12} style={{ color: idx === 0 ? "#00F5A0" : "#8A2BE2" }} />
                        {step.title}
                      </h3>
                      <span className="font-mono text-[9px] uppercase tracking-wider text-cp-accent">{step.target}</span>
                    </div>
                    <p className="mt-1 text-xs" style={{ color: isDark ? "#94a3b8" : "#475569" }}>
                      {step.description}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
