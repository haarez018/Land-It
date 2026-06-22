/**
 * Zustand global store — resume + JD state shared across Tailor, Pitcher, Coach.
 *
 * Upload a resume once on any page; it persists when navigating to another.
 * Same for the active JD text.
 */

import { create } from "zustand";
import api from "../lib/api";
import type {
  Resume,
  ATSScoreResult,
  TailorResult,
  DualScoreResult,
  StandoutScoreResult,
  ABTestResult,
} from "../lib/types";

interface AppState {
  /* ── Resume ──────────────────────────────────────── */
  resume: Resume | null;
  resumeFileName: string;
  resumeLoading: boolean;
  resumeError: string | null;

  uploadResume: (file: File) => Promise<Resume | null>;
  clearResume: () => void;

  /* ── JD ──────────────────────────────────────────── */
  jdText: string;
  setJdText: (text: string) => void;

  /* ── ATS / Tailor results (Tailor page) ──────────── */
  atsScore: ATSScoreResult | null;
  standoutScore: StandoutScoreResult | null;
  dualScore: DualScoreResult | null;
  tailorResult: TailorResult | null;
  tailorLoading: boolean;
  tailorError: string | null;

  scoreResume: (resumeId: string, jdText: string) => Promise<ATSScoreResult | null>;
  scoreDual: (resumeId: string, jdText: string) => Promise<DualScoreResult | null>;
  tailorResume: (resumeId: string, jdText: string) => Promise<TailorResult | null>;
  clearTailorResults: () => void;

  /* ── A/B Testing ─────────────────────────────────── */
  abTestResult: ABTestResult | null;
  abTestLoading: boolean;
  runABTest: (resumeId: string, resumeBText: string, jdText: string) => Promise<ABTestResult | null>;
  clearABTest: () => void;

  /* ── Cover letter (Pitcher page) ─────────────────── */
  writingSamples: string[];
  setWritingSamples: (samples: string[]) => void;

  /* ── Misc ────────────────────────────────────────── */
  lastActivity: number;
  touch: () => void;
}

export const useAppStore = create<AppState>((set) => ({
  /* ── Resume ──────────────────────────────────────── */
  resume: null,
  resumeFileName: "",
  resumeLoading: false,
  resumeError: null,

  uploadResume: async (file: File) => {
    set({ resumeLoading: true, resumeError: null });
    try {
      const form = new FormData();
      form.append("file", file);
      const { data } = await api.post<Resume>("/resume/upload", form, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      set({
        resume: data,
        resumeFileName: file.name,
        resumeLoading: false,
        lastActivity: Date.now(),
      });
      return data;
    } catch (e: any) {
      const msg = e.response?.data?.detail || "Failed to upload resume";
      set({ resumeError: msg, resumeLoading: false });
      return null;
    }
  },

  clearResume: () =>
    set({
      resume: null,
      resumeFileName: "",
      atsScore: null,
      standoutScore: null,
      dualScore: null,
      tailorResult: null,
    }),

  /* ── JD ──────────────────────────────────────────── */
  jdText: "",
  setJdText: (text: string) => set({ jdText: text }),

  /* ── ATS / Tailor ────────────────────────────────── */
  atsScore: null,
  standoutScore: null,
  dualScore: null,
  tailorResult: null,
  tailorLoading: false,
  tailorError: null,

  scoreResume: async (resumeId: string, jdText: string) => {
    set({ tailorLoading: true, tailorError: null });
    try {
      const { data } = await api.post<ATSScoreResult>(
        `/resume/${resumeId}/score`,
        { jd_text: jdText },
      );
      set({ atsScore: data, tailorLoading: false, lastActivity: Date.now() });
      return data;
    } catch (e: any) {
      const msg = e.response?.data?.detail || "Failed to score resume";
      set({ tailorError: msg, tailorLoading: false });
      return null;
    }
  },

  scoreDual: async (resumeId: string, jdText: string) => {
    set({ tailorLoading: true, tailorError: null });
    try {
      const { data } = await api.post<DualScoreResult>(
        `/resume/${resumeId}/score/dual`,
        { jd_text: jdText },
      );
      set({
        dualScore: data,
        atsScore: data.ats_score,
        standoutScore: data.standout_score,
        tailorLoading: false,
        lastActivity: Date.now(),
      });
      return data;
    } catch (e: any) {
      const msg = e.response?.data?.detail || "Failed to score resume";
      set({ tailorError: msg, tailorLoading: false });
      return null;
    }
  },

  tailorResume: async (resumeId: string, jdText: string) => {
    set({ tailorLoading: true, tailorError: null });
    try {
      const { data } = await api.post<TailorResult>(
        `/resume/${resumeId}/tailor`,
        { jd_text: jdText },
      );
      set({
        tailorResult: data,
        atsScore: {
          total_score: data.score_before,
          letter_grade: data.letter_grade_before,
        } as ATSScoreResult,
        tailorLoading: false,
        lastActivity: Date.now(),
      });
      return data;
    } catch (e: any) {
      const msg = e.response?.data?.detail || "Failed to tailor resume";
      set({ tailorError: msg, tailorLoading: false });
      return null;
    }
  },

  clearTailorResults: () =>
    set({ atsScore: null, standoutScore: null, dualScore: null, tailorResult: null }),

  /* ── A/B Testing ────────────────────────────────── */
  abTestResult: null,
  abTestLoading: false,

  runABTest: async (resumeId: string, resumeBText: string, jdText: string) => {
    set({ abTestLoading: true });
    try {
      const { data } = await api.post<ABTestResult>(
        `/resume/${resumeId}/ab-test`,
        { resume_b_text: resumeBText, jd_text: jdText },
      );
      set({ abTestResult: data, abTestLoading: false, lastActivity: Date.now() });
      return data;
    } catch {
      set({ abTestLoading: false });
      return null;
    }
  },

  clearABTest: () => set({ abTestResult: null }),

  /* ── Cover letter ────────────────────────────────── */
  writingSamples: [],
  setWritingSamples: (samples: string[]) => set({ writingSamples: samples }),

  /* ── Misc ────────────────────────────────────────── */
  lastActivity: Date.now(),
  touch: () => set({ lastActivity: Date.now() }),
}));
