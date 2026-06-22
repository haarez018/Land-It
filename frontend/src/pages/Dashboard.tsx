/** Weekly overview dashboard — shows strategy report, key metrics, and recent activity. */

import { useEffect, useState } from "react";
import { useTrackerStore } from "../store";
import WeeklyReport from "../components/shared/WeeklyReport";

const DEFAULT_STATS = {
  applications_this_week: 0,
  interviews_scheduled: 0,
  avg_ats_score: 0,
  cover_letters_generated: 0,
  coaching_sessions: 0,
  total_applications: 0,
};

export default function Dashboard() {
  const storeStats = useTrackerStore((s) => s.stats);
  const fetchStats = useTrackerStore((s) => s.fetchStats);
  const [loading, setLoading] = useState(true);

  const stats = storeStats || DEFAULT_STATS;

  useEffect(() => {
    fetchStats().finally(() => setLoading(false));
  }, [fetchStats]);

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Header */}
      <div>
        <h1 className="section-title">Here&apos;s where you stand.</h1>
        <p className="mt-2 section-subtitle">Your weekly job search overview.</p>
      </div>

      {/* Key metrics */}
      <div className="grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-6">
        <StatCard label="Applications" value={stats.applications_this_week || "--"} sub="this week" loading={loading} />
        <StatCard label="Interviews" value={stats.interviews_scheduled || "--"} sub="scheduled" loading={loading} />
        <StatCard label="Avg ATS Score" value={stats.avg_ats_score || "--"} sub="after tailoring" loading={loading} />
        <StatCard label="Cover Letters" value={stats.cover_letters_generated || "--"} sub="generated" loading={loading} />
        <StatCard label="Practice Sessions" value={stats.coaching_sessions || "--"} sub="completed" loading={loading} />
        <StatCard label="Total Pipeline" value={stats.total_applications || "--"} sub="all stages" loading={loading} />
      </div>

      {/* Weekly report */}
      <WeeklyReport report={null} />

      {/* Quick actions */}
      <div className="glass-card p-6">
        <h2 className="text-lg font-semibold text-theme">Quick Actions</h2>
        <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <QuickAction
            href="/tailor"
            icon="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
            label="Score & Tailor Resume"
            description="Upload resume + JD for 22-dimension scoring"
          />
          <QuickAction
            href="/pitcher"
            icon="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
            label="Generate Cover Letter"
            description="Voice-matched, company-personalized"
          />
          <QuickAction
            href="/coach"
            icon="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z"
            label="Mock Interview"
            description="JD-specific questions with grading"
          />
          <QuickAction
            href="/tracker"
            icon="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
            label="Track Applications"
            description="Self-updating Kanban board"
          />
        </div>
      </div>

      {/* Recent activity */}
      <div className="glass-card p-6">
        <h2 className="text-lg font-semibold text-theme">Recent Activity</h2>
        <div className="mt-4 space-y-3">
          <ActivityItem
            time="Just now"
            description="Dashboard loaded. Start by uploading a resume on the Tailor page."
            type="info"
          />
        </div>
      </div>
    </div>
  );
}

function StatCard({ label, value, sub, loading }: { label: string; value: string | number; sub: string; loading: boolean }) {
  return (
    <div className="glass-card glow-border p-4">
      <p className="text-xs text-theme-muted">{label}</p>
      {loading ? (
        <div className="mt-2 h-8 w-12 animate-pulse rounded-lg bg-[var(--bg-tertiary)]" />
      ) : (
        <p className="mt-2 stat-value">{value}</p>
      )}
      <p className="mt-1 text-[10px] text-theme-muted">{sub}</p>
    </div>
  );
}

function QuickAction({ href, icon, label, description }: { href: string; icon: string; label: string; description: string }) {
  return (
    <a
      href={href}
      className="group flex items-start gap-3 glass-card glow-border p-4 transition-all duration-300 hover:-translate-y-0.5"
    >
      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-amber-500/20 to-amber-600/10 text-amber-400 transition-all group-hover:from-amber-500/30 group-hover:to-amber-600/20 group-hover:shadow-lg group-hover:shadow-amber-500/10">
        <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d={icon} />
        </svg>
      </div>
      <div>
        <p className="text-sm font-medium text-theme">{label}</p>
        <p className="mt-0.5 text-xs text-theme-muted">{description}</p>
      </div>
    </a>
  );
}

function ActivityItem({ time, description, type }: { time: string; description: string; type: "info" | "success" | "warning" }) {
  const dotColors = { info: "bg-blue-400", success: "bg-emerald-400", warning: "bg-amber-400" };
  return (
    <div className="flex items-start gap-3">
      <div className="mt-1.5 flex flex-col items-center">
        <div className={`h-2 w-2 rounded-full ${dotColors[type]}`} />
        <div className="mt-1 h-6 w-px bg-[var(--border-primary)]" />
      </div>
      <div>
        <p className="text-xs text-theme-secondary">{description}</p>
        <p className="mt-0.5 text-[10px] text-theme-muted">{time}</p>
      </div>
    </div>
  );
}
