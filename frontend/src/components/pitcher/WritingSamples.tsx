/** Writing samples input — user pastes text snippets for voice analysis. */

import { useState } from "react";

interface Props {
  samples: string[];
  onChange: (samples: string[]) => void;
  maxSamples?: number;
}

export default function WritingSamples({
  samples,
  onChange,
  maxSamples = 5,
}: Props) {
  const [draft, setDraft] = useState("");

  const addSample = () => {
    const trimmed = draft.trim();
    if (!trimmed || samples.length >= maxSamples) return;
    onChange([...samples, trimmed]);
    setDraft("");
  };

  const removeSample = (index: number) => {
    onChange(samples.filter((_, i) => i !== index));
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <label className="text-sm font-medium text-theme-secondary">
          Writing Samples{" "}
          <span className="text-muted-theme">(optional, helps match your voice)</span>
        </label>
        <span className="text-xs text-muted-theme">
          {samples.length}/{maxSamples}
        </span>
      </div>

      {/* Existing samples */}
      {samples.length > 0 && (
        <div className="space-y-2">
          {samples.map((sample, i) => (
            <div
              key={i}
              className="group relative rounded-lg border border-[var(--border-primary)] bg-[var(--bg-tertiary)] p-3"
            >
              <p className="pr-8 text-xs text-theme-secondary line-clamp-2">
                {sample}
              </p>
              <button
                onClick={() => removeSample(i)}
                className="absolute right-2 top-2 text-muted-theme opacity-0 transition-opacity hover:text-red-400 group-hover:opacity-100"
                aria-label="Remove sample"
              >
                <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M18 6L6 18M6 6l12 12" />
                </svg>
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Add new sample */}
      {samples.length < maxSamples && (
        <div className="space-y-2">
          <textarea
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder="Paste a writing sample (email, blog post, LinkedIn post, etc.)..."
            className="h-20 w-full rounded-lg border p-3 text-sm resize-none transition-colors input-theme focus:ring-1 focus:ring-[var(--accent)]"
          />
          <button
            onClick={addSample}
            disabled={!draft.trim()}
            className={`rounded-lg px-4 py-1.5 text-xs font-semibold transition-colors ${
              draft.trim()
                ? "bg-[var(--bg-tertiary)] text-theme-secondary border border-[var(--border-primary)] hover:border-[var(--accent)]"
                : "bg-[var(--bg-tertiary)] text-muted-theme cursor-not-allowed opacity-50"
            }`}
          >
            + Add Sample
          </button>
        </div>
      )}

      {samples.length === 0 && (
        <p className="text-xs text-muted-theme">
          Add your writing samples so that we could sound like you — LinkedIn posts,
          emails, blog entries, or any professional writing work great.
        </p>
      )}
    </div>
  );
}
