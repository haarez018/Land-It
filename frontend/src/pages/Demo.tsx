import { useState } from "react";
import api from "../lib/api";
import ResumeUpload from "../components/shared/ResumeUpload";
import type { DualScoreResult } from "../lib/types";
import DualScore from "../components/standout/DualScore";
import CallbackPredictor from "../components/prediction/CallbackPredictor";
import SalaryCard from "../components/salary/SalaryCard";
import ResumeFingerprint from "../components/ats/ResumeFingerprint";

interface SalaryEstimateData {
  role_type: string;
  seniority: string;
  location: string;
  company: string;
  estimated_range: [number, number];
  estimated_midpoint: number;
  user_position_in_range: "below_mid" | "at_mid" | "above_mid";
  user_estimated_value: number;
  premium_factors: string[];
  discount_factors: string[];
  negotiation_leverage: string[];
  negotiation_talking_points: string[];
  confidence: "high" | "medium" | "low";
  confidence_reason: string;
}

interface DemoResult {
  dual_score: DualScoreResult;
  salary: SalaryEstimateData;
  demo_resume_text: string;
  demo_jd_text: string;
}

const STATS = [
  { label: "Dimensions", value: "22", sub: "14 ATS + 8 Standout" },
  { label: "AI Agents", value: "6", sub: "coordinated system" },
  { label: "API Routes", value: "71+", sub: "fully tested" },
  { label: "API Keys", value: "0", sub: "required" },
];

