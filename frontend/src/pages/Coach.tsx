/** Voice interview coaching page — question, record, grade, feedback. */

import { useRef, useState } from "react";
import api from "../lib/api";
import JDPaste from "../components/shared/JDPaste";
import VoiceWave from "../components/coach/VoiceWave";
import QuestionCard from "../components/coach/QuestionCard";
import FeedbackPanel from "../components/coach/FeedbackPanel";
import SessionProgress from "../components/coach/SessionProgress";
import { useThemeStore } from "../store/useThemeStore";

type SessionPhase = "setup" | "question" | "recording" | "feedback" | "summary";

interface Question {
  id: string;
  text: string;
  category: string;
  difficulty: "easy" | "medium" | "hard";
  question_number: number;
  total_questions: number;
}

interface DimensionGrade {
  name: string;
  score: number;
  max_score: number;
  feedback: string;
}

interface Grade {
  question_id: string;
  overall_score: number;
  max_score: number;
  dimensions: DimensionGrade[];
  strengths: string[];
  improvements: string[];
  model_answer: string;
}

interface Summary {
  total_score: number;
  max_score: number;
  score_pct: number;
  questions_answered: number;
  total_questions: number;
  grade_letter: string;
  all_strengths: string[];
  all_improvements: string[];
}

type ConnMode = "live" | "buffered" | null;

function getWsUrl(sid: string): string {
  const apiUrl = import.meta.env.VITE_API_URL as string | undefined;
  if (apiUrl) {
    return `${apiUrl.replace(/^http/, "ws")}/ws/coach/${sid}`;
  }
  return `ws://localhost:8000/ws/coach/${sid}`;
}

