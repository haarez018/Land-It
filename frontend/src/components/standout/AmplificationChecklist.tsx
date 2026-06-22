/**
 * AmplificationChecklist — actionable tips to boost standout score.
 * Shows suggestions from the highest-impact standout dimensions,
 * plus general amplification tips from the engine.
 */

import type { StandoutScoreResult } from "../../lib/types";

interface Props {
  result: StandoutScoreResult;
}

export default function AmplificationChecklist({ result }: Props) {
  // Collect suggestions from critical/high priority dimensions first
  const priorityOrder = ["critical", "high", "medium", "low"];
  const sorted = [...result.dimension_scores].sort(
    (a, b) =>
      priorityOrder.indexOf(a.priority) - priorityOrder.indexOf(b.priority),
  );

  const dimensionTips = sorted
    .filter((d) => d.suggestions.length > 0)
    .slice(0, 5);

  const hasContent =
    dimensionTips.length > 0 || result.amplification_tips.length > 0;

  if (!hasContent) {
    return (
      <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-5 text-center">
        <p className="text-sm font-medium text-emerald-400">
          Looking strong!
        </p>
        <p className="mt-1 text-xs text-navy-400">
          No critical improvements needed
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold text-white">
        Amplification Checklist
      </h3>

      {/* Engine-level tips */}
      {result.amplification_tips.length > 0 && (
        <div className="rounded-lg border border-amber-500/20 bg-amber-500/5 p-4">
          <p className="text-xs font-semibold uppercase tracking-wider text-amber-400">
            Quick Wins
          </p>
          <ul className="mt-2 space-y-2">
            {result.amplification_tips.map((tip, i) => (
              <li key={i} className="flex items-start gap-3">
                <input
                  type="checkbox"
                  className="mt-1 h-4 w-4 rounded border-navy-600 bg-navy-800 text-amber-500 focus:ring-amber-500/30"
                />
                <span className="text-sm text-navy-200">{tip}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Per-dimension suggestions */}
      {dimensionTips.map((dim) => (
        <div
          key={dim.dimension_id}
          className="rounded-lg border border-navy-700 bg-navy-800/40 p-4"
        >
          <div className="flex items-center justify-between">
            <p className="text-sm font-medium text-white">
              {dim.dimension_name}
            </p>
            <span className="text-xs text-navy-400">
              {dim.raw_score.toFixed(0)}/100
            </span>
          </div>
          <ul className="mt-2 space-y-2">
            {dim.suggestions.map((sug, i) => (
              <li key={i} className="flex items-start gap-3">
                <input
                  type="checkbox"
                  className="mt-1 h-4 w-4 rounded border-navy-600 bg-navy-800 text-amber-500 focus:ring-amber-500/30"
                />
                <span className="text-sm text-navy-300">{sug}</span>
              </li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
}
