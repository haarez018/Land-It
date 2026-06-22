/**
 * CallbackPredictor — visualizes the interview callback probability
 * with animated ring, confidence bars, and actionable insights.
 */

import type { CallbackPrediction } from "../../lib/types";

interface Props {
  prediction: CallbackPrediction;
}

function PercentRing({ pct }: { pct: number }) {
  const circumference = 2 * Math.PI * 54;
  const offset = circumference - (pct / 100) * circumference;

  const gradId = `cb-ring-${Math.random().toString(36).slice(2, 8)}`;
  const colors =
    pct >= 50
      ? { start: "#34d399", end: "#10b981" }
      : pct >= 25
        ? { start: "#fbbf24", end: "#f59e0b" }
        : { start: "#f87171", end: "#ef4444" };

  return (
    <div className="relative inline-flex items-center justify-center">
      <svg width="140" height="140" className="-rotate-90">
        <defs>
          <linearGradient id={gradId} x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor={colors.start} />
            <stop offset="100%" stopColor={colors.end} />
          </linearGradient>
          <filter id={`${gradId}-glow`}>
            <feGaussianBlur stdDeviation="4" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>
        <circle cx="70" cy="70" r="54" fill="none" stroke="var(--bg-tertiary)" strokeWidth="10" />
        <circle
          cx="70" cy="70" r="54"
          fill="none"
          stroke={`url(#${gradId})`}
          strokeWidth="10"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          filter={`url(#${gradId}-glow)`}
          className="transition-all duration-1000 ease-out"
        />
      </svg>
      <div className="absolute text-center">
        <p className="text-3xl font-black text-theme">{pct}%</p>
        <p className="text-[10px] font-medium uppercase tracking-wider text-theme-muted">callback</p>
      </div>
    </div>
  );
}

function ConfidenceBar({ lower, upper, probability }: { lower: number; upper: number; probability: number }) {
  const lPct = Math.round(lower * 100);
  const uPct = Math.round(upper * 100);
  const pPct = Math.round(probability * 100);

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-xs text-theme-muted">
        <span>{lPct}%</span>
        <span className="font-medium text-theme-secondary">Confidence: {lPct}% - {uPct}%</span>
        <span>{uPct}%</span>
      </div>
      <div className="relative h-3 w-full rounded-full bg-[var(--bg-tertiary)]">
        <div
          className="absolute h-full rounded-full bg-gradient-to-r from-amber-500/30 to-amber-400/30"
          style={{ left: `${lPct}%`, width: `${Math.max(uPct - lPct, 1)}%` }}
        />
        <div
          className="absolute top-1/2 h-4 w-1 -translate-y-1/2 rounded-full bg-amber-400 shadow-lg shadow-amber-400/50"
          style={{ left: `${pPct}%` }}
        />
      </div>
    </div>
  );
}

export default function CallbackPredictor({ prediction }: Props) {
  const pct = Math.round(prediction.probability * 100);
  const [lower, upper] = prediction.confidence_interval;
  const vsAvg = prediction.vs_average_applicant;
  const vsSign = vsAvg >= 0 ? "+" : "";

  return (
    <div className="space-y-6">
      {/* Main probability display */}
      <div className="glass-card flex flex-col items-center p-8">
        <p className="text-xs font-semibold uppercase tracking-widest text-theme-muted">
          Interview Callback Probability
        </p>
        <div className="mt-4">
          <PercentRing pct={pct} />
        </div>

        {/* Comparison badges */}
        <div className="mt-4 flex flex-wrap items-center justify-center gap-3">
          <span
            className={`rounded-full px-3 py-1.5 text-sm font-bold backdrop-blur-sm ${
              vsAvg >= 0
                ? "bg-emerald-500/15 text-emerald-400 border border-emerald-500/20"
                : "bg-red-500/15 text-red-400 border border-red-500/20"
            }`}
          >
            {vsSign}{Math.round(vsAvg)}% vs average
          </span>
          <span
            className={`rounded-full px-2.5 py-1 text-xs font-medium border ${
              prediction.confidence_level === "high"
                ? "bg-emerald-500/10 text-emerald-300 border-emerald-500/20"
                : prediction.confidence_level === "medium"
                  ? "bg-amber-500/10 text-amber-300 border-amber-500/20"
                  : "bg-red-500/10 text-red-300 border-red-500/20"
            }`}
          >
            {prediction.confidence_level} confidence
          </span>
        </div>

        {/* Confidence interval */}
        <div className="mt-4 w-full max-w-xs">
          <ConfidenceBar lower={lower} upper={upper} probability={prediction.probability} />
        </div>
      </div>

      {/* Positive & negative factors */}
      <div className="grid grid-cols-2 gap-4">
        <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-5 backdrop-blur-sm">
          <p className="text-xs font-semibold uppercase tracking-wider text-emerald-400">Helping You</p>
          <ul className="mt-3 space-y-2 text-sm text-theme-secondary">
            {prediction.top_positive_factors.map((f, i) => (
              <li key={i} className="flex items-start gap-2">
                <span className="mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-full bg-emerald-500/20 text-[10px] text-emerald-400">+</span>
                <span>{f}</span>
              </li>
            ))}
            {prediction.top_positive_factors.length === 0 && (
              <li className="text-theme-muted">No strong positive signals detected</li>
            )}
          </ul>
        </div>

        <div className="rounded-xl border border-red-500/20 bg-red-500/5 p-5 backdrop-blur-sm">
          <p className="text-xs font-semibold uppercase tracking-wider text-red-400">Holding You Back</p>
          <ul className="mt-3 space-y-2 text-sm text-theme-secondary">
            {prediction.top_negative_factors.map((f, i) => (
              <li key={i} className="flex items-start gap-2">
                <span className="mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-full bg-red-500/20 text-[10px] text-red-400">!</span>
                <span>{f}</span>
              </li>
            ))}
            {prediction.top_negative_factors.length === 0 && (
              <li className="text-theme-muted">No major weaknesses detected</li>
            )}
          </ul>
        </div>
      </div>

      {/* What gets you to 50%? */}
      <div className="glass-card p-6">
        <div className="flex items-center justify-between">
          <p className="text-sm font-semibold text-theme">What gets you to 50%?</p>
          <span className="rounded-full bg-[var(--bg-tertiary)] px-3 py-1 text-xs text-theme-muted">
            Need: {prediction.score_needed_for_50pct}
          </span>
        </div>
        <p className="mt-1 text-xs text-theme-muted">
          Current: {prediction.combined_score} | Base rate: {(prediction.base_rate * 100).toFixed(1)}% ({prediction.role_type}, {prediction.seniority_level})
        </p>
        <ul className="mt-4 space-y-3">
          {prediction.fixes_for_10pct_boost.map((fix, i) => (
            <li key={i} className="flex items-start gap-3 rounded-lg border border-[var(--border-primary)] bg-[var(--bg-tertiary)] p-3 transition-all hover:border-amber-500/30">
              <input
                type="checkbox"
                className="mt-0.5 h-4 w-4 rounded border-[var(--border-primary)] bg-[var(--bg-tertiary)] text-amber-500 focus:ring-amber-500/30 accent-amber-500"
              />
              <span className="text-sm text-theme-secondary">{fix}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
