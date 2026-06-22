/** Session score tracker showing progress across questions. */

interface QuestionResult {
  questionNumber: number;
  score: number;
  maxScore: number;
  status: "completed" | "current" | "upcoming";
}

interface Props {
  results: QuestionResult[];
  totalScore: number;
  maxTotalScore: number;
  sessionTime: number; // seconds
}

function formatTime(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}:${secs.toString().padStart(2, "0")}`;
}

export default function SessionProgress({
  results,
  totalScore,
  maxTotalScore,
  sessionTime,
}: Props) {
  const completedCount = results.filter((r) => r.status === "completed").length;
  const overallPct = maxTotalScore > 0 ? totalScore / maxTotalScore : 0;

  return (
    <div className="rounded-xl border border-navy-700 bg-navy-800 p-5">
      {/* Header stats */}
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-white">Session Progress</h3>
        <span className="text-xs text-navy-400">
          {formatTime(sessionTime)} elapsed
        </span>
      </div>

      {/* Overall progress bar */}
      <div className="mt-3">
        <div className="flex items-center justify-between text-xs">
          <span className="text-navy-400">
            {completedCount} of {results.length} questions
          </span>
          <span
            className={`font-bold ${
              overallPct >= 0.8
                ? "text-emerald-400"
                : overallPct >= 0.6
                  ? "text-amber-400"
                  : "text-navy-300"
            }`}
          >
            {totalScore} / {maxTotalScore}
          </span>
        </div>
        <div className="mt-1 h-2 overflow-hidden rounded-full bg-navy-700">
          <div
            className="h-2 rounded-full bg-amber-500 transition-all duration-700"
            style={{
              width: `${(completedCount / results.length) * 100}%`,
            }}
          />
        </div>
      </div>

      {/* Question dots */}
      <div className="mt-4 flex items-center gap-2">
        {results.map((r) => (
          <div key={r.questionNumber} className="flex flex-col items-center gap-1">
            <div
              className={`flex h-8 w-8 items-center justify-center rounded-full text-xs font-bold transition-all ${
                r.status === "completed"
                  ? r.score / r.maxScore >= 0.8
                    ? "bg-emerald-500/20 text-emerald-400 ring-1 ring-emerald-500/30"
                    : r.score / r.maxScore >= 0.6
                      ? "bg-amber-500/20 text-amber-400 ring-1 ring-amber-500/30"
                      : "bg-red-500/20 text-red-400 ring-1 ring-red-500/30"
                  : r.status === "current"
                    ? "bg-amber-500/20 text-amber-400 ring-2 ring-amber-500 animate-pulse"
                    : "bg-navy-700 text-navy-500"
              }`}
            >
              {r.status === "completed" ? (
                r.score
              ) : r.status === "current" ? (
                <span className="h-2 w-2 rounded-full bg-amber-400" />
              ) : (
                r.questionNumber
              )}
            </div>
            <span className="text-[9px] text-navy-600">Q{r.questionNumber}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
