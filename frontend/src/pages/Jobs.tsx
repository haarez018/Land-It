/** Job queue — live search (Remotive + Arbeitnow, free) + manual JD paste. */

import { useEffect, useState } from "react";
import { useJobStore, useAppStore } from "../store";
import type { JobDescription } from "../lib/types";
import JDPaste from "../components/shared/JDPaste";
import api from "../lib/api";
import { useThemeStore } from "../store/useThemeStore";

export default function Jobs() {
  const theme     = useThemeStore((s) => s.theme);
  const isDark    = theme === "dark";
  const jobs      = useJobStore((s) => s.jobs);
  const loading   = useJobStore((s) => s.loading);
  const storeErr  = useJobStore((s) => s.error);
  const fetchJobs = useJobStore((s) => s.fetchJobs);
  const parseJD   = useJobStore((s) => s.parseJD);
  const dismissJob = useJobStore((s) => s.dismissJob);
  const resume    = useAppStore((s) => s.resume);

  // Live search state
  const [query, setQuery]         = useState("");
  const [location, setLocation]   = useState("");
  const [remoteOnly, setRemoteOnly] = useState(false);
  const [searching, setSearching] = useState(false);
  const [searchResult, setSearchResult] = useState<{ found: number; queued: number; scored: boolean; data_source: string } | null>(null);
  const [searchErr, setSearchErr] = useState("");

  // Manual paste state
  const [jdText, setJdText]       = useState("");
  const [parseLoading, setParseLoading] = useState(false);

  const [appliedStatus, setAppliedStatus] = useState<Record<string, { app_id: string; status: string }>>({});

  useEffect(() => {
    fetchJobs();
    api.get<Record<string, { app_id: string; status: string }>>("/jobs/applied-status")
      .then((r) => setAppliedStatus(r.data))
      .catch(() => {});
  }, [fetchJobs]);

  const handleSearch = async () => {
    if (!query.trim()) return;
    setSearching(true);
    setSearchErr("");
    setSearchResult(null);
    try {
      const res = await api.post("/jobs/search", {
        query: query.trim(),
        location: location.trim(),
        remote_only: remoteOnly,
        resume_id: resume?.id ?? "",
        max_results: 20,
      });
      const d = res.data as { jobs_found: number; jobs_queued: number; scored: boolean; data_source: string };
      setSearchResult({ found: d.jobs_found, queued: d.jobs_queued, scored: d.scored, data_source: d.data_source ?? "scrapers" });
      await fetchJobs(); // refresh queue
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setSearchErr(msg ?? "Search failed. Make sure the backend is running.");
    } finally {
      setSearching(false);
    }
  };

  const handleParse = async () => {
    if (!jdText.trim()) return;
    setParseLoading(true);
    const result = await parseJD(jdText);
    if (result) setJdText("");
    setParseLoading(false);
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-theme">Job Queue</h1>
        <p className="mt-2 text-muted-theme">
          Search real live jobs or paste a JD manually. Scout ranks everything by how
          well it matches your resume.
        </p>
      </div>

      {/* ── Live Search ── */}
      <div className="glass-card p-6 backdrop-blur-xl shadow-lg rounded-2xl">
        <div className="flex items-center gap-2">
          <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-cp-accent/15">
            <svg className="h-4 w-4 text-cp-accent" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <circle cx="11" cy="11" r="8" /><path d="M21 21l-4.35-4.35" />
            </svg>
          </span>
          <h2 className="text-lg font-semibold text-theme">Search Live Jobs</h2>
          <span className="ml-auto rounded-full bg-emerald-500/10 px-2.5 py-0.5 text-[10px] font-semibold text-emerald-400">
            {searchResult?.data_source === "jsearch" ? "live · jsearch" : "FREE · No API key needed"}
          </span>
        </div>
        <p className="mt-1 text-xs text-muted-theme">
          {searchResult?.data_source === "jsearch"
            ? "Pulling live listings via JSearch — LinkedIn, Indeed, Glassdoor & ZipRecruiter."
            : "Pulls real listings from Remotive & Arbeitnow — remote-friendly tech roles."}
          {resume && <span className="ml-1 text-cp-accent">Auto-scoring against your resume.</span>}
        </p>

        <div className="mt-4 flex flex-col gap-3 sm:flex-row">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSearch()}
            placeholder="Role / title  (e.g. Senior React Developer)"
            className="flex-1 rounded-xl px-4 py-2 text-sm font-mono outline-none transition-all"
            style={{
              backgroundColor: isDark ? "rgba(255,255,255,0.05)" : "rgba(0,0,0,0.03)",
              border: `1px solid ${isDark ? "rgba(255,255,255,0.1)" : "rgba(0,0,0,0.08)"}`,
              color: isDark ? "#f0f4ff" : "#111827",
            }}
          />
          <input
            type="text"
            value={location}
            onChange={(e) => setLocation(e.target.value)}
            placeholder="Location (optional)"
            className="w-48 rounded-xl px-4 py-2 text-sm font-mono outline-none transition-all"
            style={{
              backgroundColor: isDark ? "rgba(255,255,255,0.05)" : "rgba(0,0,0,0.03)",
              border: `1px solid ${isDark ? "rgba(255,255,255,0.1)" : "rgba(0,0,0,0.08)"}`,
              color: isDark ? "#f0f4ff" : "#111827",
            }}
          />
          <label className="flex items-center gap-2 text-xs text-theme-secondary cursor-pointer select-none">
            <input
              type="checkbox"
              checked={remoteOnly}
              onChange={(e) => setRemoteOnly(e.target.checked)}
              className="accent-cp-accent h-3.5 w-3.5"
            />
            Remote only
          </label>
        </div>

        <button
          onClick={handleSearch}
          disabled={!query.trim() || searching}
          className="mt-3 text-xs font-semibold rounded-xl transition-all cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
          style={{
            background: query.trim() && !searching ? "linear-gradient(135deg, #00F5A0, #00c47f)" : undefined,
            backgroundColor: !query.trim() || searching ? "rgba(255,255,255,0.05)" : undefined,
            color: query.trim() && !searching ? "#060914" : "#4B5670",
            padding: "8px 20px",
            boxShadow: query.trim() && !searching ? "0 4px 14px rgba(0,245,160,0.3)" : undefined,
          }}
        >
          {searching ? (
            <span className="flex items-center gap-2">
              <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
                <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" className="opacity-25" />
                <path d="M4 12a8 8 0 018-8" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
              </svg>
              Searching live jobs...
            </span>
          ) : "Search Jobs"}
        </button>

        {/* Result feedback */}
        {searchResult && (
          <div className="mt-3 flex items-center gap-2 rounded-xl bg-emerald-500/10 border border-emerald-500/20 px-4 py-2">
            <svg className="h-4 w-4 text-emerald-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
              <polyline points="20 6 9 17 4 12" />
            </svg>
            <span className="text-xs text-emerald-400">
              Found <strong>{searchResult.found}</strong> jobs → added <strong>{searchResult.queued}</strong> to your queue
              {searchResult.scored && resume && " · ranked by fit score against your resume"}
            </span>
          </div>
        )}
        {searchErr && (
          <div className="mt-3 rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-2 text-xs text-red-400">
            {searchErr}
          </div>
        )}
      </div>

      {/* ── Manual Paste ── */}
      <div className="glass-card p-6 backdrop-blur-xl shadow-lg rounded-2xl">
        <h2 className="text-lg font-semibold text-theme">Paste a Job Description</h2>
        <p className="mt-1 text-xs text-muted-theme">Have a specific role in mind? Paste the full JD and Scout will parse and score it.</p>
        <div className="mt-4">
          <JDPaste value={jdText} onChange={setJdText} placeholder="Paste the full job description here..." />
        </div>
        {jdText.length > 0 && (
          <p className="mt-2 text-xs text-muted-theme">{jdText.split(/\s+/).length} words</p>
        )}
        <button
          onClick={handleParse}
          disabled={!jdText.trim() || parseLoading}
          className="mt-4 text-xs font-semibold rounded-xl transition-all cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
          style={{
            background: jdText.trim() && !parseLoading ? "linear-gradient(135deg, #00F5A0, #00c47f)" : undefined,
            backgroundColor: !jdText.trim() || parseLoading ? "rgba(255,255,255,0.05)" : undefined,
            color: jdText.trim() && !parseLoading ? "#060914" : "#4B5670",
            padding: "8px 20px",
            boxShadow: jdText.trim() && !parseLoading ? "0 4px 14px rgba(0,245,160,0.3)" : undefined,
          }}
        >
          {parseLoading ? "Parsing..." : "Parse & Score"}
        </button>
      </div>

      {storeErr && (
        <div className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
          {storeErr}
        </div>
      )}

      {/* ── Queue ── */}
      <div className="glass-card p-6 backdrop-blur-xl shadow-lg rounded-2xl">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-cp-accent">Queue</h2>
          <span className="text-xs text-muted-theme">{jobs.length} jobs</span>
        </div>

        {loading ? (
          <div className="mt-4 flex justify-center py-8">
            <svg className="h-6 w-6 animate-spin text-cp-accent" viewBox="0 0 24 24" fill="none">
              <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" className="opacity-25" />
              <path d="M4 12a8 8 0 018-8" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
            </svg>
          </div>
        ) : jobs.length > 0 ? (
          <div className="mt-4 space-y-3">
            {jobs.map((job) => (
              <JobCard
                key={job.id}
                job={job}
                onDismiss={dismissJob}
                initialApplied={appliedStatus[job.id]}
              />
            ))}
          </div>
        ) : (
          <div className="mt-6 flex flex-col items-center gap-3 py-8 text-center">
            <svg className="h-10 w-10 text-muted-theme opacity-40" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <p className="text-sm text-muted-theme">No jobs yet. Search above to pull live listings.</p>
          </div>
        )}
      </div>
    </div>
  );
}

