interface ResumeVersion {
  version_id: string;
  resume_id: string;
  version_number: number;
  created_at: string;
  source: string;
  target_jd_id?: string;
  target_company?: string;
  ats_score: number;
  standout_score: number;
  combined_score: number;
  callback_probability: number;
  tier: string;
  change_summary: string;
  changes_made: number;
}

interface ImprovementTrend {
  versions: number;
  first_score: number;
  latest_score: number;
  improvement: number;
  trend: "improving" | "stable" | "declining";
}

interface Props {
  versions: ResumeVersion[];
  trend: ImprovementTrend;
}

const SOURCE_LABELS: Record<string, string> = {
  original: "Original",
  tailored: "Tailored",
  manual_edit: "Manual Edit",
  baseline: "Baseline",
};

const TIER_COLORS: Record<string, string> = {
  Standout: "bg-purple-500/20 text-purple-400",
  Strong: "bg-emerald-500/20 text-emerald-400",
  Solid: "bg-blue-500/20 text-blue-400",
  "Needs Work": "bg-amber-500/20 text-amber-400",
  Weak: "bg-red-500/20 text-red-400",
};

const TREND_LABELS: Record<string, { text: string; color: string }> = {
  improving: { text: "Improving", color: "text-emerald-400" },
  stable: { text: "Stable", color: "text-navy-400" },
  declining: { text: "Declining", color: "text-red-400" },
};

function Sparkline({ versions }: { versions: ResumeVersion[] }) {
  if (versions.length < 2) return null;

  const scores = versions.map((v) => v.combined_score);
  const min = Math.min(...scores) - 5;
  const max = Math.max(...scores) + 5;
  const range = max - min || 1;
  const w = 200;
  const h = 40;

  const points = scores
    .map((s, i) => {
      const x = (i / (scores.length - 1)) * w;
      const y = h - ((s - min) / range) * h;
      return `${x},${y}`;
    })
    .join(" ");

  return (
    <svg width={w} height={h} className="inline-block">
      <polyline
        points={points}
        fill="none"
        stroke="#f59e0b"
        strokeWidth="2"
        strokeLinejoin="round"
      />
      {scores.map((s, i) => {
        const x = (i / (scores.length - 1)) * w;
        const y = h - ((s - min) / range) * h;
        return <circle key={i} cx={x} cy={y} r="3" fill="#f59e0b" />;
      })}
    </svg>
  );
}

export default function VersionHistory({ versions, trend }: Props) {
  const trendInfo = TREND_LABELS[trend.trend] ?? TREND_LABELS.stable;
  const sorted = [...versions].sort((a, b) => b.version_number - a.version_number);

  return (
    <div className="space-y-4 rounded-xl border border-navy-700 bg-navy-800 p-6">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-white">Version History</h3>
        <div className="flex items-center gap-3">
          <span className={`text-sm font-bold ${trendInfo.color}`}>
            {trendInfo.text}
          </span>
          {trend.improvement !== 0 && (
            <span
              className={`text-sm font-bold ${
                trend.improvement > 0 ? "text-emerald-400" : "text-red-400"
              }`}
            >
              {trend.improvement > 0 ? "+" : ""}
              {trend.improvement.toFixed(1)} pts
            </span>
          )}
        </div>
      </div>

      {versions.length >= 2 && (
        <div className="flex justify-center py-2">
          <Sparkline versions={versions} />
        </div>
      )}

      <div className="space-y-3">
        {sorted.map((v) => (
          <div
            key={v.version_id}
            className="flex items-center justify-between rounded-lg border border-navy-600 bg-navy-800/50 px-4 py-3"
          >
            <div className="flex items-center gap-4">
              <span className="flex h-8 w-8 items-center justify-center rounded-full bg-navy-700 text-xs font-bold text-white">
                v{v.version_number}
              </span>
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-white">
                    {SOURCE_LABELS[v.source] ?? v.source}
                  </span>
                  {v.target_company && (
                    <span className="text-xs text-navy-400">
                      for {v.target_company}
                    </span>
                  )}
                </div>
                {v.change_summary && (
                  <p className="text-xs text-navy-400">{v.change_summary}</p>
                )}
              </div>
            </div>

            <div className="flex items-center gap-4">
              <span className="text-lg font-bold text-white">
                {v.combined_score.toFixed(0)}
              </span>
              <span
                className={`rounded-full px-2 py-0.5 text-xs font-bold ${
                  TIER_COLORS[v.tier] ?? ""
                }`}
              >
                {v.tier}
              </span>
            </div>
          </div>
        ))}
      </div>

      {versions.length === 0 && (
        <p className="text-center text-sm text-navy-400">
          No versions recorded yet. Score or tailor your resume to start tracking.
        </p>
      )}
    </div>
  );
}
