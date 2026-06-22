/** Weekly strategy report display component. */

interface WeeklyReportData {
  week_of: string;
  summary: string;
  applications_target: number;
  applications_sent: number;
  interviews_scheduled: number;
  avg_ats_score: number;
  top_opportunities: Array<{
    company: string;
    role: string;
    fit_score: number;
    status: string;
  }>;
  action_items: string[];
  wins: string[];
}

interface Props {
  report: WeeklyReportData | null;
}

export default function WeeklyReport({ report }: Props) {
  if (!report) {
    return (
      <div className="rounded-xl border border-[var(--border-primary)] bg-[var(--bg-card)] p-6">
        <h2 className="text-lg font-semibold text-amber-400">Weekly Report</h2>
        <p className="mt-4 text-theme-secondary">
          Set your weekly goal to get started. The Planner will generate your
          first strategy report on Sunday evening.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Report header */}
      <div className="rounded-xl border border-[var(--border-primary)] bg-[var(--bg-card)] p-6">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-amber-400">Weekly Report</h2>
          <span className="text-xs text-muted-theme">Week of {report.week_of}</span>
        </div>
        <p className="mt-3 text-sm text-theme-secondary">{report.summary}</p>
      </div>

      {/* Progress meters */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <ProgressMeter
          label="Applications"
          current={report.applications_sent}
          target={report.applications_target}
          color="amber"
        />
        <ProgressMeter
          label="Interviews"
          current={report.interviews_scheduled}
          target={3}
          color="emerald"
        />
        <ProgressMeter
          label="Avg ATS Score"
          current={report.avg_ats_score}
          target={85}
          color="blue"
          suffix="/100"
        />
      </div>

      {/* Top opportunities */}
      {report.top_opportunities.length > 0 && (
        <div className="rounded-xl border border-[var(--border-primary)] bg-[var(--bg-card)] p-5">
          <h3 className="text-sm font-semibold text-theme">Top Opportunities</h3>
          <div className="mt-3 space-y-2">
            {report.top_opportunities.map((opp, i) => (
              <div
                key={i}
                className="flex items-center justify-between rounded-lg border border-[var(--border-primary)] bg-[var(--bg-tertiary)] px-4 py-2"
              >
                <div>
                  <p className="text-sm font-medium text-theme">{opp.role}</p>
                  <p className="text-xs text-muted-theme">{opp.company}</p>
                </div>
                <div className="flex items-center gap-3">
                  <span
                    className={`rounded px-2 py-0.5 text-[10px] font-bold ${
                      opp.fit_score >= 80
                        ? "bg-emerald-500/15 text-emerald-400"
                        : "bg-amber-500/15 text-amber-400"
                    }`}
                  >
                    {opp.fit_score}% fit
                  </span>
                  <span className="chip-idle rounded px-2 py-0.5 text-[10px]">
                    {opp.status}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Action items & Wins */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        {report.action_items.length > 0 && (
          <div className="rounded-xl border border-[var(--border-primary)] bg-[var(--bg-card)] p-5">
            <h3 className="text-sm font-semibold text-amber-400">Action Items</h3>
            <ul className="mt-3 space-y-2">
              {report.action_items.map((item, i) => (
                <li key={i} className="flex items-start gap-2 text-xs text-theme-secondary">
                  <input
                    type="checkbox"
                    className="mt-0.5 h-3.5 w-3.5 rounded border-[var(--border-primary)] bg-[var(--bg-tertiary)] accent-amber-500"
                  />
                  {item}
                </li>
              ))}
            </ul>
          </div>
        )}

        {report.wins.length > 0 && (
          <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-5">
            <h3 className="text-sm font-semibold text-emerald-400">
              This Week&apos;s Wins
            </h3>
            <ul className="mt-3 space-y-2">
              {report.wins.map((win, i) => (
                <li key={i} className="flex items-start gap-2 text-xs text-emerald-400">
                  <svg
                    className="mt-0.5 h-3 w-3 flex-shrink-0"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="3"
                  >
                    <polyline points="20 6 9 17 4 12" />
                  </svg>
                  {win}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}

function ProgressMeter({
  label,
  current,
  target,
  color,
  suffix,
}: {
  label: string;
  current: number;
  target: number;
  color: "amber" | "emerald" | "blue";
  suffix?: string;
}) {
  const pct = Math.min(100, (current / target) * 100);
  const barColors = { amber: "bg-amber-500", emerald: "bg-emerald-500", blue: "bg-blue-500" };
  const textColors = { amber: "text-amber-400", emerald: "text-emerald-400", blue: "text-blue-400" };

  return (
    <div className="rounded-xl border border-[var(--border-primary)] bg-[var(--bg-card)] p-4">
      <p className="text-xs text-muted-theme">{label}</p>
      <div className="mt-2 flex items-baseline gap-1">
        <span className={`text-2xl font-bold ${textColors[color]}`}>{current}</span>
        <span className="text-sm text-muted-theme">{suffix || `/ ${target}`}</span>
      </div>
      <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-[var(--bg-tertiary)]">
        <div
          className={`h-1.5 rounded-full ${barColors[color]} transition-all`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