const STATUS_ORDER = ["submitted", "phone_screen", "interviewing", "offer", "rejected"] as const;
type AppStatus = typeof STATUS_ORDER[number];

const STATUS_LABELS: Record<AppStatus, string> = {
  submitted:    "Applied",
  phone_screen: "Got Response",
  interviewing: "Interviewing",
  offer:        "Offer",
  rejected:     "Rejected",
};

const STATUS_COLORS: Record<AppStatus, string> = {
  submitted:    "bg-blue-500/15 text-blue-400",
  phone_screen: "bg-amber-500/15 text-amber-400",
  interviewing: "bg-purple-500/15 text-purple-400",
  offer:        "bg-emerald-500/15 text-emerald-400",
  rejected:     "bg-red-500/15 text-red-400",
};

function JobCard({
  job,
  onDismiss,
  initialApplied,
}: {
  job: JobDescription;
  onDismiss: (id: string) => void;
  initialApplied?: { app_id: string; status: string };
}) {
  const applyUrl = (job as JobDescription & { source_url?: string }).source_url;
  const [appId, setAppId] = useState<string | null>(initialApplied?.app_id ?? null);
  const [status, setStatus] = useState<AppStatus | null>(
    (initialApplied?.status as AppStatus) ?? null
  );
  const [applying, setApplying] = useState(false);
  const [updating, setUpdating] = useState(false);

  const handleApplyClick = async () => {
    try { await api.post(`/jobs/${job.id}/click-apply`); } catch {}
    if (applyUrl) window.open(applyUrl, "_blank", "noopener,noreferrer");
  };

  const handleMarkApplied = async () => {
    if (status || applying) return;
    setApplying(true);
    try {
      const r = await api.post<{ app_id: string; current_status: string }>(
        `/jobs/${job.id}/mark-applied`
      );
      setAppId(r.data.app_id);
      setStatus(r.data.current_status as AppStatus);
    } catch {}
    setApplying(false);
  };

  const handleStatusUpdate = async (newStatus: AppStatus) => {
    if (!appId || updating) return;
    setUpdating(true);
    try {
      await api.patch(`/jobs/${job.id}/application-status`, { status: newStatus });
      setStatus(newStatus);
    } catch {}
    setUpdating(false);
  };

  const nextStatuses = (): AppStatus[] => {
    if (!status) return [];
    if (status === "rejected" || status === "offer") return [];
    return (["phone_screen", "interviewing", "offer", "rejected"] as AppStatus[]).filter(
      (s) => STATUS_ORDER.indexOf(s) > STATUS_ORDER.indexOf(status)
    );
  };

  const theme = useThemeStore((s) => s.theme);
  const isDark = theme === "dark";

  return (
    <div
      className="glass-card p-4 backdrop-blur-xl transition-all rounded-2xl"
      style={{
        backgroundColor: isDark ? "rgba(255,255,255,0.02)" : "rgba(255,255,255,0.7)",
        borderColor: isDark ? "rgba(255,255,255,0.06)" : "rgba(0,0,0,0.06)",
      }}
      onMouseEnter={(e) => { e.currentTarget.style.borderColor = "#00F5A0"; }}
      onMouseLeave={(e) => { e.currentTarget.style.borderColor = ""; }}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <h3 className="text-sm font-semibold text-theme truncate">{job.title || "Untitled Role"}</h3>
            {job.fit_score != null && job.fit_score > 0 && (
              <span className={`shrink-0 rounded px-2 py-0.5 text-[10px] font-bold ${
                job.fit_score >= 80 ? "bg-emerald-500/15 text-emerald-400"
                  : job.fit_score >= 60 ? "bg-amber-500/15 text-amber-400"
                  : "bg-red-500/15 text-red-400"
              }`}>
                {Math.round(job.fit_score)}% fit
              </span>
            )}
            {status && (
              <span className={`shrink-0 rounded-full px-2 py-0.5 text-[10px] font-bold ${STATUS_COLORS[status]}`}>
                {STATUS_LABELS[status]}
              </span>
            )}
          </div>
          <p className="mt-0.5 text-xs text-muted-theme">
            {job.company || "Unknown Company"}
            {job.location && ` · ${job.location}`}
            {job.remote_policy && ` · ${job.remote_policy}`}
            {(job as JobDescription & { salary_range?: string }).salary_range &&
              ` · ${(job as JobDescription & { salary_range?: string }).salary_range}`}
          </p>
        </div>
        <button onClick={() => onDismiss(job.id)} className="shrink-0 text-muted-theme hover:text-red-400 transition-colors" aria-label="Dismiss">
          <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M18 6L6 18M6 6l12 12" />
          </svg>
        </button>
      </div>

      {/* Badges */}
      <div className="mt-2 flex flex-wrap gap-1.5">
        {job.seniority_level && (
          <span className="chip-idle rounded px-2 py-0.5 text-[10px]">{job.seniority_level}</span>
        )}
        {job.employment_type && (
          <span className="chip-idle rounded px-2 py-0.5 text-[10px]">{job.employment_type}</span>
        )}
      </div>

      {/* Skills */}
      {job.required_skills.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1">
          {job.required_skills.slice(0, 8).map((skill) => (
            <span key={skill} className="rounded-full bg-blue-500/10 px-2 py-0.5 text-[10px] text-blue-400">{skill}</span>
          ))}
          {job.required_skills.length > 8 && (
            <span className="text-[10px] text-muted-theme">+{job.required_skills.length - 8} more</span>
          )}
        </div>
      )}

      {/* Tech stack */}
      {job.tech_stack.length > 0 && (
        <div className="mt-1 flex flex-wrap gap-1">
          {job.tech_stack.slice(0, 6).map((tech) => (
            <span key={tech} className="rounded-full bg-purple-500/10 px-2 py-0.5 text-[10px] text-purple-400">{tech}</span>
          ))}
        </div>
      )}

      {/* Primary actions */}
      <div className="mt-3 flex flex-wrap gap-2">
        <a
          href={`/tailor?jd=${encodeURIComponent(job.raw_text.slice(0, 200))}`}
          className="rounded-xl border border-cp-accent/30 bg-cp-accent/5 px-3 py-1 text-xs font-semibold text-cp-accent transition-all hover:bg-cp-accent/15"
        >
          Tailor Resume
        </a>
        <a
          href={`/pitcher?jd=${encodeURIComponent(job.raw_text.slice(0, 200))}`}
          className="rounded-xl border border-cp-accent/30 bg-cp-accent/5 px-3 py-1 text-xs font-semibold text-cp-accent transition-all hover:bg-cp-accent/15"
        >
          Cover Letter
        </a>
        {applyUrl && (
          <button
            onClick={handleApplyClick}
            className="rounded-xl border border-cp-purple/30 bg-cp-purple/5 px-3 py-1 text-xs font-semibold text-cp-purple transition-all hover:bg-cp-purple/15"
          >
            Apply ↗
          </button>
        )}
        {!status && (
          <button
            onClick={handleMarkApplied}
            disabled={applying}
            className="rounded-xl border border-white/10 bg-white/5 px-3 py-1 text-xs font-semibold text-muted-theme transition-all hover:border-cp-accent hover:text-cp-accent disabled:opacity-50"
          >
            {applying ? "Saving..." : "Mark as Applied"}
          </button>
        )}
      </div>

      {/* Status progression — only visible after marking applied */}
      {status && nextStatuses().length > 0 && (
        <div className="mt-2 flex flex-wrap items-center gap-2">
          <span className="text-[10px] text-muted-theme">Update status:</span>
          {nextStatuses().map((s) => (
            <button
              key={s}
              onClick={() => handleStatusUpdate(s)}
              disabled={updating}
              className={`rounded px-2.5 py-0.5 text-[10px] font-semibold transition-colors disabled:opacity-50 ${
                s === "rejected"
                  ? "bg-red-500/10 text-red-400 hover:bg-red-500/20"
                  : s === "offer"
                  ? "bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20"
                  : "bg-[var(--bg-tertiary)] text-muted-theme hover:bg-purple-500/10 hover:text-purple-400"
              }`}
            >
              {s === "phone_screen" ? "Got Response" : s === "interviewing" ? "Got Interview" : s === "offer" ? "Got Offer!" : "Rejected"}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
