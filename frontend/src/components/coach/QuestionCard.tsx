/** Displays a single interview question with category and difficulty badges. */

interface Props {
  question: string;
  category: string;
  difficulty: "easy" | "medium" | "hard";
  questionNumber: number;
  totalQuestions: number;
  isActive: boolean;
}

const DIFFICULTY_STYLES = {
  easy: "bg-emerald-500/10 text-emerald-400",
  medium: "bg-amber-500/10 text-amber-400",
  hard: "bg-red-500/10 text-red-400",
};

const CATEGORY_STYLES: Record<string, string> = {
  behavioral: "bg-blue-500/10 text-blue-400",
  technical: "bg-purple-500/10 text-purple-400",
  situational: "bg-cyan-500/10 text-cyan-400",
  system_design: "bg-orange-500/10 text-orange-400",
  culture_fit: "bg-pink-500/10 text-pink-400",
};

export default function QuestionCard({
  question,
  category,
  difficulty,
  questionNumber,
  totalQuestions,
  isActive,
}: Props) {
  return (
    <div
      className={`rounded-xl border p-6 transition-all ${
        isActive
          ? "border-amber-500/50 bg-navy-800 shadow-lg shadow-amber-500/5"
          : "border-navy-700 bg-navy-800/50 opacity-60"
      }`}
    >
      {/* Header badges */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span
            className={`rounded-full px-2.5 py-0.5 text-[10px] font-bold uppercase ${
              CATEGORY_STYLES[category] || "bg-navy-700 text-navy-300"
            }`}
          >
            {category.replace(/_/g, " ")}
          </span>
          <span
            className={`rounded-full px-2.5 py-0.5 text-[10px] font-bold uppercase ${DIFFICULTY_STYLES[difficulty]}`}
          >
            {difficulty}
          </span>
        </div>
        <span className="text-xs text-navy-500">
          {questionNumber} / {totalQuestions}
        </span>
      </div>

      {/* Question text */}
      <p
        className={`mt-4 text-lg font-medium leading-relaxed ${
          isActive ? "text-white" : "text-navy-400"
        }`}
      >
        {question}
      </p>

      {/* Timer hint */}
      {isActive && (
        <p className="mt-3 text-xs text-navy-500">
          Take your time. A strong answer is 1-2 minutes.
        </p>
      )}
    </div>
  );
}
