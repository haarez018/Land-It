/**
 * StandoutBadge — compact badge showing the standout letter grade + spike icon.
 * Used in the Kanban card and application list as a quick visual indicator
 * of how impressive the resume is to a human reader (beyond ATS).
 */

interface Props {
  grade: string;
  spikeDetected: boolean;
  totalScore: number;
}

const gradeColors: Record<string, string> = {
  "A+": "bg-emerald-500/20 text-emerald-400 border-emerald-500/30",
  A: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30",
  "A-": "bg-emerald-500/15 text-emerald-300 border-emerald-500/25",
  "B+": "bg-amber-500/20 text-amber-400 border-amber-500/30",
  B: "bg-amber-500/15 text-amber-300 border-amber-500/25",
  "B-": "bg-amber-500/10 text-amber-300 border-amber-500/20",
  "C+": "bg-orange-500/20 text-orange-400 border-orange-500/30",
  C: "bg-orange-500/15 text-orange-300 border-orange-500/25",
  "C-": "bg-orange-500/10 text-orange-300 border-orange-500/20",
  D: "bg-red-500/20 text-red-400 border-red-500/30",
  F: "bg-red-500/25 text-red-300 border-red-500/40",
};

export default function StandoutBadge({
  grade,
  spikeDetected,
  totalScore,
}: Props) {
  const colorClass =
    gradeColors[grade] ||
    "bg-navy-600/30 text-navy-300 border-navy-600";

  return (
    <div
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 ${colorClass}`}
      title={`Standout Score: ${totalScore} (${grade})${spikeDetected ? " — Spike Detected" : ""}`}
    >
      {spikeDetected && (
        <span className="text-xs text-amber-400" aria-label="Spike detected">
          &#9733;
        </span>
      )}
      <span className="text-xs font-bold">{grade}</span>
      <span className="text-[10px] font-medium opacity-70">Standout</span>
    </div>
  );
}
