interface SkillGap {
  skill: string;
  category: string;
  jd_context: string;
  score_impact: number;
  difficulty: string;
  suggestion: string;
}

interface SkillGapAnalysis {
  total_gaps: number;
  critical_gaps: SkillGap[];
  recommended_gaps: SkillGap[];
  bonus_gaps: SkillGap[];
  matched_skills: string[];
  match_percentage: number;
  total_potential_score_gain: number;
  top_3_highest_impact_gaps: SkillGap[];
  quick_wins: string[];
  short_term: string[];
  long_term: string[];
}

interface Props {
  analysis: SkillGapAnalysis;
}

const DIFF_COLORS: Record<string, string> = {
  easy: "text-emerald-400 bg-emerald-500/10 border-emerald-500/30",
  medium: "text-amber-400 bg-amber-500/10 border-amber-500/30",
  hard: "text-red-400 bg-red-500/10 border-red-500/30",
};

function GapItem({ gap }: { gap: SkillGap }) {
  return (
    <div className="flex items-start justify-between gap-3 rounded-lg border border-navy-600 bg-navy-800/50 p-3">
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="font-semibold text-white">{gap.skill}</span>
          <span
            className={`rounded-full border px-2 py-0.5 text-xs font-bold ${
              DIFF_COLORS[gap.difficulty] ?? DIFF_COLORS.medium
            }`}
          >
            {gap.difficulty}
          </span>
        </div>
        <p className="mt-1 text-xs text-navy-400">{gap.suggestion}</p>
      </div>
      <span className="shrink-0 rounded-full bg-amber-500/20 px-2 py-1 text-xs font-bold text-amber-400">
        +{gap.score_impact} pts
      </span>
    </div>
  );
}

export default function SkillGapCard({ analysis }: Props) {
  const matchColor =
    analysis.match_percentage >= 80
      ? "text-emerald-400"
      : analysis.match_percentage >= 50
        ? "text-amber-400"
        : "text-red-400";

  return (
    <div className="space-y-6 rounded-xl border border-navy-700 bg-navy-800 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-white">Skill Gap Analysis</h3>
        <div className="flex items-center gap-3">
          <span className={`text-2xl font-bold ${matchColor}`}>
            {analysis.match_percentage}%
          </span>
          <span className="text-xs text-navy-400">match</span>
        </div>
      </div>

      {/* Matched */}
      {analysis.matched_skills.length > 0 && (
        <div>
          <p className="text-xs font-semibold uppercase text-emerald-400 mb-2">
            Matched Skills ({analysis.matched_skills.length})
          </p>
          <div className="flex flex-wrap gap-2">
            {analysis.matched_skills.map((s) => (
              <span
                key={s}
                className="rounded-full bg-emerald-500/10 border border-emerald-500/30 px-2.5 py-1 text-xs text-emerald-300"
              >
                {s}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Critical gaps */}
      {analysis.critical_gaps.length > 0 && (
        <div>
          <p className="text-xs font-semibold uppercase text-red-400 mb-2">
            Critical Gaps — Required ({analysis.critical_gaps.length})
          </p>
          <div className="space-y-2">
            {analysis.critical_gaps.map((g) => (
              <GapItem key={g.skill} gap={g} />
            ))}
          </div>
        </div>
      )}

      {/* Recommended gaps */}
      {analysis.recommended_gaps.length > 0 && (
        <div>
          <p className="text-xs font-semibold uppercase text-amber-400 mb-2">
            Recommended — Preferred ({analysis.recommended_gaps.length})
          </p>
          <div className="space-y-2">
            {analysis.recommended_gaps.map((g) => (
              <GapItem key={g.skill} gap={g} />
            ))}
          </div>
        </div>
      )}

      {/* Quick wins */}
      {analysis.quick_wins.length > 0 && (
        <div className="rounded-lg border border-emerald-500/20 bg-emerald-500/5 p-4">
          <p className="text-xs font-semibold uppercase text-emerald-400 mb-2">
            Quick Wins — Close these gaps today
          </p>
          <ul className="space-y-1 text-sm text-navy-200">
            {analysis.quick_wins.map((w, i) => (
              <li key={i} className="flex items-start gap-2">
                <span className="text-emerald-400 mt-0.5">+</span>
                <span>{w}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Short-term */}
      {analysis.short_term.length > 0 && (
        <div className="rounded-lg border border-amber-500/20 bg-amber-500/5 p-4">
          <p className="text-xs font-semibold uppercase text-amber-400 mb-2">
            Short-term — 1-2 weeks
          </p>
          <ul className="space-y-1 text-sm text-navy-200">
            {analysis.short_term.map((w, i) => (
              <li key={i} className="flex items-start gap-2">
                <span className="text-amber-400 mt-0.5">~</span>
                <span>{w}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Total gain */}
      {analysis.total_potential_score_gain > 0 && (
        <p className="text-center text-sm text-navy-300">
          Closing all gaps could add up to{" "}
          <span className="font-bold text-amber-400">
            +{analysis.total_potential_score_gain} points
          </span>{" "}
          to your score
        </p>
      )}
    </div>
  );
}
