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
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import api from "../lib/api";
import type { CalibrationDashboard, JobSearchAnalytics } from "../lib/types";

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
  const [calibration, setCalibration] = useState<CalibrationDashboard | null>(null);
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
    api
      .get<CalibrationDashboard>("/calibration")
      .then((r) => setCalibration(r.data))
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
      <div
        className="glass-card p-6 border rounded-2xl shadow-lg backdrop-blur-xl"
        style={{
          borderColor: "rgba(0,245,160,0.25)",
          backgroundColor: "rgba(0,245,160,0.06)",
        }}
      >
        <p className="text-lg font-semibold leading-relaxed text-theme">
          {analytics.one_sentence_summary}
        </p>
      </div>

      {/* 2. Funnel */}
      <div className="glass-card p-6 backdrop-blur-xl rounded-2xl shadow-lg border border-white/10">
        <h2 className="mb-4 text-xs font-bold uppercase tracking-wider text-muted-theme">
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
        <div className="glass-card p-5 backdrop-blur-xl rounded-2xl shadow-md border border-white/10">
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
        <div className="glass-card p-5 backdrop-blur-xl rounded-2xl shadow-md border border-white/10">
          <p className="text-xs font-bold uppercase text-muted-theme">Rejections</p>
          <p className="mt-2 text-2xl font-bold text-theme">{f.rejections}</p>
        </div>
        <div
          className="glass-card p-5 backdrop-blur-xl rounded-2xl shadow-md border"
          style={{
            borderColor: "rgba(138,43,226,0.3)",
            backgroundColor: "rgba(138,43,226,0.06)",
          }}
        >
          <p className="text-xs font-bold uppercase text-cp-purple" style={{ color: "#8A2BE2" }}>Clicked Apply</p>
          <p className="mt-2 text-2xl font-bold text-cp-purple" style={{ color: "#8A2BE2" }}>{clickedApply}</p>
          <p className="mt-1 text-[10px] text-muted-theme">distinct jobs</p>
        </div>
      </div>

      {/* 4. Dimension heatmap */}
      {dimEntries.length > 0 && (
        <div className="glass-card p-5 backdrop-blur-xl rounded-2xl shadow-md border border-white/10">
          <h2 className="mb-3 text-sm font-bold uppercase tracking-wider text-muted-theme">
            Dimension Heatmap (weakest first)
          </h2>
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
            {dimEntries.map(([dim, score]) => (
              <div
                key={dim}
                className="flex items-center justify-between rounded-xl px-3 py-2 bg-white/5 border border-white/10"
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
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <div className="glass-card p-4 border border-emerald-500/10 bg-emerald-500/5 backdrop-blur-xl rounded-2xl">
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
        <div className="glass-card p-4 border border-cp-accent/25 bg-cp-accent/5 backdrop-blur-xl rounded-2xl">
          <p className="text-xs font-bold uppercase text-cp-accent">Focus Areas</p>
          <ul className="mt-2 space-y-1 text-sm text-theme-secondary">
            {analytics.focus_areas.map((fa, i) => (
              <li key={i} className="flex items-start gap-2">
                <span className="text-cp-accent">!</span> {fa}
              </li>
            ))}
          </ul>
        </div>
      </div>

      {/* 6. Confidence Calibration */}
      {calibration && (
        <div className="glass-card p-6 backdrop-blur-xl rounded-2xl shadow-lg border border-white/10">
          <div className="mb-4 flex items-start justify-between">
            <div>
              <h2 className="text-sm font-bold uppercase tracking-wider text-muted-theme">
                Confidence Calibration
              </h2>
              <p className="mt-1 text-xs text-muted-theme">{calibration.interpretation}</p>
            </div>
            <span
              className={`rounded-full px-3 py-1 text-xs font-bold ${
                calibration.is_well_calibrated
                  ? "bg-emerald-500/20 text-emerald-400"
                  : "bg-cp-accent/20 text-cp-accent"
              }`}
            >
              {calibration.is_well_calibrated ? "Well-calibrated" : "Needs tuning"}
            </span>
          </div>

          <div className="mb-4 grid grid-cols-3 gap-3">
            <div className="rounded-xl bg-white/5 border border-white/10 p-3 text-center">
              <p className="text-xl font-bold text-theme">{calibration.overall_brier.toFixed(3)}</p>
              <p className="text-[10px] text-muted-theme">Brier Score</p>
            </div>
            <div className="rounded-xl bg-white/5 border border-white/10 p-3 text-center">
              <p className="text-xl font-bold text-theme">{(calibration.accuracy * 100).toFixed(0)}%</p>
              <p className="text-[10px] text-muted-theme">Accuracy</p>
            </div>
            <div className="rounded-xl bg-white/5 border border-white/10 p-3 text-center">
              <p className="text-xl font-bold text-theme">{calibration.n_resolved}</p>
              <p className="text-[10px] text-muted-theme">Resolved Apps</p>
            </div>
          </div>

          {calibration.calibration_buckets.length > 0 ? (
            <div>
              <p className="mb-2 text-xs text-muted-theme">Reliability diagram — perfect calibration follows the diagonal</p>
              <ResponsiveContainer width="100%" height={220}>
                <LineChart
                  data={[
                    { predicted: 0, perfect: 0, actual: null },
                    ...calibration.calibration_buckets.map((b) => ({
                      predicted: Math.round(((b.range_low + b.range_high) / 2) * 100),
                      actual: Math.round(b.actual_rate * 100),
                      perfect: Math.round(((b.range_low + b.range_high) / 2) * 100),
                    })),
                    { predicted: 100, perfect: 100, actual: null },
                  ]}
                  margin={{ top: 4, right: 12, left: -12, bottom: 0 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                  <XAxis
                    dataKey="predicted"
                    tickFormatter={(v) => `${v}%`}
                    tick={{ fontSize: 10, fill: "var(--text-muted)" }}
                    label={{ value: "Predicted probability", position: "insideBottom", offset: -2, fontSize: 10, fill: "var(--text-muted)" }}
                  />
                  <YAxis
                    tickFormatter={(v) => `${v}%`}
                    tick={{ fontSize: 10, fill: "var(--text-muted)" }}
                    domain={[0, 100]}
                  />
                  <Tooltip
                    formatter={(v: number) => `${v}%`}
                    contentStyle={{ background: "rgba(13,17,23,0.9)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8, fontSize: 11 }}
                  />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                  <Line type="monotone" dataKey="perfect" stroke="#6b7280" strokeDasharray="4 4" dot={false} name="Perfect" strokeWidth={1} />
                  <Line type="monotone" dataKey="actual" stroke="#00F5A0" strokeWidth={2} dot={{ r: 4, fill: "#00F5A0" }} name="Actual" connectNulls={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <p className="text-center text-sm text-muted-theme py-8">
              No resolved applications with callback predictions yet.
              <br />
              Set <code className="text-amber-400">callback_probability</code> on applications to track calibration.
            </p>
          )}
        </div>
      )}
    </div>
  );
}
