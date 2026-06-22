/** Resume tailor page — upload, score, rewrite, see diff. */

import { useAppStore } from "../store";
import ResumeUpload from "../components/shared/ResumeUpload";
import JDPaste from "../components/shared/JDPaste";
import ScoreGauge from "../components/ats/ScoreGauge";
import DimensionBreakdown from "../components/ats/DimensionBreakdown";
import WeightageRadar from "../components/ats/WeightageRadar";
import ResumeDiff from "../components/ats/ResumeDiff";
import ResumeFingerprint from "../components/ats/ResumeFingerprint";
import DualScore from "../components/standout/DualScore";
import CallbackPredictor from "../components/prediction/CallbackPredictor";

export default function Tailor() {
  const resume = useAppStore((s) => s.resume);
  const resumeFileName = useAppStore((s) => s.resumeFileName);
  const resumeLoading = useAppStore((s) => s.resumeLoading);
  const uploadResume = useAppStore((s) => s.uploadResume);

  const jdText = useAppStore((s) => s.jdText);
  const setJdText = useAppStore((s) => s.setJdText);

  const atsScore = useAppStore((s) => s.atsScore);
  const dualScore = useAppStore((s) => s.dualScore);
  const tailorResult = useAppStore((s) => s.tailorResult);
  const tailorLoading = useAppStore((s) => s.tailorLoading);
  const tailorError = useAppStore((s) => s.tailorError);
  const tailorResume = useAppStore((s) => s.tailorResume);

  const loading = resumeLoading || tailorLoading;

  const handleUpload = async (file: File) => {
    await uploadResume(file);
  };

  const handleTailor = async () => {
    if (!resume || !jdText.trim()) return;
    await tailorResume(resume.id, jdText);
  };

  const canTailor = !!resume && jdText.trim().length > 50;

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Header */}
      <div>
        <h1 className="section-title">Let&apos;s see what we&apos;re working with.</h1>
        <p className="mt-2 section-subtitle">
          Upload your resume and a job description. We&apos;ll score it on 22
          dimensions, show what&apos;s weak, and fix it.
        </p>
      </div>

      {/* Upload section */}
      <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
        <div className="glass-card glow-border p-6">
          <h2 className="text-lg font-semibold text-theme">Resume</h2>
          <div className="mt-4">
            <ResumeUpload
              onUpload={handleUpload}
              loading={loading && !tailorResult}
              fileName={resumeFileName}
            />
          </div>
          {resume && (
            <div className="mt-3 text-xs text-theme-muted">
              <span className="text-emerald-400 font-medium">{resume.contact.name}</span>
              {" · "}
              {resume.total_yoe.toFixed(1)} YoE
              {" · "}
              {resume.seniority_level}
            </div>
          )}
        </div>

        <div className="glass-card glow-border p-6">
          <h2 className="text-lg font-semibold text-theme">Job Description</h2>
          <div className="mt-4">
            <JDPaste value={jdText} onChange={setJdText} />
          </div>
          {jdText.length > 0 && (
            <p className="mt-2 text-xs text-theme-muted">
              {jdText.split(/\s+/).length} words
            </p>
          )}
        </div>
      </div>

      {/* Action button */}
      <button
        onClick={handleTailor}
        disabled={!canTailor || loading}
        className={canTailor && !loading ? "btn-primary" : "btn-secondary opacity-50 cursor-not-allowed"}
      >
        {loading ? (
          <span className="flex items-center gap-2">
            <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
              <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" className="opacity-25" />
              <path d="M4 12a8 8 0 018-8" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
            </svg>
            Scoring & Tailoring...
          </span>
        ) : (
          "Score & Tailor"
        )}
      </button>

      {/* Error */}
      {tailorError && (
        <div className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400 animate-slide-down">
          {tailorError}
        </div>
      )}

      {/* Results */}
      {tailorResult && (
        <div className="space-y-6 animate-slide-up">
          {/* Score summary */}
          <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
            <div className="glass-card flex flex-col items-center p-6">
              <p className="text-xs uppercase text-theme-muted">Before</p>
              <ScoreGauge score={tailorResult.score_before} grade={tailorResult.letter_grade_before} />
            </div>

            <div className="glass-card flex flex-col items-center justify-center p-6">
              <p className="text-xs uppercase text-theme-muted">Improvement</p>
              <p className={`mt-2 text-4xl font-bold ${tailorResult.improvement >= 0 ? "text-emerald-400" : "text-red-400"}`}>
                {tailorResult.improvement >= 0 ? "+" : ""}{tailorResult.improvement.toFixed(1)}
              </p>
              <p className="mt-1 text-sm text-theme-muted">
                {tailorResult.total_changes} changes across {tailorResult.passes_applied.length} passes
              </p>
              {tailorResult.predicted_ats_pass ? (
                <span className="mt-2 rounded-full bg-emerald-500/20 border border-emerald-500/30 px-3 py-1 text-xs font-bold text-emerald-400">
                  Predicted ATS PASS
                </span>
              ) : (
                <span className="mt-2 rounded-full bg-orange-500/20 border border-orange-500/30 px-3 py-1 text-xs font-bold text-orange-400">
                  More work needed
                </span>
              )}
            </div>

            <div className="glass-card flex flex-col items-center p-6">
              <p className="text-xs uppercase text-theme-muted">After</p>
              <ScoreGauge score={tailorResult.score_after} grade={tailorResult.letter_grade_after} />
            </div>
          </div>

          {/* Radar chart */}
          {atsScore?.dimension_scores && (
            <WeightageRadar dimensions={atsScore.dimension_scores} />
          )}

          {/* Dimension breakdown */}
          {atsScore?.dimension_scores && (
            <div className="glass-card p-6">
              <DimensionBreakdown dimensions={atsScore.dimension_scores} />
            </div>
          )}

          {/* DualScore + CallbackPredictor */}
          {dualScore && (
            <>
              <DualScore result={dualScore} />
              {dualScore.callback_prediction && (
                <CallbackPredictor prediction={dualScore.callback_prediction} />
              )}
            </>
          )}

          {/* Resume Fingerprint */}
          {atsScore?.dimension_scores && (
            <div className="glass-card p-6">
              <ResumeFingerprint
                dimensionScores={[
                  ...atsScore.dimension_scores.map((d) => ({
                    id: d.dimension_id, name: d.dimension_name, score: d.raw_score, weight: d.weight,
                  })),
                  ...(dualScore?.standout_score.dimension_scores ?? []).map((d) => ({
                    id: d.dimension_id, name: d.dimension_name, score: d.raw_score, weight: d.weight,
                  })),
                ]}
                combinedScore={dualScore?.combined_score ?? atsScore.total_score}
                letterGrade={dualScore?.combined_grade ?? atsScore.letter_grade}
              />
            </div>
          )}

          {/* Diff view */}
          <div className="glass-card p-6">
            <h3 className="mb-4 text-lg font-semibold text-theme">Resume Changes</h3>
            <ResumeDiff unifiedDiff={tailorResult.unified_diff} changeLog={tailorResult.change_log} />
          </div>
        </div>
      )}

      {/* Empty state */}
      {!tailorResult && !loading && (
        <div className="glass-card p-8 text-center text-theme-muted">
          <svg className="mx-auto h-12 w-12 text-theme-muted opacity-30" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          <p className="mt-4">Upload a resume and paste a JD to see your 22-dimension score breakdown.</p>
        </div>
      )}
    </div>
  );
}
