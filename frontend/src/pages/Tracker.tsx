/** Kanban board tracker — backed by useTrackerStore. */

import { useCallback, useEffect } from "react";
import { useTrackerStore } from "../store";
import { useThemeStore } from "../store/useThemeStore";
import type { ApplicationStatus } from "../lib/types";
import Board from "../components/kanban/Board";

export default function Tracker() {
  const theme = useThemeStore((s) => s.theme);
  const isDark = theme === "dark";
  const apps = useTrackerStore((s) => s.apps);
  const loading = useTrackerStore((s) => s.loading);
  const error = useTrackerStore((s) => s.error);
  const fetchApps = useTrackerStore((s) => s.fetchApps);
  const updateStatus = useTrackerStore((s) => s.updateStatus);

  useEffect(() => {
    fetchApps();
  }, [fetchApps]);

  const handleStatusChange = useCallback(
    async (appId: string, newStatus: ApplicationStatus) => {
      await updateStatus(appId, newStatus);
    },
    [updateStatus],
  );

  const handleSelectApp = useCallback((appId: string) => {
    // TODO: Open application detail drawer
    console.log("Selected application:", appId);
  }, []);

  /* Map TrackedApp → Application shape the Board expects */
  const boardApps = apps.map((a) => ({
    id: a.id,
    user_id: "",
    job_id: a.job_id,
    job: {
      id: a.job_id,
      raw_text: "",
      title: "",
      company: "",
      location: "",
      remote_policy: "",
      seniority_level: "",
      employment_type: "",
      required_skills: [],
      preferred_skills: [],
      tech_stack: [],
      requirements: [],
    },
    status: a.status,
    fit_score: a.fit_score,
    ats_score_before: a.ats_score_before ?? undefined,
    ats_score_after: a.ats_score_after ?? undefined,
    planner_priority: a.priority,
  }));

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-theme">
            Here&apos;s where everything stands.
          </h1>
          <p className="mt-2 text-muted-theme">
            Drag applications across stages. Follow-ups are auto-scheduled.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <span className="rounded-full bg-white/5 border border-white/10 px-3 py-1 text-xs text-muted-theme">
            {apps.length} total
          </span>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
          {error}
        </div>
      )}

      {/* Loading */}
      {loading ? (
        <div className="flex items-center justify-center py-16">
          <svg
            className="h-6 w-6 animate-spin text-amber-400"
            viewBox="0 0 24 24"
            fill="none"
          >
            <circle
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="3"
              className="opacity-25"
            />
            <path
              d="M4 12a8 8 0 018-8"
              stroke="currentColor"
              strokeWidth="3"
              strokeLinecap="round"
            />
          </svg>
        </div>
      ) : apps.length > 0 ? (
        <Board
          applications={boardApps}
          onStatusChange={handleStatusChange}
          onSelectApp={handleSelectApp}
        />
      ) : (
        /* Empty state with static columns */
        <div className="flex gap-4 overflow-x-auto pb-4">
          {[
            "Queued",
            "Tailoring",
            "Ready",
            "Submitted",
            "Interviewing",
            "Offer",
          ].map((label) => (
            <div
              key={label}
              className="min-w-[260px] flex-shrink-0 rounded-2xl glass-card backdrop-blur-xl border border-white/10"
            >
              <div className="border-b border-white/10 px-4 py-3">
                <h3 className="text-sm font-semibold text-theme-secondary">
                  {label}
                </h3>
              </div>
              <div className="p-3">
                <div className="rounded-xl border border-dashed border-white/10 p-4 text-center text-xs text-muted-theme bg-white/[0.01]">
                  No applications
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Help text */}
      <div
        className="glass-card p-4 border border-white/10 text-center rounded-2xl shadow-md backdrop-blur-xl"
        style={{
          backgroundColor: isDark ? "rgba(255,255,255,0.02)" : "rgba(255,255,255,0.55)"
        }}
      >
        <p className="text-sm text-muted-theme">
          Applications flow through the pipeline automatically as you tailor
          resumes and submit them. Use the{" "}
          <span className="font-semibold text-cp-accent">Tailor</span> page to
          score and optimize, then mark as submitted here.
        </p>
      </div>
    </div>
  );
}
