import { useState, useEffect } from "react";

const STEPS = [
  {
    emoji: "👋",
    title: "Welcome to Land It!",
    description:
      "Land It is your AI-powered job search co-pilot. It helps you find jobs, tailor your resume, write cover letters, practice interviews, and track every application — all in one place.",
    color: "from-amber-500 to-amber-600",
    hint: null,
  },
  {
    emoji: "📄",
    title: "Start with your resume",
    description:
      "Upload your resume first. Land It uses it to score job matches, tailor your resume to specific roles, and craft personalised cover letters. Go to the Dashboard and hit \"Upload Resume\".",
    color: "from-blue-500 to-blue-600",
    hint: "Dashboard → Upload Resume",
  },
  {
    emoji: "🔍",
    title: "Search live jobs",
    description:
      "Head to the Jobs tab and search for any role — e.g. \"Senior React Developer\". Land It pulls real listings from Remotive & Arbeitnow, ranks them by how well they match your resume, and adds them to your queue.",
    color: "from-amber-500 to-orange-500",
    hint: "Jobs → Search Live Jobs",
  },
  {
    emoji: "✂️",
    title: "Tailor your resume",
    description:
      "Click \"Tailor Resume\" on any job card (or go to the Tailor tab). The AI rewrites your resume to highlight the skills and keywords that matter most for that specific role — boosting your ATS score.",
    color: "from-purple-500 to-purple-600",
    hint: "Jobs → Tailor Resume  ·  or  ·  Tailor tab",
  },
  {
    emoji: "✉️",
    title: "Generate a cover letter",
    description:
      "Click \"Cover Letter\" on any job card (or go to the Pitcher tab). The AI writes a compelling, personalised cover letter based on your resume and the job description.",
    color: "from-emerald-500 to-emerald-600",
    hint: "Jobs → Cover Letter  ·  or  ·  Pitcher tab",
  },
  {
    emoji: "🎤",
    title: "Practice your interview",
    description:
      "Go to the Coach tab and practice common interview questions with AI feedback. The coach listens to your answers and scores them on clarity, confidence, and content.",
    color: "from-pink-500 to-rose-500",
    hint: "Coach tab",
  },
  {
    emoji: "📋",
    title: "Track your applications",
    description:
      "Applied to a job? Hit \"Mark as Applied\" on the job card. Then update the status as things progress — Got Response → Got Interview → Got Offer. See everything on the Tracker board.",
    color: "from-cyan-500 to-cyan-600",
    hint: "Jobs → Mark as Applied  ·  then  ·  Tracker tab",
  },
  {
    emoji: "📊",
    title: "Watch your Analytics",
    description:
      "The Analytics tab shows your full funnel — Applied → Responses → Interviews → Offers — plus score trends, dimension heatmaps, and this week's wins. Check it often to see what's working.",
    color: "from-indigo-500 to-indigo-600",
    hint: "Analytics tab",
  },
  {
    emoji: "🚀",
    title: "You're all set!",
    description:
      "That's the full Land It flow. Start by uploading your resume, then search for jobs. You can reopen this tutorial anytime with the ? button in the top-right corner. Good luck!",
    color: "from-amber-400 to-amber-600",
    hint: null,
  },
];

const STORAGE_KEY = "landit_tutorial_done";

interface TutorialProps {
  open: boolean;
  onClose: () => void;
}

export default function Tutorial({ open, onClose }: TutorialProps) {
  const [step, setStep] = useState(0);

  useEffect(() => {
    if (open) setStep(0);
  }, [open]);

  if (!open) return null;

  const current = STEPS[step];
  const isLast = step === STEPS.length - 1;
  const isFirst = step === 0;

  const handleClose = () => {
    localStorage.setItem(STORAGE_KEY, "true");
    onClose();
  };

  return (
    <div className="fixed inset-0 z-[9999] flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/70 backdrop-blur-sm"
        onClick={handleClose}
      />

      {/* Card */}
      <div className="relative w-full max-w-md rounded-2xl border border-[var(--border-primary)] bg-[var(--bg-secondary)] shadow-2xl shadow-black/40 overflow-hidden">
        {/* Top gradient bar */}
        <div className={`h-1.5 w-full bg-gradient-to-r ${current.color} transition-all duration-500`} />

        {/* Content */}
        <div className="p-7">
          {/* Step counter */}
          <div className="flex items-center justify-between mb-5">
            <span className="text-[10px] font-bold uppercase tracking-widest text-muted-theme">
              Step {step + 1} of {STEPS.length}
            </span>
            <button
              onClick={handleClose}
              className="text-muted-theme hover:text-theme transition-colors"
              aria-label="Close tutorial"
            >
              <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M18 6L6 18M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* Emoji + title */}
          <div className="flex items-center gap-4 mb-4">
            <div className={`flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-gradient-to-br ${current.color} shadow-lg text-2xl`}>
              {current.emoji}
            </div>
            <h2 className="text-xl font-bold text-theme leading-tight">{current.title}</h2>
          </div>

          {/* Description */}
          <p className="text-sm text-theme-secondary leading-relaxed">{current.description}</p>

          {/* Hint pill */}
          {current.hint && (
            <div className="mt-4 inline-flex items-center gap-1.5 rounded-full border border-amber-500/30 bg-amber-500/10 px-3 py-1">
              <svg className="h-3 w-3 text-amber-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
              </svg>
              <span className="text-[11px] font-semibold text-amber-400">{current.hint}</span>
            </div>
          )}

          {/* Progress dots */}
          <div className="mt-6 flex items-center justify-center gap-1.5">
            {STEPS.map((_, i) => (
              <button
                key={i}
                onClick={() => setStep(i)}
                className={`rounded-full transition-all duration-300 ${
                  i === step
                    ? "w-5 h-2 bg-amber-400"
                    : i < step
                    ? "w-2 h-2 bg-amber-400/40"
                    : "w-2 h-2 bg-[var(--bg-tertiary)]"
                }`}
              />
            ))}
          </div>

          {/* Buttons */}
          <div className="mt-5 flex items-center gap-3">
            {!isFirst && (
              <button
                onClick={() => setStep((s) => s - 1)}
                className="rounded-lg border border-[var(--border-primary)] px-4 py-2 text-sm font-semibold text-muted-theme hover:text-theme transition-colors"
              >
                Back
              </button>
            )}
            <button
              onClick={() => (isLast ? handleClose() : setStep((s) => s + 1))}
              className={`flex-1 rounded-lg bg-gradient-to-r ${current.color} px-4 py-2 text-sm font-bold text-white shadow-md transition-all hover:opacity-90 active:scale-[0.98]`}
            >
              {isLast ? "Let's go!" : "Next →"}
            </button>
            {!isLast && (
              <button
                onClick={handleClose}
                className="text-xs text-muted-theme hover:text-theme transition-colors"
              >
                Skip
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export { STORAGE_KEY };
