/**
 * Onboarding — multi-step wizard for first-time users.
 *
 * Steps:
 *  1. Resume upload (paste text or file)
 *  2. Job search preferences
 *  3. Writing voice (optional)
 *  4. Baseline score (the wow moment)
 *  5. Redirect to dashboard
 */

import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useOnboardingStore } from "../store/useOnboardingStore";
import ScoreGauge from "../components/ats/ScoreGauge";
import ResumeUpload from "../components/shared/ResumeUpload";

const ROLE_OPTIONS = [
  { id: "software_engineer_backend", label: "Backend" },
  { id: "software_engineer_frontend", label: "Frontend" },
  { id: "ml_engineer", label: "ML / AI" },
  { id: "data_scientist", label: "Data Science" },
  { id: "product_manager", label: "Product" },
  { id: "devops_sre", label: "DevOps / SRE" },
  { id: "design_ux", label: "Design / UX" },
  { id: "research_scientist", label: "Research" },
];

const SENIORITY_OPTIONS = ["junior", "mid", "senior", "staff_principal"];

const LOCATION_OPTIONS = [
  "san_francisco", "new_york", "seattle", "los_angeles", "boston",
  "austin", "denver", "chicago", "remote_us", "london", "berlin",
  "toronto", "bangalore", "singapore", "tokyo",
];

const SIZE_OPTIONS = [
  { id: "startup", label: "Startup" },
  { id: "mid", label: "Mid-size" },
  { id: "faang", label: "Big Tech" },
];

function ProgressBar({ step }: { step: number }) {
  return (
    <div className="mb-8 flex items-center gap-2">
      {[1, 2, 3, 4].map((s) => (
        <div key={s} className="flex items-center gap-2">
          <div
            className={`flex h-8 w-8 items-center justify-center rounded-full text-sm font-bold ${
              s <= step
                ? "bg-amber-500 text-white"
                : "bg-[var(--bg-tertiary)] text-theme-secondary border border-[var(--border-primary)]"
            }`}
          >
            {s}
          </div>
          {s < 4 && (
            <div
              className={`h-0.5 w-12 ${
                s < step ? "bg-amber-500" : "bg-[var(--border-primary)]"
              }`}
            />
          )}
        </div>
      ))}
    </div>
  );
}

