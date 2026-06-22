/**
 * Analytics — job search analytics dashboard.
 *
 * Sections:
 *  1. One-sentence summary (bold, at top)
 *  2. Funnel visualization
 *  3. Score trends
 *  4. Dimension heatmap
 *  5. This week's wins + focus areas
 */

import { useEffect, useState } from "react";
import api from "../lib/api";
import type { JobSearchAnalytics } from "../lib/types";

function FunnelBar({
  label,
  count,
  maxCount,
  rate,
  benchmark,
}: {
  label: string;
  count: number;
  maxCount: number;
  rate?: string;
  benchmark?: string;
}) {
  const pct = maxCount > 0 ? (count / maxCount) * 100 : 0;
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-xs">
        <span className="text-theme-secondary">{label}</span>
        <span className="font-bold text-theme">{count}</span>
      </div>
      <div className="h-5 w-full rounded-full bg-[var(--bg-tertiary)]">
        <div
          className="h-full rounded-full bg-gradient-to-r from-amber-500 to-amber-400 transition-all duration-700"
          style={{ width: `${Math.max(pct, 2)}%` }}
        />
      </div>
      {rate && (
        <div className="flex items-center gap-2 text-[10px] text-muted-theme">
          <span>{rate}</span>
          {benchmark && (
            <span
              className={
                benchmark.includes("above")
                  ? "text-emerald-400"
                  : benchmark.includes("below")
                    ? "text-red-400"
                    : "text-muted-theme"
              }
            >
              {benchmark}
            </span>
          )}
        </div>
      )}
    </div>
  );
}

function HeatCell({ score }: { score: number }) {
  const bg =
    score >= 70
      ? "bg-emerald-500/20 text-emerald-400"
      : score >= 40
        ? "bg-amber-500/20 text-amber-400"
        : "bg-red-500/20 text-red-400";
  return (
    <span className={`rounded px-2 py-0.5 text-xs font-bold ${bg}`}>
      {score.toFixed(0)}
    </span>
  );
}

