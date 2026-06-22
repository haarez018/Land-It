/**
 * DualScore — side-by-side ATS (14-dim) and Standout (8-dim) score display.
 * Shows the combined 22-dimension score at the top, then ATS and Standout rings.
 */

import ScoreGauge from "../ats/ScoreGauge";
import type { DualScoreResult } from "../../lib/types";

interface Props {
  result: DualScoreResult;
}

export default function DualScore({ result }: Props) {
  const ats = result.ats_score;
  const standout = result.standout_score;

  return (
    <div className="space-y-6">
      {/* Combined score header */}
      <div className="glass-card flex flex-col items-center p-8">
        <p className="text-xs font-semibold uppercase tracking-widest text-theme-muted">
          Combined Score ({result.total_dimensions} dimensions)
        </p>
        <div className="mt-3 flex items-baseline gap-3">
          <span className="text-6xl font-black bg-gradient-to-r from-amber-400 to-amber-500 bg-clip-text text-transparent">
            {result.combined_score}
          </span>
          <span className="text-2xl font-bold text-theme-secondary">
            {result.combined_grade}
          </span>
        </div>
        <p className="mt-4 max-w-md text-center text-sm text-theme-secondary">
          {result.summary}
        </p>
      </div>

      {/* Side-by-side rings */}
      <div className="grid grid-cols-2 gap-4">
        {/* ATS */}
        <div className="glass-card glow-border flex flex-col items-center p-6">
          <p className="mb-3 text-xs font-semibold uppercase tracking-widest text-theme-muted">
            ATS Score
          </p>
          <ScoreGauge score={ats.total_score} grade={ats.letter_grade} />
          <div className="mt-3 flex items-center gap-2">
            <span
              className={`h-2 w-2 rounded-full ${
                ats.predicted_ats_pass ? "bg-emerald-400 shadow-lg shadow-emerald-400/50" : "bg-red-400 shadow-lg shadow-red-400/50"
              }`}
            />
            <span className="text-xs text-theme-secondary">
              {ats.predicted_ats_pass ? "ATS Pass" : "ATS Risk"}
            </span>
          </div>
          <p className="mt-2 text-xs text-theme-muted">
            {ats.dimension_scores.length} dimensions
          </p>
        </div>

        {/* Standout */}
        <div className="glass-card glow-border flex flex-col items-center p-6">
          <p className="mb-3 text-xs font-semibold uppercase tracking-widest text-theme-muted">
            Standout Score
          </p>
          <ScoreGauge score={standout.total_score} grade={standout.letter_grade} />
          <div className="mt-3 flex items-center gap-2">
            <span
              className={`h-2 w-2 rounded-full ${
                standout.spike_detected ? "bg-amber-400 shadow-lg shadow-amber-400/50" : "bg-gray-500"
              }`}
            />
            <span className="text-xs text-theme-secondary">
              {standout.spike_detected ? "Spike Detected" : "No Spike"}
            </span>
          </div>
          <p className="mt-2 text-xs text-theme-muted">
            {standout.dimension_scores.length} dimensions
          </p>
        </div>
      </div>

      {/* Top wins & issues */}
      <div className="grid grid-cols-2 gap-4">
        <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-5 backdrop-blur-sm">
          <p className="text-xs font-semibold uppercase tracking-wider text-emerald-400">
            Top Wins
          </p>
          <ul className="mt-3 space-y-2 text-sm text-theme-secondary">
            {[...ats.top_3_wins, ...standout.top_3_wins].slice(0, 4).map((win, i) => (
              <li key={i} className="flex items-center gap-2">
                <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-emerald-500/20 text-xs text-emerald-400">+</span>
                {win}
              </li>
            ))}
          </ul>
        </div>
        <div className="rounded-xl border border-red-500/20 bg-red-500/5 p-5 backdrop-blur-sm">
          <p className="text-xs font-semibold uppercase tracking-wider text-red-400">
            Top Issues
          </p>
          <ul className="mt-3 space-y-2 text-sm text-theme-secondary">
            {[...ats.top_3_issues, ...standout.top_3_issues].slice(0, 4).map((issue, i) => (
              <li key={i} className="flex items-center gap-2">
                <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-red-500/20 text-xs text-red-400">!</span>
                {issue}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