export default function Demo() {
  const [result, setResult] = useState<DemoResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [customResumeFile, setCustomResumeFile] = useState<File | null>(null);
  const [customJd, setCustomJd] = useState("");
  const [customResult, setCustomResult] = useState<DualScoreResult | null>(null);
  const [customLoading, setCustomLoading] = useState(false);

  const scoreDemo = async () => {
    setLoading(true);
    setError(null);
    try {
      const { data } = await api.get<DemoResult>("/demo/score");
      setResult(data);
    } catch {
      setError("Failed to score demo resume");
    } finally {
      setLoading(false);
    }
  };

  const scoreCustom = async () => {
    if (!customResumeFile || !customJd.trim()) return;
    setCustomLoading(true);
    try {
      const formData = new FormData();
      formData.append("file", customResumeFile);
      const uploadResp = await api.post("/resume/upload", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      const resumeId = uploadResp.data?.id;
      if (!resumeId) throw new Error("Upload failed");
      const { data } = await api.post<DualScoreResult>(
        `/resume/${resumeId}/score/dual`,
        { jd_text: customJd },
      );
      setCustomResult(data);
    } catch {
      setCustomResult(null);
    } finally {
      setCustomLoading(false);
    }
  };

  return (
    <div className="space-y-16">
      {/* Hero */}
      <section className="relative overflow-hidden rounded-2xl py-16 text-center">
        {/* Gradient background */}
        <div className="absolute inset-0 bg-gradient-to-br from-amber-500/10 via-transparent to-indigo-500/10 rounded-2xl" />
        <div className="absolute inset-0 bg-grid-pattern bg-grid opacity-30" />

        <div className="relative space-y-8 px-6">
          {/* Badge */}
          <div className="inline-flex items-center gap-2 rounded-full border border-amber-500/30 bg-amber-500/10 px-4 py-1.5 text-sm font-medium text-amber-400 animate-fade-in">
            <span className="h-2 w-2 rounded-full bg-amber-400 animate-pulse" />
            Live scoring engine — no API keys required
          </div>

          <h1 className="text-5xl font-black tracking-tight text-theme animate-slide-up sm:text-6xl">
            See the{" "}
            <span className="bg-gradient-to-r from-amber-400 via-amber-500 to-orange-500 bg-clip-text text-transparent">
              22 dimensions
            </span>
          </h1>
          <p className="mx-auto max-w-2xl text-lg text-theme-secondary animate-slide-up">
            A senior backend engineer resume scored against a Google SWE job
            description. 14 ATS dimensions to pass the robot, 8 Standout
            dimensions to impress the human. Callback probability. Salary intelligence.
          </p>

          {/* CTA button */}
          <div className="animate-slide-up">
            <button
              onClick={scoreDemo}
              disabled={loading}
              className="group relative inline-flex items-center gap-3 rounded-2xl bg-gradient-to-r from-amber-500 to-amber-600 px-10 py-5 text-lg font-bold text-white shadow-2xl shadow-amber-500/30 transition-all duration-300 hover:shadow-amber-500/50 hover:-translate-y-1 disabled:opacity-60 disabled:hover:translate-y-0"
            >
              {loading ? (
                <>
                  <svg className="h-5 w-5 animate-spin" viewBox="0 0 24 24" fill="none">
                    <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" className="opacity-25" />
                    <path d="M4 12a8 8 0 018-8" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
                  </svg>
                  Scoring 22 dimensions...
                </>
              ) : (
                <>
                  <svg className="h-5 w-5 transition-transform group-hover:scale-110" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" clipRule="evenodd" />
                  </svg>
                  Score This Resume
                </>
              )}
              {/* Glow effect */}
              <div className="absolute inset-0 rounded-2xl bg-gradient-to-r from-amber-400 to-amber-600 opacity-0 blur-xl transition-opacity group-hover:opacity-30" />
            </button>
          </div>

          {error && (
            <p className="text-red-400 animate-fade-in">{error}</p>
          )}

          {/* Stats row */}
          <div className="mx-auto grid max-w-2xl grid-cols-4 gap-4 pt-4 animate-fade-in">
            {STATS.map((s) => (
              <div key={s.label} className="text-center">
                <p className="stat-value">{s.value}</p>
                <p className="text-xs font-semibold text-theme-secondary">{s.label}</p>
                <p className="text-[10px] text-theme-muted">{s.sub}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Demo Results */}
      {result && (
        <section className="space-y-8 animate-slide-up">
          <DualScore result={result.dual_score} />
          {result.dual_score.callback_prediction && (
            <CallbackPredictor prediction={result.dual_score.callback_prediction} />
          )}
          <SalaryCard estimate={result.salary} />
          <div className="glass-card p-6">
            <ResumeFingerprint
              dimensionScores={[
                ...result.dual_score.ats_score.dimension_scores.map((d) => ({
                  id: d.dimension_id,
                  name: d.dimension_name,
                  score: d.raw_score,
                  weight: d.weight,
                })),
                ...result.dual_score.standout_score.dimension_scores.map((d) => ({
                  id: d.dimension_id,
                  name: d.dimension_name,
                  score: d.raw_score,
                  weight: d.weight,
                })),
              ]}
              combinedScore={result.dual_score.combined_score}
              letterGrade={result.dual_score.combined_grade}
            />
          </div>
        </section>
      )}

      {/* Try Your Own */}
      <section className="space-y-8">
        <div className="text-center">
          <h2 className="text-3xl font-bold text-theme">
            Try with your own resume
          </h2>
          <p className="mt-2 text-theme-secondary">
            Upload your resume (PDF/DOCX) and paste a job description to see your 22-dimension score
          </p>
        </div>

        <div className="grid gap-6 md:grid-cols-2">
          <div className="glass-card p-6 space-y-3">
            <label className="text-sm font-medium text-theme-secondary">
              Your Resume (PDF or DOCX)
            </label>
            <ResumeUpload
              onUpload={setCustomResumeFile}
              loading={customLoading}
              fileName={customResumeFile?.name}
            />
          </div>
          <div className="glass-card p-6 space-y-3">
            <label className="text-sm font-medium text-theme-secondary">
              Job Description
            </label>
            <textarea
              value={customJd}
              onChange={(e) => setCustomJd(e.target.value)}
              rows={10}
              className="w-full rounded-xl border border-[var(--border-primary)] bg-[var(--bg-tertiary)] p-4 text-sm text-theme transition-all duration-200 placeholder:text-theme-muted focus:border-amber-500/50 focus:outline-none focus:ring-2 focus:ring-amber-500/20 resize-none"
              placeholder="Paste the job description here..."
            />
          </div>
        </div>

        <div className="text-center">
          <button
            onClick={scoreCustom}
            disabled={customLoading || !customResumeFile || !customJd.trim()}
            className="btn-primary text-base"
          >
            {customLoading ? "Scoring..." : "Score Mine"}
          </button>
        </div>

        {customResult && (
          <div className="space-y-8 animate-slide-up">
            <DualScore result={customResult} />
            {customResult.callback_prediction && (
              <CallbackPredictor prediction={customResult.callback_prediction} />
            )}
          </div>
        )}
      </section>

      {/* Footer */}
      <footer className="border-t border-[var(--border-primary)] py-8 text-center">
        <p className="text-sm text-theme-muted">
          22 scoring dimensions &middot; 6 AI agents &middot; Dynamic 3-axis weighting &middot; Zero API keys
        </p>
        <p className="mt-2 text-xs text-theme-muted">
          Built with FastAPI, React, TypeScript, and TailwindCSS
        </p>
      </footer>
    </div>
  );
}
