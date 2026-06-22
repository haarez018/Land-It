/** Graded answer feedback panel with 5-dimension score breakdown. */

interface FeedbackDimension {
  name: string;
  score: number;
  maxScore: number;
  feedback: string;
}

interface Props {
  overallScore: number;
  maxScore: number;
  dimensions: FeedbackDimension[];
  strengths: string[];
  improvements: string[];
  modelAnswer?: string;
}

function getScoreColor(pct: number): string {
  if (pct >= 0.8) return "text-emerald-400";
  if (pct >= 0.6) return "text-amber-400";
  return "text-red-400";
}

function getBarColor(pct: number): string {
  if (pct >= 0.8) return "bg-emerald-500";
  if (pct >= 0.6) return "bg-amber-500";
  return "bg-red-500";
}

export default function FeedbackPanel({
  overallScore,
  maxScore,
  dimensions,
  strengths,
  improvements,
  modelAnswer,
}: Props) {
  const overallPct = overallScore / maxScore;

  return (
    <div className="space-y-4">
      {/* Overall score */}
      <div className="flex items-center gap-4 rounded-xl border border-navy-700 bg-navy-800 p-5">
        <div className="text-center">
          <p
            className={`text-3xl font-bold ${getScoreColor(overallPct)}`}
          >
            {overallScore}
          </p>
          <p className="text-xs text-navy-500">/ {maxScore}</p>
        </div>
        <div className="flex-1">
          <div className="h-3 overflow-hidden rounded-full bg-navy-700">
            <div
              className={`h-3 rounded-full transition-all duration-700 ${getBarColor(overallPct)}`}
              style={{ width: `${overallPct * 100}%` }}
            />
          </div>
          <p className="mt-1 text-xs text-navy-400">
            {overallPct >= 0.8
              ? "Strong answer — well structured with good examples."
              : overallPct >= 0.6
                ? "Decent answer — some areas need more depth."
                : "Needs improvement — focus on specifics and structure."}
          </p>
        </div>
      </div>

      {/* Dimension breakdown */}
      <div className="rounded-xl border border-navy-700 bg-navy-800 p-5">
        <h4 className="text-sm font-semibold text-white">Score Breakdown</h4>
        <div className="mt-3 space-y-3">
          {dimensions.map((dim) => {
            const pct = dim.score / dim.maxScore;
            return (
              <div key={dim.name}>
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium text-navy-300">
                    {dim.name}
                  </span>
                  <span
                    className={`text-xs font-bold ${getScoreColor(pct)}`}
                  >
                    {dim.score}/{dim.maxScore}
                  </span>
                </div>
                <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-navy-700">
                  <div
                    className={`h-1.5 rounded-full transition-all duration-500 ${getBarColor(pct)}`}
                    style={{ width: `${pct * 100}%` }}
                  />
                </div>
                <p className="mt-0.5 text-[11px] text-navy-500">
                  {dim.feedback}
                </p>
              </div>
            );
          })}
        </div>
      </div>

      {/* Strengths & Improvements */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        {strengths.length > 0 && (
          <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-4">
            <h4 className="text-sm font-semibold text-emerald-400">
              What You Did Well
            </h4>
            <ul className="mt-2 space-y-1">
              {strengths.map((s, i) => (
                <li
                  key={i}
                  className="flex items-start gap-2 text-xs text-emerald-300"
                >
                  <svg className="mt-0.5 h-3 w-3 flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
                    <polyline points="20 6 9 17 4 12" />
                  </svg>
                  {s}
                </li>
              ))}
            </ul>
          </div>
        )}

        {improvements.length > 0 && (
          <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 p-4">
            <h4 className="text-sm font-semibold text-amber-400">
              Where to Improve
            </h4>
            <ul className="mt-2 space-y-1">
              {improvements.map((imp, i) => (
                <li
                  key={i}
                  className="flex items-start gap-2 text-xs text-amber-300"
                >
                  <svg className="mt-0.5 h-3 w-3 flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <circle cx="12" cy="12" r="10" />
                    <path d="M12 8v4M12 16h.01" />
                  </svg>
                  {imp}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {/* Model answer */}
      {modelAnswer && (
        <div className="rounded-xl border border-navy-700 bg-navy-800 p-4">
          <h4 className="text-sm font-semibold text-navy-300">
            Example Strong Answer
          </h4>
          <p className="mt-2 text-xs leading-relaxed text-navy-400">
            {modelAnswer}
          </p>
        </div>
      )}
    </div>
  );
}
