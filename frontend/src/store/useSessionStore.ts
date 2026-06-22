/**
 * Zustand store — interview coaching session state.
 *
 * Persists the active session so the user can navigate away and come back.
 */

import { create } from "zustand";
import api from "../lib/api";

/* ── API response shapes ─────────────────────────────────────────────── */

export interface CoachQuestion {
  id: string;
  text: string;
  category: string;
  difficulty: "easy" | "medium" | "hard";
  what_good_looks_like?: string;
  follow_ups?: string[];
  red_flags?: string[];
}

export interface AnswerFeedback {
  overall_score: number;
  max_score: number;
  dimensions: {
    name: string;
    score: number;
    maxScore: number;
    feedback: string;
  }[];
  strengths: string[];
  improvements: string[];
  red_flags: string[];
  model_answer?: string;
}

export interface SessionSummary {
  total_score: number;
  max_score: number;
  questions_answered: number;
  questions_skipped: number;
  duration_seconds: number;
  strongest_category: string;
  weakest_category: string;
  overall_feedback: string;
}

/* ── Store ────────────────────────────────────────────────────────────── */

interface SessionState {
  sessionId: string | null;
  questions: CoachQuestion[];
  currentIndex: number;
  answers: Map<string, AnswerFeedback>;
  summary: SessionSummary | null;
  loading: boolean;
  error: string | null;

  /* Actions */
  startSession: (jdText: string) => Promise<void>;
  fetchQuestions: () => Promise<void>;
  submitAnswer: (questionId: string, answerText: string) => Promise<AnswerFeedback | null>;
  skipQuestion: (questionId: string) => Promise<void>;
  nextQuestion: () => void;
  fetchSummary: () => Promise<SessionSummary | null>;
  resetSession: () => void;
}

export const useSessionStore = create<SessionState>((set, get) => ({
  sessionId: null,
  questions: [],
  currentIndex: 0,
  answers: new Map(),
  summary: null,
  loading: false,
  error: null,

  startSession: async (jdText: string) => {
    set({ loading: true, error: null });
    try {
      const { data } = await api.post<{ session_id: string; questions: CoachQuestion[] }>(
        "/coach/session/start",
        { jd_text: jdText },
      );
      set({
        sessionId: data.session_id,
        questions: data.questions,
        currentIndex: 0,
        answers: new Map(),
        summary: null,
        loading: false,
      });
    } catch (e: any) {
      set({
        error: e.response?.data?.detail || "Failed to start session",
        loading: false,
      });
    }
  },

  fetchQuestions: async () => {
    const { sessionId } = get();
    if (!sessionId) return;
    try {
      const { data } = await api.get<CoachQuestion[]>(
        `/coach/session/${sessionId}/questions`,
      );
      set({ questions: data });
    } catch {
      // silent
    }
  },

  submitAnswer: async (questionId: string, answerText: string) => {
    const { sessionId } = get();
    if (!sessionId) return null;
    set({ loading: true, error: null });
    try {
      const { data } = await api.post<AnswerFeedback>(
        `/coach/session/${sessionId}/answer`,
        { question_id: questionId, answer_text: answerText },
      );
      set((state) => {
        const next = new Map(state.answers);
        next.set(questionId, data);
        return { answers: next, loading: false };
      });
      return data;
    } catch (e: any) {
      set({
        error: e.response?.data?.detail || "Failed to submit answer",
        loading: false,
      });
      return null;
    }
  },

  skipQuestion: async (questionId: string) => {
    const { sessionId } = get();
    if (!sessionId) return;
    try {
      await api.post(`/coach/session/${sessionId}/skip`, {
        question_id: questionId,
      });
    } catch {
      // silent
    }
  },

  nextQuestion: () =>
    set((state) => ({
      currentIndex: Math.min(state.currentIndex + 1, state.questions.length - 1),
    })),

  fetchSummary: async () => {
    const { sessionId } = get();
    if (!sessionId) return null;
    set({ loading: true });
    try {
      const { data } = await api.get<SessionSummary>(
        `/coach/session/${sessionId}/summary`,
      );
      set({ summary: data, loading: false });
      return data;
    } catch (e: any) {
      set({
        error: e.response?.data?.detail || "Failed to fetch summary",
        loading: false,
      });
      return null;
    }
  },

  resetSession: () =>
    set({
      sessionId: null,
      questions: [],
      currentIndex: 0,
      answers: new Map(),
      summary: null,
      error: null,
    }),
}));
