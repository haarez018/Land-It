/** Application card for the Kanban board. */

import type { Application } from "../../lib/types";

interface Props {
  application: Application;
  onSelect?: (id: string) => void;
}

const STATUS_ACCENT: Record<string, string> = {
  discovered: "border-l-navy-500",
  queued: "border-l-blue-500",
  tailoring: "border-l-amber-500",
  ready: "border-l-emerald-500",
  submitted: "border-l-purple-500",
  followed_up: "border-l-cyan-500",
  phone_screen: "border-l-pink-500",
  interviewing: "border-l-orange-500",
  offer: "border-l-emerald-400",
  rejected: "border-l-red-500",
  withdrawn: "border-l-navy-600",
};

export default function Card({ application, onSelect }: Props) {
  const { job, fit_score, ats_score_after, status } = application;

  return (
    <div
      onClick={() => onSelect?.(application.id)}
      className={`cursor-pointer rounded-xl border border-white/10 border-l-4 bg-white/5 p-3 backdrop-blur-md transition-all hover:border-[#00F5A0] hover:shadow-lg ${
        STATUS_ACCENT[status] || "border-l-[#475569]"
      }`}
    >
      {/* Company + Title */}
      <p className="text-xs font-medium text-[#00F5A0]">
        {job.company || "Unknown Company"}
      </p>
      <p className="mt-0.5 text-sm font-semibold text-theme line-clamp-1">
        {job.title || "Untitled Role"}
      </p>

      {/* Location */}
      {job.location && (
        <p className="mt-1 text-[10px] text-muted-theme">{job.location}</p>
      )}

      {/* Score badges */}
      <div className="mt-2 flex items-center gap-2">
        {fit_score > 0 && (
          <span
            className={`rounded px-1.5 py-0.5 text-[10px] font-bold ${
              fit_score >= 80
                ? "bg-emerald-500/15 text-emerald-400"
                : fit_score >= 60
                  ? "bg-amber-500/15 text-amber-400"
                  : "bg-red-500/15 text-red-400"
            }`}
          >
            Fit {fit_score}
          </span>
        )}
        {ats_score_after != null && ats_score_after > 0 && (
          <span className="rounded bg-blue-500/15 px-1.5 py-0.5 text-[10px] font-bold text-blue-400">
            ATS {ats_score_after}
          </span>
        )}
      </div>

      {/* Priority indicator */}
      {application.planner_priority > 0 && application.planner_priority <= 3 && (
        <div className="mt-2 flex items-center gap-1">
          {Array.from({ length: application.planner_priority }).map((_, i) => (
            <div
              key={i}
              className="h-1.5 w-1.5 rounded-full bg-[#00F5A0]"
            />
          ))}
          <span className="ml-1 text-[9px] text-muted-theme">priority</span>
        </div>
      )}
    </div>
  );
}
