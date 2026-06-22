/**
 * Zustand store for onboarding wizard state.
 */

import { create } from "zustand";
import api from "../lib/api";
// Types are defined inline since the onboarding API returns custom shapes

interface OnboardingProfile {
  name: string;
  email: string;
  target_roles: string[];
  target_seniority: string;
  target_locations: string[];
  remote_preference: string;
  salary_min: number;
  salary_max: number;
  company_size_preference: string[];
  weekly_goal: number;
}

interface ResumeSummary {
  resume_id: string;
  name: string;
  total_yoe: number;
  seniority_level: string;
  primary_domain: string;
  skill_count: number;
  top_skills: string[];
  work_experience_count: number;
}

interface BaselineScore {
  ats_score: number;
  standout_score: number;
  combined_score: number;
  combined_grade: string;
  callback_probability: number | null;
  top_3_wins: string[];
  top_3_issues: string[];
  role_type: string;
  seniority: string;
  summary: string;
}

interface VoiceSummary {
  tone: string;
  formality_level: string;
  avg_sentence_length: number;
}

interface OnboardingState {
  currentStep: number;
  profile: Partial<OnboardingProfile>;
  resumeSummary: ResumeSummary | null;
  baselineScore: BaselineScore | null;
  voiceSummary: VoiceSummary | null;
  isComplete: boolean;
  loading: boolean;
  error: string | null;

  goToStep: (step: number) => void;
  submitProfile: (data: OnboardingProfile) => Promise<boolean>;
  uploadResume: (file: File) => Promise<boolean>;
  uploadResumeText: (text: string) => Promise<boolean>;
  submitWritingSamples: (samples: string[]) => Promise<boolean>;
  runBaselineScore: (roleType?: string) => Promise<boolean>;
  completeOnboarding: () => Promise<boolean>;
  checkStatus: () => Promise<void>;
}

export const useOnboardingStore = create<OnboardingState>((set) => ({
  currentStep: 1,
  profile: {},
  resumeSummary: null,
  baselineScore: null,
  voiceSummary: null,
  isComplete: false,
  loading: false,
  error: null,

  goToStep: (step: number) => set({ currentStep: step }),

  uploadResume: async (file: File) => {
    set({ loading: true, error: null });
    try {
      const formData = new FormData();
      formData.append("file", file);
      const { data } = await api.post<ResumeSummary>("/onboarding/resume", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      set({ resumeSummary: data, loading: false });
      return true;
    } catch (e: any) {
      set({ error: e.response?.data?.detail || "Failed to parse resume", loading: false });
      return false;
    }
  },

  submitProfile: async (data: OnboardingProfile) => {
    set({ loading: true, error: null });
    try {
      await api.post("/onboarding/profile", data);
      set({ profile: data, loading: false, currentStep: 2 });
      return true;
    } catch (e: any) {
      set({ error: e.response?.data?.detail || "Failed to save profile", loading: false });
      return false;
    }
  },

  uploadResumeText: async (text: string) => {
    set({ loading: true, error: null });
    try {
      const { data } = await api.post<ResumeSummary>("/onboarding/resume-text", {
        resume_text: text,
      });
      set({ resumeSummary: data, loading: false });
      return true;
    } catch (e: any) {
      set({ error: e.response?.data?.detail || "Failed to parse resume", loading: false });
      return false;
    }
  },

  submitWritingSamples: async (samples: string[]) => {
    set({ loading: true, error: null });
    try {
      const { data } = await api.post("/onboarding/writing-samples", { samples });
      set({
        voiceSummary: data.voice_summary,
        loading: false,
        currentStep: 4,
      });
      return true;
    } catch (e: any) {
      set({ error: e.response?.data?.detail || "Failed to analyze samples", loading: false });
      return false;
    }
  },

  runBaselineScore: async (roleType?: string) => {
    set({ loading: true, error: null });
    try {
      const { data } = await api.post<BaselineScore>("/onboarding/baseline-score", {
        role_type: roleType || "",
      });
      set({ baselineScore: data, loading: false });
      return true;
    } catch (e: any) {
      set({ error: e.response?.data?.detail || "Failed to run baseline", loading: false });
      return false;
    }
  },

  completeOnboarding: async () => {
    set({ loading: true, error: null });
    try {
      await api.post("/onboarding/complete");
      set({ isComplete: true, loading: false, currentStep: 5 });
      return true;
    } catch (e: any) {
      set({ error: e.response?.data?.detail || "Failed to complete", loading: false });
      return false;
    }
  },

  checkStatus: async () => {
    try {
      const { data } = await api.get("/onboarding/status");
      set({ isComplete: data.completed });
    } catch {
      // Ignore — first load
    }
  },
}));
