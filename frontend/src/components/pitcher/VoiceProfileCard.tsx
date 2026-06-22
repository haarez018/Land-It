/** Visual display of the detected voice profile. */

import type { VoiceProfile } from "../../lib/types";

interface Props {
  profile: VoiceProfile;
}

const TONE_LABELS: Record<string, string> = {
  warm_professional: "Warm & Professional",
  confident_casual: "Confident & Casual",
  formal_authoritative: "Formal & Authoritative",
};

const FORMALITY_COLORS: Record<string, string> = {
  informal: "text-emerald-400",
  semi_formal: "text-amber-400",
  formal: "text-blue-400",
  very_formal: "text-purple-400",
};

export default function VoiceProfileCard({ profile }: Props) {
  return (
    <div className="rounded-xl border border-navy-700 bg-navy-800 p-5">
      <div className="flex items-center gap-2">
        <svg className="h-5 w-5 text-amber-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M12 1a3 3 0 00-3 3v8a3 3 0 006 0V4a3 3 0 00-3-3z" />
          <path d="M19 10v2a7 7 0 01-14 0v-2" />
          <line x1="12" y1="19" x2="12" y2="23" />
          <line x1="8" y1="23" x2="16" y2="23" />
        </svg>
        <h3 className="text-lg font-semibold text-white">Your Voice Profile</h3>
      </div>

      <div className="mt-4 grid grid-cols-2 gap-4">
        {/* Tone */}
        <div>
          <p className="text-xs uppercase text-navy-500">Tone</p>
          <p className="mt-1 text-sm font-medium text-amber-400">
            {TONE_LABELS[profile.tone] || profile.tone}
          </p>
        </div>

        {/* Formality */}
        <div>
          <p className="text-xs uppercase text-navy-500">Formality</p>
          <p
            className={`mt-1 text-sm font-medium ${
              FORMALITY_COLORS[profile.formality_level] || "text-navy-200"
            }`}
          >
            {profile.formality_level.replace(/_/g, " ")}
          </p>
        </div>

        {/* Sentence length */}
        <div>
          <p className="text-xs uppercase text-navy-500">Avg Sentence</p>
          <p className="mt-1 text-sm font-medium text-navy-200">
            {profile.avg_sentence_length.toFixed(1)} words
          </p>
        </div>

        {/* Vocabulary */}
        <div>
          <p className="text-xs uppercase text-navy-500">Vocabulary</p>
          <p className="mt-1 text-sm font-medium text-navy-200">
            {profile.vocabulary_complexity}
          </p>
        </div>

        {/* Punctuation style */}
        <div>
          <p className="text-xs uppercase text-navy-500">Punctuation</p>
          <p className="mt-1 text-sm font-medium text-navy-200">
            {profile.punctuation_style.replace(/_/g, " ")}
          </p>
        </div>

        {/* Storytelling */}
        <div>
          <p className="text-xs uppercase text-navy-500">Storytelling</p>
          <p className="mt-1 text-sm font-medium text-navy-200">
            {profile.storytelling_style.replace(/_/g, " ")}
          </p>
        </div>
      </div>

      {/* Characteristic phrases */}
      {profile.characteristic_phrases.length > 0 && (
        <div className="mt-4">
          <p className="text-xs uppercase text-navy-500">Characteristic Phrases</p>
          <div className="mt-2 flex flex-wrap gap-2">
            {profile.characteristic_phrases.map((phrase, i) => (
              <span
                key={i}
                className="rounded-full bg-amber-500/10 px-3 py-1 text-xs text-amber-400"
              >
                &ldquo;{phrase}&rdquo;
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Enthusiasm markers */}
      {profile.enthusiasm_markers.length > 0 && (
        <div className="mt-3">
          <p className="text-xs uppercase text-navy-500">Enthusiasm Markers</p>
          <div className="mt-2 flex flex-wrap gap-2">
            {profile.enthusiasm_markers.map((marker, i) => (
              <span
                key={i}
                className="rounded-full bg-emerald-500/10 px-3 py-1 text-xs text-emerald-400"
              >
                {marker}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
