/** Cover letter page — uses global resume + JD from store. */

import { useAppStore } from "../store";
import { useCoverLetter } from "../hooks/useCoverLetter";
import ResumeUpload from "../components/shared/ResumeUpload";
import JDPaste from "../components/shared/JDPaste";
import WritingSamples from "../components/pitcher/WritingSamples";
import CoverLetterPreview from "../components/pitcher/CoverLetterPreview";
import VoiceProfileCard from "../components/pitcher/VoiceProfileCard";
import CompanyContextCard from "../components/pitcher/CompanyContextCard";

export default function Pitcher() {
  /* Global state — resume persists from Tailor page */
  const resume = useAppStore((s) => s.resume);
  const resumeFileName = useAppStore((s) => s.resumeFileName);
  const resumeLoading = useAppStore((s) => s.resumeLoading);
  const uploadResume = useAppStore((s) => s.uploadResume);

  const jdText = useAppStore((s) => s.jdText);
  const setJdText = useAppStore((s) => s.setJdText);

  const samples = useAppStore((s) => s.writingSamples);
  const setSamples = useAppStore((s) => s.setWritingSamples);

  /* Local cover-letter state */
  const { result, loading, error, generate } = useCoverLetter();

  const handleUpload = async (file: File) => {
    await uploadResume(file);
  };

  const handleGenerate = async () => {
    if (!resume || !jdText.trim()) return;
    await generate(resume.id, jdText, samples);
  };

  const canGenerate = !!resume && jdText.trim().length > 50;

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-theme">
          Sounds like you. Works harder than you.
        </h1>
        <p className="mt-2 text-muted-theme">
          Generate a cover letter that matches your voice and targets the role.
          Add writing samples for better voice matching.
        </p>
      </div>

      {/* Input section */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Resume upload */}
        <div className="glass-card p-6 backdrop-blur-xl shadow-lg rounded-2xl">
          <h2 className="text-lg font-semibold text-theme">Resume</h2>
          <div className="mt-4">
            <ResumeUpload
              onUpload={handleUpload}
              loading={resumeLoading}
              fileName={resumeFileName}
            />
          </div>
          {resume && (
            <div className="mt-3 text-xs text-muted-theme">
              <span className="text-emerald-400 font-medium">{resume.contact.name}</span>
              {" · "}
              {resume.total_yoe.toFixed(1)} YoE
              {" · "}
              {resume.seniority_level}
            </div>
          )}
        </div>

        {/* JD paste */}
        <div className="glass-card p-6 backdrop-blur-xl shadow-lg rounded-2xl">
          <h2 className="text-lg font-semibold text-theme">Job Description</h2>
          <div className="mt-4">
            <JDPaste value={jdText} onChange={setJdText} />
          </div>
          {jdText.length > 0 && (
            <p className="mt-2 text-xs text-muted-theme">
              {jdText.split(/\s+/).length} words
            </p>
          )}
        </div>

        {/* Writing samples */}
        <div className="glass-card p-6 backdrop-blur-xl shadow-lg rounded-2xl">
          <h2 className="mb-4 text-lg font-semibold text-theme">Voice Samples</h2>
          <WritingSamples samples={samples} onChange={setSamples} />
        </div>
      </div>

      {/* Generate button */}
      <button
        onClick={handleGenerate}
        disabled={!canGenerate || loading}
        className={`px-8 py-3 text-sm font-bold transition-all rounded-xl cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed`}
        style={{
          background: canGenerate && !loading ? "linear-gradient(135deg, #00F5A0, #00c47f)" : undefined,
          backgroundColor: !canGenerate || loading ? "rgba(255,255,255,0.05)" : undefined,
          color: canGenerate && !loading ? "#060914" : "#4B5670",
          boxShadow: canGenerate && !loading ? "0 4px 14px rgba(0,245,160,0.3)" : undefined,
        }}
      >
        {loading ? (
          <span className="flex items-center gap-2">
            <svg
              className="h-4 w-4 animate-spin"
              viewBox="0 0 24 24"
              fill="none"
            >
              <circle
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="3"
                className="opacity-25"
              />
              <path
                d="M4 12a8 8 0 018-8"
                stroke="currentColor"
                strokeWidth="3"
                strokeLinecap="round"
              />
            </svg>
            Analyzing Voice & Generating...
          </span>
        ) : (
          "Generate Cover Letter"
        )}
      </button>

      {/* Error */}
      {error && (
        <div className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
          {error}
        </div>
      )}

      {/* Results */}
      {result && (
        <div className="space-y-6">
          {/* Voice + Company side by side */}
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <VoiceProfileCard profile={result.voice_profile} />
            <CompanyContextCard context={result.company_context} />
          </div>

          {/* Cover letter preview */}
          <CoverLetterPreview
            letter={result.cover_letter}
            alternativeOpenings={result.alternative_openings}
          />
        </div>
      )}

      {/* Empty state */}
      {!result && !loading && (
        <div className="glass-card p-8 text-center text-muted-theme backdrop-blur-xl rounded-2xl shadow-lg">
          Upload a resume and paste a JD to generate your personalized cover letter.
        </div>
      )}
    </div>
  );
}