function ChipSelect({
  options,
  selected,
  onChange,
}: {
  options: { id: string; label: string }[];
  selected: string[];
  onChange: (ids: string[]) => void;
}) {
  return (
    <div className="flex flex-wrap gap-2">
      {options.map((opt) => (
        <button
          key={opt.id}
          type="button"
          onClick={() =>
            onChange(
              selected.includes(opt.id)
                ? selected.filter((s) => s !== opt.id)
                : [...selected, opt.id],
            )
          }
          className={`rounded-full px-4 py-1.5 text-sm font-medium transition-colors ${
            selected.includes(opt.id)
              ? "bg-amber-500 text-white"
              : "chip-idle hover:opacity-90"
          }`}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}

export default function Onboarding() {
  const navigate = useNavigate();
  const store = useOnboardingStore();

  // Step 1 state
  const [resumeFile, setResumeFile] = useState<File | null>(null);

  // Step 2 state
  const [roles, setRoles] = useState<string[]>([]);
  const [seniority, setSeniority] = useState("mid");
  const [locations, setLocations] = useState<string[]>([]);
  const [remote] = useState("any");
  const [sizes, setSizes] = useState<string[]>([]);
  const [goal, setGoal] = useState(5);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");

  // Step 3 state
  const [samples, setSamples] = useState("");

  const step = store.currentStep;

  return (
    <div className="mx-auto max-w-2xl px-6 py-12">
      <ProgressBar step={step} />

      {/* ── Step 1: Resume ──────────────────────────── */}
      {step === 1 && (
        <div className="space-y-6">
          <div>
            <h1 className="text-2xl font-bold text-theme">
              Let's see what we're working with
            </h1>
            <p className="mt-1 text-theme-secondary">
              Upload your resume as a PDF or DOCX — we'll parse and analyze it instantly.
            </p>
          </div>

          <ResumeUpload
            onUpload={setResumeFile}
            loading={store.loading}
            fileName={resumeFile?.name}
          />

          {store.resumeSummary && (
            <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-4">
              <p className="text-sm font-semibold text-emerald-500">Resume parsed!</p>
              <div className="mt-2 grid grid-cols-2 gap-2 text-sm text-theme-secondary">
                <p>Name: <span className="text-theme font-medium">{store.resumeSummary.name}</span></p>
                <p>YoE: <span className="text-theme font-medium">{store.resumeSummary.total_yoe}</span></p>
                <p>Level: <span className="text-theme font-medium">{store.resumeSummary.seniority_level}</span></p>
                <p>Domain: <span className="text-theme font-medium">{store.resumeSummary.primary_domain}</span></p>
                <p>Skills: <span className="text-theme font-medium">{store.resumeSummary.skill_count}</span></p>
                <p>Roles: <span className="text-theme font-medium">{store.resumeSummary.work_experience_count}</span></p>
              </div>
              <p className="mt-2 text-xs text-muted-theme">
                Top skills: {store.resumeSummary.top_skills.join(", ")}
              </p>
            </div>
          )}

          {store.error && (
            <p className="text-sm text-red-400">{store.error}</p>
          )}

          <button
            onClick={async () => {
              if (!resumeFile) return;
              const ok = await store.uploadResume(resumeFile);
              if (ok) store.goToStep(2);
            }}
            disabled={!resumeFile || store.loading}
            className="w-full rounded-xl bg-amber-500 py-3 font-bold text-white transition-colors hover:bg-amber-400 disabled:opacity-50"
          >
            {store.loading ? "Analyzing..." : "Next: Tell us what you're looking for"}
          </button>
        </div>
      )}

      {/* ── Step 2: Preferences ─────────────────────── */}
      {step === 2 && (
        <div className="space-y-6">
          <div>
            <h1 className="text-2xl font-bold text-theme">
              What are you looking for?
            </h1>
            <p className="mt-1 text-theme-secondary">
              This helps us score your resume against the right benchmarks.
            </p>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-xs font-medium text-muted-theme">Name</label>
              <input value={name} onChange={(e) => setName(e.target.value)}
                className="mt-1 w-full rounded-lg border px-3 py-2 text-sm input-theme" />
            </div>
            <div>
              <label className="text-xs font-medium text-muted-theme">Email</label>
              <input value={email} onChange={(e) => setEmail(e.target.value)} type="email"
                className="mt-1 w-full rounded-lg border px-3 py-2 text-sm input-theme" />
            </div>
          </div>

          <div>
            <label className="text-xs font-medium text-muted-theme">Target Roles</label>
            <div className="mt-2">
              <ChipSelect options={ROLE_OPTIONS} selected={roles} onChange={setRoles} />
            </div>
          </div>

          <div>
            <label className="text-xs font-medium text-muted-theme">Seniority</label>
            <div className="mt-2 flex gap-2">
              {SENIORITY_OPTIONS.map((s) => (
                <button key={s} type="button" onClick={() => setSeniority(s)}
                  className={`rounded-full px-4 py-1.5 text-sm font-medium transition-colors ${seniority === s ? "bg-amber-500 text-white" : "chip-idle"}`}>
                  {s.replace("_", "/")}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="text-xs font-medium text-muted-theme">Preferred Locations</label>
            <div className="mt-2 flex flex-wrap gap-2">
              {LOCATION_OPTIONS.map((loc) => (
                <button key={loc} type="button"
                  onClick={() => setLocations(locations.includes(loc) ? locations.filter(l => l !== loc) : [...locations, loc])}
                  className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${locations.includes(loc) ? "bg-amber-500 text-white" : "chip-idle"}`}>
                  {loc.replace(/_/g, " ")}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="text-xs font-medium text-muted-theme">Company Size</label>
            <div className="mt-2">
              <ChipSelect options={SIZE_OPTIONS} selected={sizes} onChange={setSizes} />
            </div>
          </div>

          <div>
            <label className="text-xs font-medium text-muted-theme">Weekly Application Goal: {goal}</label>
            <input type="range" min={1} max={15} value={goal} onChange={(e) => setGoal(+e.target.value)}
              className="mt-2 w-full accent-amber-500" />
          </div>

          <button
            onClick={async () => {
              const ok = await store.submitProfile({
                name, email, target_roles: roles, target_seniority: seniority,
                target_locations: locations, remote_preference: remote,
                salary_min: 0, salary_max: 0,
                company_size_preference: sizes, weekly_goal: goal,
              });
              if (ok) store.goToStep(3);
            }}
            disabled={store.loading}
            className="w-full rounded-xl bg-amber-500 py-3 font-bold text-white hover:bg-amber-400 disabled:opacity-50"
          >
            {store.loading ? "Saving..." : "Next: Your writing voice"}
          </button>
        </div>
      )}

      {/* ── Step 3: Writing Samples ─────────────────── */}
      {step === 3 && (
        <div className="space-y-6">
          <div>
            <h1 className="text-2xl font-bold text-theme">Share your voice</h1>
            <p className="mt-1 text-theme-secondary">
              Paste a previous cover letter, email, or LinkedIn about section.
              This helps us write cover letters that sound like YOU, not a robot.
            </p>
          </div>

          <textarea
            value={samples}
            onChange={(e) => setSamples(e.target.value)}
            placeholder="Paste a writing sample here (optional)..."
            className="h-40 w-full rounded-xl border p-4 text-sm input-theme focus:ring-1 focus:ring-[var(--accent)]"
          />

          <div className="flex gap-3">
            <button
              onClick={async () => {
                const sampleList = samples.trim() ? [samples.trim()] : [];
                await store.submitWritingSamples(sampleList);
              }}
              disabled={store.loading}
              className="flex-1 rounded-xl bg-amber-500 py-3 font-bold text-white hover:bg-amber-400 disabled:opacity-50"
            >
              {store.loading ? "Analyzing..." : "Next: See your baseline score"}
            </button>
            <button
              onClick={() => store.goToStep(4)}
              className="rounded-xl border border-[var(--border-primary)] px-6 py-3 text-sm text-theme-secondary hover:border-[var(--border-hover)] transition-colors"
            >
              Skip for now
            </button>
          </div>
        </div>
      )}

      {/* ── Step 4: Baseline Score (The Wow Moment) ── */}
      {step === 4 && (
        <div className="space-y-6">
          <div>
            <h1 className="text-2xl font-bold text-theme">
              Here's where you stand
            </h1>
            <p className="mt-1 text-theme-secondary">
              Your resume scored against a typical{" "}
              {store.profile.target_roles?.[0]?.replace(/_/g, " ") || "backend"} role.
            </p>
          </div>

          {!store.baselineScore && !store.loading && (
            <button
              onClick={() => store.runBaselineScore(store.profile.target_roles?.[0])}
              className="w-full rounded-xl bg-amber-500 py-3 font-bold text-white hover:bg-amber-400"
            >
              Score my resume
            </button>
          )}

          {store.loading && (
            <div className="flex flex-col items-center py-12">
              <div className="h-12 w-12 animate-spin rounded-full border-4 border-amber-500 border-t-transparent" />
              <p className="mt-4 text-sm text-muted-theme">
                Scoring your resume against a typical{" "}
                {store.profile.target_roles?.[0]?.replace(/_/g, " ") || "backend"} job...
              </p>
            </div>
          )}

          {store.baselineScore && (
            <>
              <div className="flex justify-center gap-8">
                <div className="text-center">
                  <p className="text-xs font-medium text-muted-theme">ATS Score</p>
                  <ScoreGauge
                    score={store.baselineScore.ats_score}
                    grade={store.baselineScore.combined_grade}
                  />
                </div>
                <div className="text-center">
                  <p className="text-xs font-medium text-muted-theme">Standout Score</p>
                  <ScoreGauge
                    score={store.baselineScore.standout_score}
                    grade={store.baselineScore.combined_grade}
                  />
                </div>
              </div>

              <div className="text-center">
                <p className="text-3xl font-black text-amber-400">
                  {store.baselineScore.combined_score}
                </p>
                <p className="text-sm text-theme-secondary">Combined Score</p>
                {store.baselineScore.callback_probability !== null && (
                  <p className="mt-1 text-xs text-muted-theme">
                    Estimated callback probability:{" "}
                    {(store.baselineScore.callback_probability * 100).toFixed(0)}%
                  </p>
                )}
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="rounded-lg border border-emerald-500/20 bg-emerald-500/5 p-3">
                  <p className="text-xs font-bold text-emerald-400">Strengths</p>
                  <ul className="mt-1 space-y-0.5 text-xs text-theme-secondary">
                    {store.baselineScore.top_3_wins.map((w, i) => (
                      <li key={i}>+ {w}</li>
                    ))}
                  </ul>
                </div>
                <div className="rounded-lg border border-amber-500/20 bg-amber-500/5 p-3">
                  <p className="text-xs font-bold text-amber-400">Improve</p>
                  <ul className="mt-1 space-y-0.5 text-xs text-theme-secondary">
                    {store.baselineScore.top_3_issues.map((w, i) => (
                      <li key={i}>! {w}</li>
                    ))}
                  </ul>
                </div>
              </div>

              <p className="text-center text-sm text-theme-secondary">
                {store.baselineScore.summary}
              </p>

              <button
                onClick={async () => {
                  await store.completeOnboarding();
                  navigate("/");
                }}
                className="w-full rounded-xl bg-amber-500 py-3 font-bold text-white hover:bg-amber-400"
              >
                Start your job search
              </button>
            </>
          )}
        </div>
      )}
    </div>
  );
}
