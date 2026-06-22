/**
 * ABComparison — side-by-side A/B test visualization for two resume versions.
 *
 * Layout:
 *  - Two-column header: Version A vs Version B with score gauges
 *  - Center winner badge
 *  - Dimension comparison table (22 rows)
 *  - Merge suggestions
 *  - Recommendation callout
 */

import ScoreGauge from "../ats/ScoreGauge";
import type { ABTestResult } from "../../lib/types";

interface Props {
  result: ABTestResult;
}

function WinnerBadge({
  winner,
  margin,
}: {
  winner: string;
  margin: number;
}) {
  if (winner === "tie") {
    return (
      <div className="rounded-full bg-navy-600/50 px-4 py-2 text-center">
        <p className="text-sm font-bold text-navy-200">Tie</p>
      </div>
    );
  }
  return (
    <div className="rounded-full bg-amber-500/15 px-4 py-2 text-center">
      <p className="text-sm font-bold text-amber-400">
        {winner} wins by {margin.toFixed(1)}%
      </p>
    </div>
  );
}

function DimRow({
  name,
  scoreA,
  scoreB,
  winner,
  delta,
}: {
  name: string;
  scoreA: number;
  scoreB: number;
  winner: string;
  delta: number;
}) {
  const aColor =
    winner === "A" ? "text-emerald-400 font-bold" : "text-navy-300";
  const bColor =
    winner === "B" ? "text-emerald-400 font-bold" : "text-navy-300";

  return (
    <tr className="border-b border-navy-700/50">
      <td className="py-2 pr-3 text-sm text-navy-200">{name}</td>
      <td className={`py-2 px-3 text-right text-sm ${aColor}`}>
        {scoreA.toFixed(0)}
      </td>
      <td className="py-2 px-1">
        <div className="relative mx-auto h-2 w-20 rounded-full bg-navy-700">
          {winner === "A" && (
            <div
              className="absolute right-1/2 h-full rounded-l-full bg-emerald-500/60"
              style={{ width: `${Math.min(delta, 50)}%` }}
            />
          )}
          {winner === "B" && (
            <div
              className="absolute left-1/2 h-full rounded-r-full bg-emerald-500/60"
              style={{ width: `${Math.min(delta, 50)}%` }}
            />
          )}
        </div>
      </td>
      <td className={`py-2 px-3 text-left text-sm ${bColor}`}>
        {scoreB.toFixed(0)}
      </td>
      <td className="py-2 pl-3">
        {winner !== "tie" && (
          <span
            className={`rounded px-1.5 py-0.5 text-[10px] font-bold ${
              winner === "A"
                ? "bg-blue-500/15 text-blue-300"
                : "bg-purple-500/15 text-purple-300"
            }`}
          >
            {winner}
          </span>
        )}
      </td>
    </tr>
  );
}

const recColors: Record<string, string> = {
  use_a: "bg-blue-500/15 text-blue-300 border-blue-500/30",
  use_b: "bg-purple-500/15 text-purple-300 border-purple-500/30",
  combine: "bg-amber-500/15 text-amber-300 border-amber-500/30",
  either: "bg-navy-600/30 text-navy-300 border-navy-600",
};

export default function ABComparison({ result }: Props) {
  const gradeA =
    result.version_a_combined >= 80
      ? "A"
      : result.version_a_combined >= 60
        ? "B"
        : "C";
  const gradeB =
    result.version_b_combined >= 80
      ? "A"
      : result.version_b_combined >= 60
        ? "B"
        : "C";

  return (
    <div className="space-y-6">
      {/* Header: two columns + winner center */}
      <div className="grid grid-cols-3 items-center gap-4">
        <div className="flex flex-col items-center rounded-xl border border-navy-700 bg-navy-800/40 p-5">
          <p className="mb-2 text-xs font-semibold uppercase text-blue-400">
            Version A
          </p>
          <ScoreGauge score={result.version_a_combined} grade={gradeA} />
          <p className="mt-2 text-xs text-navy-400">
            Callback: {(result.version_a_callback * 100).toFixed(0)}%
          </p>
        </div>

        <div className="flex flex-col items-center">
          <WinnerBadge
            winner={result.overall_winner}
            margin={result.win_margin}
          />
        </div>

        <div className="flex flex-col items-center rounded-xl border border-navy-700 bg-navy-800/40 p-5">
          <p className="mb-2 text-xs font-semibold uppercase text-purple-400">
            Version B
          </p>
          <ScoreGauge score={result.version_b_combined} grade={gradeB} />
          <p className="mt-2 text-xs text-navy-400">
            Callback: {(result.version_b_callback * 100).toFixed(0)}%
          </p>
        </div>
      </div>

      {/* Dimension comparison table */}
      <div className="rounded-xl border border-navy-700 bg-navy-800/40 p-4">
        <h3 className="mb-3 text-sm font-semibold text-white">
          Dimension-by-Dimension ({result.dimension_comparisons.length})
        </h3>
        <table className="w-full">
          <thead>
            <tr className="border-b border-navy-600 text-xs uppercase text-navy-400">
              <th className="pb-2 text-left">Dimension</th>
              <th className="pb-2 text-right">A</th>
              <th className="pb-2 text-center">Delta</th>
              <th className="pb-2 text-left">B</th>
              <th className="pb-2 text-left">Winner</th>
            </tr>
          </thead>
          <tbody>
            {result.dimension_comparisons.map((c) => (
              <DimRow
                key={c.dimension_id}
                name={c.dimension_name}
                scoreA={c.score_a}
                scoreB={c.score_b}
                winner={c.winner}
                delta={c.delta}
              />
            ))}
          </tbody>
        </table>
      </div>

      {/* Merge suggestions */}
      <div className="rounded-xl border border-navy-700 bg-navy-800/40 p-4">
        <h3 className="mb-3 text-sm font-semibold text-white">
          Merge Suggestions
        </h3>
        <div className="space-y-2">
          {result.merge_suggestions.map((m, i) => (
            <div
              key={i}
              className="flex items-center gap-3 rounded-lg bg-navy-800/60 p-3"
            >
              <span
                className={`rounded-full border px-2 py-0.5 text-[10px] font-bold uppercase ${
                  recColors[m.recommendation] || recColors.either
                }`}
              >
                {m.recommendation.replace("_", " ")}
              </span>
              <div>
                <p className="text-sm font-medium text-white capitalize">
                  {m.section.replace("_", " ")}
                </p>
                <p className="text-xs text-navy-400">{m.reason}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Recommendation callout */}
      <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 p-5">
        <p className="text-xs font-semibold uppercase text-amber-400">
          Recommendation
        </p>
        <p className="mt-2 text-sm leading-relaxed text-navy-200">
          {result.recommendation}
        </p>
      </div>
    </div>
  );
}
