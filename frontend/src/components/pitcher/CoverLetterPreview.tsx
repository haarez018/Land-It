/** Cover letter preview with copy/download and quality scores. */

import { useState } from "react";
import type { CoverLetter } from "../../lib/types";

interface Props {
  letter: CoverLetter;
  alternativeOpenings: string[];
}

export default function CoverLetterPreview({
  letter,
  alternativeOpenings,
}: Props) {
  const [copied, setCopied] = useState(false);
  const [showAlts, setShowAlts] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(letter.text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="space-y-4">
      {/* Score badges */}
      <div className="flex flex-wrap gap-3">
        <ScoreBadge
          label="Voice Match"
          score={letter.voice_match_score}
          color="amber"
        />
        <ScoreBadge
          label="Company Fit"
          score={letter.company_personalization_score}
          color="emerald"
        />
        <span className="flex items-center gap-1.5 rounded-full bg-[var(--bg-tertiary)] border border-[var(--border-primary)] px-3 py-1 text-xs text-theme-secondary">
          <svg className="h-3 w-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M4 7V4h16v3M9 20h6M12 4v16" />
          </svg>
          {letter.word_count} words
        </span>
        <span className="flex items-center gap-1.5 rounded-full bg-[var(--bg-tertiary)] border border-[var(--border-primary)] px-3 py-1 text-xs text-theme-secondary">
          {letter.paragraphs} paragraphs
        </span>
      </div>

      {/* Letter text */}
      <div className="rounded-xl border border-[var(--border-primary)] bg-[var(--bg-card)] p-6">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-theme-secondary">
            Cover Letter for {letter.role_title} at {letter.company_name}
          </h3>
          <button
            onClick={handleCopy}
            className="flex items-center gap-1.5 rounded-lg bg-[var(--bg-tertiary)] border border-[var(--border-primary)] px-3 py-1.5 text-xs font-medium text-theme-secondary transition-colors hover:border-[var(--border-hover)] hover:text-theme"
          >
            {copied ? (
              <>
                <svg className="h-3.5 w-3.5 text-emerald-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polyline points="20 6 9 17 4 12" />
                </svg>
                Copied!
              </>
            ) : (
              <>
                <svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
                  <path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1" />
                </svg>
                Copy
              </>
            )}
          </button>
        </div>

        <div className="mt-4 whitespace-pre-wrap font-serif text-sm leading-relaxed text-theme-secondary">
          {letter.text}
        </div>
      </div>

      {/* Requirements addressed */}
      {letter.requirements_addressed.length > 0 && (
        <div className="rounded-xl border border-[var(--border-primary)] bg-[var(--bg-card)] p-4">
          <h4 className="text-sm font-semibold text-emerald-500">
            Requirements Addressed ({letter.requirements_addressed.length})
          </h4>
          <ul className="mt-2 space-y-1">
            {letter.requirements_addressed.map((req, i) => (
              <li key={i} className="flex items-start gap-2 text-xs text-theme-secondary">
                <svg className="mt-0.5 h-3 w-3 flex-shrink-0 text-emerald-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
                  <polyline points="20 6 9 17 4 12" />
                </svg>
                {req}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Verification notes */}
      {letter.verification_notes.length > 0 && (
        <div className="rounded-xl border border-orange-500/20 bg-orange-500/5 p-4">
          <h4 className="text-sm font-semibold text-orange-400">
            Notes to Review
          </h4>
          <ul className="mt-2 space-y-1">
            {letter.verification_notes.map((note, i) => (
              <li key={i} className="flex items-start gap-2 text-xs text-orange-300">
                <span className="mt-0.5">&#x26A0;</span>
                {note}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Alternative openings */}
      {alternativeOpenings.length > 0 && (
        <div className="rounded-xl border border-[var(--border-primary)] bg-[var(--bg-card)] p-4">
          <button
            onClick={() => setShowAlts(!showAlts)}
            className="flex w-full items-center justify-between text-sm font-semibold text-theme-secondary hover:text-theme transition-colors"
          >
            <span>Alternative Openings ({alternativeOpenings.length})</span>
            <svg
              className={`h-4 w-4 transition-transform ${showAlts ? "rotate-180" : ""}`}
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <polyline points="6 9 12 15 18 9" />
            </svg>
          </button>
          {showAlts && (
            <div className="mt-3 space-y-2">
              {alternativeOpenings.map((alt, i) => (
                <div
                  key={i}
                  className="rounded-lg border border-[var(--border-primary)] bg-[var(--bg-tertiary)] p-3"
                >
                  <p className="text-xs text-theme-secondary">
                    <span className="mr-2 font-bold text-amber-500">
                      Option {i + 1}:
                    </span>
                    {alt}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function ScoreBadge({
  label,
  score,
  color,
}: {
  label: string;
  score: number;
  color: "amber" | "emerald" | "blue";
}) {
  const colorMap = {
    amber: {
      bg: "bg-amber-500/10",
      text: "text-amber-400",
      bar: "bg-amber-500",
    },
    emerald: {
      bg: "bg-emerald-500/10",
      text: "text-emerald-400",
      bar: "bg-emerald-500",
    },
    blue: {
      bg: "bg-blue-500/10",
      text: "text-blue-400",
      bar: "bg-blue-500",
    },
  };
  const c = colorMap[color];

  return (
    <div className={`flex items-center gap-2 rounded-full ${c.bg} px-3 py-1`}>
      <span className={`text-xs font-medium ${c.text}`}>{label}</span>
      <div className="h-1.5 w-12 rounded-full bg-[var(--bg-tertiary)]">
        <div
          className={`h-1.5 rounded-full ${c.bar} transition-all`}
          style={{ width: `${score}%` }}
        />
      </div>
      <span className={`text-xs font-bold ${c.text}`}>{score}</span>
    </div>
  );
}