export default function Coach() {
  const theme = useThemeStore((s) => s.theme);
  const isDark = theme === "dark";
  const [phase, setPhase] = useState<SessionPhase>("setup");
  const [jdText, setJdText] = useState("");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [questions, setQuestions] = useState<Question[]>([]);
  const [currentQ, setCurrentQ] = useState(0);
  const [answerText, setAnswerText] = useState("");
  const [isRecording, setIsRecording] = useState(false);
  const [sessionTime, setSessionTime] = useState(0);
  const [currentGrade, setCurrentGrade] = useState<Grade | null>(null);
  const [grades, setGrades] = useState<Grade[]>([]);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [connMode, setConnMode] = useState<ConnMode>(null);
  const [streamText, setStreamText] = useState("");
  const wsRef = useRef<WebSocket | null>(null);

  const handleStartSession = async () => {
    if (jdText.trim().length < 50) return;
    setLoading(true);
    setError(null);
    try {
      const { data: session } = await api.post("/coach/session/start", {
        jd_text: jdText,
        question_count: 5,
      });
      setSessionId(session.session_id);

      const { data: qs } = await api.get<Question[]>(
        `/coach/session/${session.session_id}/questions`
      );
      setQuestions(qs);
      setCurrentQ(0);
      setGrades([]);
      setSummary(null);
      setPhase("question");

      // Attempt WebSocket; fall back to SSE/buffered if it doesn't connect within 2 s
      const ws = new WebSocket(getWsUrl(session.session_id));
      let resolved = false;
      const timer = setTimeout(() => {
        if (!resolved) {
          resolved = true;
          ws.close();
          setConnMode("buffered");
        }
      }, 2000);
      ws.onopen = () => {
        if (!resolved) {
          resolved = true;
          clearTimeout(timer);
          setConnMode("live");
          wsRef.current = ws;
        }
      };
      ws.onerror = () => {
        if (!resolved) {
          resolved = true;
          clearTimeout(timer);
          setConnMode("buffered");
        }
      };
      ws.onclose = () => {
        if (wsRef.current === ws) {
          wsRef.current = null;
          setConnMode("buffered");
        }
      };
      ws.onmessage = (evt) => {
        try {
          const msg = JSON.parse(evt.data) as { text?: string; done?: boolean; error?: string };
          if (msg.text) setStreamText((prev) => prev + msg.text);
          if (msg.done || msg.error) setLoading(false);
        } catch {
          // ignore malformed frames
        }
      };

      const interval = setInterval(() => {
        setSessionTime((t) => t + 1);
      }, 1000);
      // cleanup stored as closure on session start only — intentional for demo scope
      setTimeout(() => clearInterval(interval), 60 * 60 * 1000);
    } catch (e: any) {
      setError(e.response?.data?.detail || "Failed to start session");
    } finally {
      setLoading(false);
    }
  };

  const handleStartRecording = () => {
    setIsRecording(true);
    setPhase("recording");
  };

  const handleStopRecording = () => {
    setIsRecording(false);
    setPhase("feedback");
  };

  const handleSubmitAnswer = async () => {
    if (!sessionId || !answerText.trim()) return;
    setLoading(true);
    try {
      const { data: grade } = await api.post<Grade>(
        `/coach/session/${sessionId}/answer`,
        { answer_text: answerText, duration_seconds: 0 }
      );
      setCurrentGrade(grade);
      setGrades((prev) => [...prev, grade]);
      setAnswerText("");
      setPhase("feedback");
    } catch (e: any) {
      setError(e.response?.data?.detail || "Failed to grade answer");
    } finally {
      setLoading(false);
    }
  };

  const handleNextQuestion = async () => {
    if (currentQ < questions.length - 1) {
      setCurrentQ((q) => q + 1);
      setCurrentGrade(null);
      setPhase("question");
    } else {
      await fetchSummary();
    }
  };

  const fetchSummary = async () => {
    if (!sessionId) return;
    setLoading(true);
    try {
      const { data } = await api.get<Summary>(`/coach/session/${sessionId}/summary`);
      setSummary(data);
      setPhase("summary");
    } catch {
      setPhase("summary");
    } finally {
      setLoading(false);
    }
  };

  const sessionResults = questions.map((_, i) => {
    const grade = grades[i];
    return {
      questionNumber: i + 1,
      score: grade ? grade.overall_score : 0,
      maxScore: grade ? grade.max_score : 10,
      status: (
        i < currentQ || phase === "summary"
          ? "completed"
          : i === currentQ
            ? "current"
            : "upcoming"
      ) as "completed" | "current" | "upcoming",
    };
  });

  const totalScore = grades.reduce((s, g) => s + g.overall_score, 0);
  const maxTotalScore = grades.reduce((s, g) => s + g.max_score, 0) || questions.length * 10;

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold text-theme">
            Ask me the hard ones. I won&apos;t judge.
          </h1>
          <p className="mt-2 text-theme-secondary">
            Practice with AI-generated questions from the actual JD. Get graded
            feedback on every answer.
          </p>
        </div>
        {connMode && (
          <span
            className={`mt-1 flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-bold ${
              connMode === "live"
                ? "bg-emerald-500/15 text-emerald-400"
                : "bg-amber-500/15 text-amber-400"
            }`}
          >
            <span
              className={`inline-block h-2 w-2 rounded-full ${
                connMode === "live" ? "animate-pulse bg-emerald-400" : "bg-amber-400"
              }`}
            />
            {connMode === "live" ? "Live" : "Buffered"}
          </span>
        )}
      </div>

      {error && (
        <div className="rounded-lg border border-red-500/20 bg-red-500/5 px-4 py-3 text-sm text-red-400">
          {error}
        </div>
      )}

      {/* Setup phase */}
      {phase === "setup" && (
        <div className="space-y-6">
          <div className="glass-card p-6 backdrop-blur-xl shadow-lg rounded-2xl">
            <h2 className="text-lg font-semibold text-theme">
              Paste the Job Description
            </h2>
            <p className="mt-1 text-xs text-muted-theme">
              We&apos;ll generate targeted interview questions based on the role.
            </p>
            <div className="mt-4">
              <JDPaste value={jdText} onChange={setJdText} />
            </div>
          </div>

          <div className="flex items-center gap-4">
            <button
              onClick={handleStartSession}
              disabled={jdText.trim().length < 50 || loading}
              className="px-8 py-3 text-sm font-bold transition-all rounded-xl cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
              style={{
                background: jdText.trim().length >= 50 && !loading ? "linear-gradient(135deg, #00F5A0, #00c47f)" : undefined,
                backgroundColor: jdText.trim().length < 50 || loading ? "rgba(255,255,255,0.05)" : undefined,
                color: jdText.trim().length >= 50 && !loading ? "#060914" : "#4B5670",
                boxShadow: jdText.trim().length >= 50 && !loading ? "0 4px 14px rgba(0,245,160,0.3)" : undefined,
              }}
            >
              {loading ? "Generating questions..." : "Start Mock Interview"}
            </button>
            <span className="text-xs text-muted-theme">
              5 questions &middot; ~15 min
            </span>
          </div>
        </div>
      )}

      {/* Active session */}
      {phase !== "setup" && phase !== "summary" && questions.length > 0 && (
        <div className="space-y-6">
          {/* Progress */}
          <SessionProgress
            results={sessionResults}
            totalScore={totalScore}
            maxTotalScore={maxTotalScore}
            sessionTime={sessionTime}
          />

          {/* Current question */}
          <QuestionCard
            question={questions[currentQ].text}
            category={questions[currentQ].category}
            difficulty={questions[currentQ].difficulty}
            questionNumber={currentQ + 1}
            totalQuestions={questions.length}
            isActive={phase === "question" || phase === "recording"}
          />

          {/* Voice wave + recording controls */}
          {phase !== "feedback" && (
            <div
              className="glass-card p-6 backdrop-blur-xl shadow-lg rounded-2xl border"
              style={{
                borderColor: isDark ? "rgba(255,255,255,0.08)" : "rgba(0,0,0,0.08)",
                backgroundColor: isDark ? "rgba(255,255,255,0.04)" : "rgba(255,255,255,0.6)"
              }}
            >
              <VoiceWave isRecording={isRecording} />

              <div className="mt-4 flex items-center justify-center gap-4">
                {phase === "question" && !isRecording && (
                  <button
                    onClick={handleStartRecording}
                    className="flex items-center gap-2 rounded-xl px-6 py-3 text-sm font-bold text-[#060914] cursor-pointer transition-all hover:scale-105"
                    style={{
                      background: "linear-gradient(135deg, #00F5A0, #00c47f)",
                      boxShadow: "0 4px 14px rgba(0,245,160,0.3)"
                    }}
                  >
                    <div className="h-3 w-3 rounded-full bg-red-600 animate-pulse" />
                    Start Recording
                  </button>
                )}

                {phase === "recording" && (
                  <button
                    onClick={handleStopRecording}
                    className="flex items-center gap-2 rounded-xl bg-red-500 px-6 py-3 text-sm font-bold text-white hover:bg-red-400 transition-all cursor-pointer hover:scale-105"
                  >
                    <div className="h-3 w-3 rounded-sm bg-white" />
                    Stop Recording
                  </button>
                )}
              </div>

              {/* Text answer */}
              <div className="mt-4">
                <textarea
                  value={answerText}
                  onChange={(e) => setAnswerText(e.target.value)}
                  placeholder="Type your answer here..."
                  className="h-24 w-full rounded-xl border p-3 text-sm resize-none outline-none font-mono transition-all"
                  style={{
                    backgroundColor: isDark ? "rgba(255,255,255,0.05)" : "rgba(0,0,0,0.03)",
                    borderColor: isDark ? "rgba(255,255,255,0.1)" : "rgba(0,0,0,0.1)",
                    color: isDark ? "#f0f4ff" : "#111827"
                  }}
                />
                <div className="mt-2 flex justify-end gap-3">
                  <button
                    onClick={handleSubmitAnswer}
                    disabled={!answerText.trim() || loading}
                    className="rounded-xl px-5 py-2 text-xs font-bold transition-all disabled:opacity-50 cursor-pointer"
                    style={{
                      background: answerText.trim() && !loading ? "linear-gradient(135deg, #00F5A0, #00c47f)" : undefined,
                      backgroundColor: !answerText.trim() || loading ? "rgba(255,255,255,0.05)" : undefined,
                      color: answerText.trim() && !loading ? "#060914" : "#4B5670",
                      boxShadow: answerText.trim() && !loading ? "0 4px 12px rgba(0,245,160,0.25)" : undefined
                    }}
                  >
                    {loading ? "Grading..." : "Submit Answer"}
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Feedback */}
          {phase === "feedback" && currentGrade && (
            <div className="space-y-4">
              <FeedbackPanel
                overallScore={currentGrade.overall_score}
                maxScore={currentGrade.max_score}
                dimensions={currentGrade.dimensions.map((d) => ({
                  name: d.name,
                  score: d.score,
                  maxScore: d.max_score,
                  feedback: d.feedback,
                }))}
                strengths={currentGrade.strengths}
                improvements={currentGrade.improvements}
                modelAnswer={currentGrade.model_answer}
              />

              <button
                onClick={handleNextQuestion}
                disabled={loading}
                className="rounded-xl px-6 py-3 text-sm font-bold text-[#060914] cursor-pointer transition-all disabled:opacity-50"
                style={{
                  background: "linear-gradient(135deg, #00F5A0, #00c47f)",
                  boxShadow: "0 4px 14px rgba(0,245,160,0.3)"
                }}
              >
                {currentQ < questions.length - 1 ? "Next Question" : "Finish Session"}
              </button>
            </div>
          )}

          {/* Live streaming feedback (WebSocket mode) */}
          {phase === "feedback" && !currentGrade && streamText && (
            <div className="glass-card p-4 border border-cp-accent/20 bg-cp-accent/5 backdrop-blur-md rounded-2xl">
              <p className="mb-2 text-xs font-bold uppercase text-cp-accent">Live Feedback</p>
              <p className="whitespace-pre-wrap text-sm text-theme-secondary">{streamText}</p>
              {loading && (
                <span className="mt-2 inline-block h-4 w-1 animate-pulse bg-cp-accent" />
              )}
            </div>
          )}

          {/* No grade yet in feedback phase — show submit flow */}
          {phase === "feedback" && !currentGrade && (
            <div
              className="glass-card p-6 border rounded-2xl backdrop-blur-xl"
              style={{
                borderColor: isDark ? "rgba(255,255,255,0.08)" : "rgba(0,0,0,0.08)",
                backgroundColor: isDark ? "rgba(255,255,255,0.04)" : "rgba(255,255,255,0.6)"
              }}
            >
              <p className="mb-3 text-sm font-semibold text-theme">Type your answer to get feedback</p>
              <textarea
                value={answerText}
                onChange={(e) => setAnswerText(e.target.value)}
                placeholder="Type your answer here..."
                className="h-32 w-full rounded-xl border p-3 text-sm resize-none outline-none font-mono transition-all"
                style={{
                  backgroundColor: isDark ? "rgba(255,255,255,0.05)" : "rgba(0,0,0,0.03)",
                  borderColor: isDark ? "rgba(255,255,255,0.1)" : "rgba(0,0,0,0.1)",
                  color: isDark ? "#f0f4ff" : "#111827"
                }}
              />
              <div className="mt-3 flex justify-end gap-3">
                <button
                  onClick={handleSubmitAnswer}
                  disabled={!answerText.trim() || loading}
                  className="rounded-xl px-5 py-2 text-xs font-bold transition-all disabled:opacity-50 cursor-pointer"
                  style={{
                    background: answerText.trim() && !loading ? "linear-gradient(135deg, #00F5A0, #00c47f)" : undefined,
                    backgroundColor: !answerText.trim() || loading ? "rgba(255,255,255,0.05)" : undefined,
                    color: answerText.trim() && !loading ? "#060914" : "#4B5670",
                    boxShadow: answerText.trim() && !loading ? "0 4px 12px rgba(0,245,160,0.25)" : undefined
                  }}
                >
                  {loading ? "Grading..." : "Submit Answer"}
                </button>
                <button
                  onClick={handleNextQuestion}
                  className="rounded-xl border px-5 py-2 text-xs text-theme-secondary transition-all hover:text-cp-accent hover:border-cp-accent cursor-pointer"
                  style={{
                    borderColor: isDark ? "rgba(255,255,255,0.1)" : "rgba(0,0,0,0.1)"
                  }}
                >
                  Skip
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Summary phase */}
      {phase === "summary" && (
        <div className="space-y-6">
          <div
            className="glass-card p-6 border border-emerald-500/20 bg-emerald-500/5 backdrop-blur-md rounded-2xl text-center shadow-lg"
          >
            <p className="text-4xl font-bold text-emerald-400">
              {summary
                ? Math.round(summary.score_pct * 100)
                : Math.round((totalScore / maxTotalScore) * 100)}
              %
            </p>
            <p className="mt-2 text-lg font-semibold text-theme">
              Session Complete
              {summary?.grade_letter && (
                <span className="ml-2 text-cp-accent">({summary.grade_letter})</span>
              )}
            </p>
            <p className="mt-1 text-sm text-muted-theme">
              {questions.length} questions in{" "}
              {Math.floor(sessionTime / 60)}:{(sessionTime % 60)
                .toString()
                .padStart(2, "0")}
            </p>
          </div>

          <SessionProgress
            results={sessionResults.map((r) => ({ ...r, status: "completed" as const }))}
            totalScore={totalScore}
            maxTotalScore={maxTotalScore}
            sessionTime={sessionTime}
          />

          {summary && summary.all_improvements.length > 0 && (
            <div
              className="glass-card p-4 border rounded-2xl shadow-md backdrop-blur-sm"
              style={{
                borderColor: isDark ? "rgba(255,255,255,0.08)" : "rgba(0,0,0,0.08)",
                backgroundColor: isDark ? "rgba(255,255,255,0.02)" : "rgba(255,255,255,0.55)"
              }}
            >
              <p className="text-sm font-semibold text-cp-accent">Key Improvements</p>
              <ul className="mt-2 space-y-1">
                {summary.all_improvements.slice(0, 5).map((item, i) => (
                  <li key={i} className="text-xs text-theme-secondary">• {item}</li>
                ))}
              </ul>
            </div>
          )}

          <div className="flex gap-4">
            <button
              onClick={() => {
                setPhase("setup");
                setCurrentQ(0);
                setSessionTime(0);
                setQuestions([]);
                setGrades([]);
                setCurrentGrade(null);
                setSummary(null);
                setSessionId(null);
              }}
              className="rounded-xl px-6 py-3 text-sm font-bold text-[#060914] cursor-pointer transition-all hover:scale-105"
              style={{
                background: "linear-gradient(135deg, #00F5A0, #00c47f)",
                boxShadow: "0 4px 14px rgba(0,245,160,0.3)"
              }}
            >
              New Session
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
