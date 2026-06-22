/** Per-dimension score breakdown with issues, suggestions, and priority badges. */

import type { DimensionScore } from "../../lib/types";

interface Props {
  dimensions: DimensionScore[];
}

const priorityColors: Record<string, string> = {
  critical: "bg-red-500/20 text-red-400 border-red-500/30",
  high: "bg-orange-500/20 text-orange-400 border-orange-500/30",
  medium: "bg-amber-500/20 text-amber-400 border-amber-500/30",
  low: "bg-[var(--bg-tertiary)] text-[var(--text-muted)] border-[var(--border-primary)]",
};

function ScoreBar({ score }: { score: number }) {
  const color =
    score >= 80
      ? "bg-emerald-500"
      : score >= 60
        ? "bg-amber-500"
        : score >= 40
          ? "bg-orange-500"
          : "bg-red-500";

  return (
    <div className="h-2 w-full rounded-full bg-[var(--bg-tertiary)]">
      <div
        className={`h-full rounded-full ${color} transition-all duration-700`}
        style={{ width: `${Math.min(score, 100)}%` }}
      />
    </div>
  );
}

export default function DimensionBreakdown({ dimensions }: Props) {
  if (!dimensions.length) return null;

  return (
    <div className="space-y-3">
      <h3 className="text-lg font-semibold text-theme">Score Breakdown</h3>
      {dimensions.map((dim) => (
        <details
          key={dim.dimension_id}
          className="group rounded-lg border border-[var(--border-primary)] bg-[var(--bg-card)]"
        >
          <summary className="flex cursor-pointer items-center gap-3 p-4">
            {/* Priority badge */}
            <span
              className={`rounded-full border px-2 py-0.5 text-[10px] font-bold uppercase ${priorityColors[dim.priority] || priorityColors.low}`}
            >
              {dim.priority}
            </span>
            {/* Name + score */}
            <div className="flex-1">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-theme">
                  {dim.dimension_name}
                </span>
                <span className="text-sm font-bold text-amber-500">
                  {dim.raw_score.toFixed(0)}
                </span>
              </div>
              <ScoreBar score={dim.raw_score} />
            </div>
            {/* Weight */}
            <span className="text-xs text-muted-theme">
              {(dim.weight * 100).toFixed(0)}%
            </span>
          </summary>

          <div className="border-t border-[var(--border-primary)] px-4 py-3 text-sm">
            <p className="text-theme-secondary">{dim.explanation}</p>

            {dim.issues.length > 0 && (
              <div className="mt-2">
                <p className="text-xs font-semibold uppercase text-red-400">Issues</p>
                <ul className="mt-1 list-inside list-disc text-theme-secondary">
                  {dim.issues.map((issue, i) => (
                    <li key={i}>{issue}</li>
                  ))}
                </ul>
              </div>
            )}

            {dim.suggestions.length > 0 && (
              <div className="mt-2">
                <p className="text-xs font-semibold uppercase text-emerald-500">
                  Suggestions
                </p>
                <ul className="mt-1 list-inside list-disc text-theme-secondary">
                  {dim.suggestions.map((sug, i) => (
                    <li key={i}>{sug}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </details>
      ))}
    </div>
  );
}