export default function Analytics() {
  const [analytics, setAnalytics] = useState<JobSearchAnalytics | null>(null);
  const [loading, setLoading] = useState(true);
  const [clickedApply, setClickedApply] = useState(0);

  useEffect(() => {
    api
      .get<JobSearchAnalytics>("/analytics")
      .then((r) => setAnalytics(r.data))
      .catch(() => {})
      .finally(() => setLoading(false));
    api
      .get<{ count: number }>("/jobs/apply-clicks")
      .then((r) => setClickedApply(r.data.count))
      .catch(() => {});
  }, []);

  if (loading) {
    return (
      <div className="flex h-96 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-amber-500 border-t-transparent" />
      </div>
    );
  }

  if (!analytics) {
    return (
      <div className="p-8 text-center text-muted-theme">
        No analytics data available yet. Start applying to see insights.
      </div>
    );
  }

  const f = analytics.funnel;
  const maxCount = Math.max(f.jobs_discovered, 1);

  const dimEntries = Object.entries(analytics.dimension_heatmap.dimension_averages)
    .sort(([, a], [, b]) => a - b);

  return (
    <div className="mx-auto max-w-4xl space-y-8 p-6">
      {/* 1. Summary */}
      <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 p-6">
        <p className="text-lg font-semibold leading-relaxed text-theme">
          {analytics.one_sentence_summary}
        </p>
      </div>

      {/* 2. Funnel */}
      <div className="rounded-xl border border-[var(--border-primary)] bg-[var(--bg-card)] p-6">
        <h2 className="mb-4 text-sm font-bold uppercase tracking-wider text-muted-theme">
          Application Funnel
        </h2>
        <div className="space-y-3">
          <FunnelBar label="Discovered" count={f.jobs_discovered} maxCount={maxCount} />
          <FunnelBar label="Applied" count={f.jobs_applied} maxCount={maxCount}
            rate={`${(f.conversion_rates.discovered_to_applied * 100).toFixed(0)}% conversion`} />
          <FunnelBar label="Responses" count={f.responses_received} maxCount={maxCount}
            rate={`${(f.conversion_rates.applied_to_response * 100).toFixed(0)}% of applied`}
            benchmark={f.benchmark_comparisons.applied_to_response} />
          <FunnelBar label="Interviews" count={f.interviews_scheduled} maxCount={maxCount}
            rate={`${(f.conversion_rates.response_to_interview * 100).toFixed(0)}% of responses`}
            benchmark={f.benchmark_comparisons.response_to_interview} />
          <FunnelBar label="Offers" count={f.offers_received} maxCount={maxCount}
            rate={`${(f.conversion_rates.interview_to_offer * 100).toFixed(0)}% of interviews`}
            benchmark={f.benchmark_comparisons.interview_to_offer} />
        </div>
      </div>

      {/* 3. Score trend + Rejections + Clicked Apply */}
      <div className="grid grid-cols-3 gap-4">
        <div className="rounded-xl border border-[var(--border-primary)] bg-[var(--bg-card)] p-5">
          <p className="text-xs font-bold uppercase text-muted-theme">Score Trend</p>
          <div className="mt-2 flex items-center gap-3">
            <span className={`text-2xl font-bold ${analytics.is_improving ? "text-emerald-400" : "text-theme-secondary"}`}>
              {analytics.is_improving ? "+" : ""}{analytics.score_improvement}
            </span>
            <span className="text-sm text-muted-theme">
              {analytics.is_improving ? "Improving" : "Stable"}
            </span>
          </div>
        </div>
        <div className="rounded-xl border border-[var(--border-primary)] bg-[var(--bg-card)] p-5">
          <p className="text-xs font-bold uppercase text-muted-theme">Rejections</p>
          <p className="mt-2 text-2xl font-bold text-theme">{f.rejections}</p>
        </div>
        <div className="rounded-xl border border-blue-500/20 bg-blue-500/5 p-5">
          <p className="text-xs font-bold uppercase text-blue-400">Clicked Apply</p>
          <p className="mt-2 text-2xl font-bold text-blue-400">{clickedApply}</p>
          <p className="mt-1 text-[10px] text-muted-theme">distinct jobs</p>
        </div>
      </div>

      {/* 4. Dimension heatmap */}
      {dimEntries.length > 0 && (
        <div className="rounded-xl border border-[var(--border-primary)] bg-[var(--bg-card)] p-5">
          <h2 className="mb-3 text-sm font-bold uppercase tracking-wider text-muted-theme">
            Dimension Heatmap (weakest first)
          </h2>
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
            {dimEntries.map(([dim, score]) => (
              <div
                key={dim}
                className="flex items-center justify-between rounded-lg bg-[var(--bg-tertiary)] px-3 py-2"
              >
                <span className="truncate text-xs text-theme-secondary">
                  {dim.replace(/_/g, " ")}
                </span>
                <HeatCell score={score} />
              </div>
            ))}
          </div>
          <div className="mt-3 flex gap-4 text-xs">
            <span className="text-emerald-400">
              Strongest: {analytics.dimension_heatmap.strongest_dimensions.join(", ")}
            </span>
            <span className="text-red-400">
              Weakest: {analytics.dimension_heatmap.weakest_dimensions.join(", ")}
            </span>
          </div>
        </div>
      )}

      {/* 5. Wins + Focus Areas */}
      <div className="grid grid-cols-2 gap-4">
        <div className="rounded-lg border border-emerald-500/20 bg-emerald-500/5 p-4">
          <p className="text-xs font-bold uppercase text-emerald-400">This Week's Wins</p>
          <ul className="mt-2 space-y-1 text-sm text-theme-secondary">
            {analytics.this_week_wins.length > 0 ? (
              analytics.this_week_wins.map((w, i) => (
                <li key={i} className="flex items-start gap-2">
                  <span className="text-emerald-400">+</span> {w}
                </li>
              ))
            ) : (
              <li className="text-muted-theme">Keep going — wins are coming!</li>
            )}
          </ul>
        </div>
        <div className="rounded-lg border border-amber-500/20 bg-amber-500/5 p-4">
          <p className="text-xs font-bold uppercase text-amber-400">Focus Areas</p>
          <ul className="mt-2 space-y-1 text-sm text-theme-secondary">
            {analytics.focus_areas.map((fa, i) => (
              <li key={i} className="flex items-start gap-2">
                <span className="text-amber-400">!</span> {fa}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
