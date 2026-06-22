/**
 * SpikeCard — highlights the candidate's single most impressive "spike" achievement.
 * Only renders when spike_detected is true. Shows the spike factor explanation
 * and a glowing visual treatment.
 */

import type { StandoutDimensionScore } from "../../lib/types";

interface Props {
  spikeScore: StandoutDimensionScore;
  detected: boolean;
}

export default function SpikeCard({ spikeScore, detected }: Props) {
  if (!detected) {
    return (
      <div className="rounded-xl border border-dashed border-navy-600 bg-navy-800/30 p-5 text-center">
        <p className="text-sm text-navy-400">
          No standout spike detected yet
        </p>
        <p className="mt-1 text-xs text-navy-500">
          A spike is a single achievement so impressive it alone justifies an
          interview
        </p>
        {spikeScore.suggestions.length > 0 && (
          <div className="mt-3 text-left">
            <p className="text-xs font-semibold uppercase text-amber-400">
              How to create a spike
            </p>
            <ul className="mt-1 space-y-1 text-xs text-navy-300">
              {spikeScore.suggestions.map((s, i) => (
                <li key={i} className="flex items-start gap-2">
                  <span className="mt-0.5 text-amber-400">&#9650;</span> {s}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="relative overflow-hidden rounded-xl border border-amber-500/30 bg-gradient-to-br from-amber-500/10 to-navy-800/80 p-5">
      {/* Glow effect */}
      <div className="absolute -right-8 -top-8 h-24 w-24 rounded-full bg-amber-400/20 blur-2xl" />

      <div className="relative">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-amber-500/20 text-lg">
            &#9733;
          </div>
          <div>
            <p className="text-sm font-bold text-amber-400">
              Spike Detected
            </p>
            <p className="text-xs text-navy-300">
              Score: {spikeScore.raw_score.toFixed(0)} / 100
            </p>
          </div>
        </div>

        <p className="mt-3 text-sm text-navy-200">{spikeScore.explanation}</p>

        {spikeScore.issues.length > 0 && (
          <div className="mt-3 rounded-lg bg-navy-800/60 p-3">
            <p className="text-xs font-semibold text-amber-400">
              Amplify your spike
            </p>
            <ul className="mt-1 space-y-1">
              {spikeScore.suggestions.map((s, i) => (
                <li
                  key={i}
                  className="flex items-start gap-2 text-xs text-navy-300"
                >
                  <span className="mt-0.5 text-amber-400">&#8593;</span> {s}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}
