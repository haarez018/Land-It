/**
 * Zustand store — job queue and parsed JDs.
 *
 * Shared between Jobs page, Tracker (Kanban), and Dashboard stats.
 */

import { create } from "zustand";
import api from "../lib/api";
import type { JobDescription } from "../lib/types";

interface JobState {
  /* ── Data ─────────────────────────────────────────── */
  jobs: JobDescription[];
  loading: boolean;
  error: string | null;

  /* ── Actions ──────────────────────────────────────── */
  fetchJobs: () => Promise<void>;
  parseJD: (jdText: string) => Promise<JobDescription | null>;
  dismissJob: (jobId: string) => Promise<void>;
  getJob: (jobId: string) => JobDescription | undefined;
}

export const useJobStore = create<JobState>((set, get) => ({
  jobs: [],
  loading: false,
  error: null,

  fetchJobs: async () => {
    set({ loading: true, error: null });
    try {
      const { data } = await api.get<JobDescription[]>("/jobs/queue");
      set({ jobs: data, loading: false });
    } catch {
      // Expected to fail when no jobs exist yet
      set({ loading: false });
    }
  },

  parseJD: async (jdText: string) => {
    set({ error: null });
    try {
      const { data } = await api.post<JobDescription>("/jobs/jd", {
        jd_text: jdText,
      });
      set((state) => ({ jobs: [data, ...state.jobs] }));
      return data;
    } catch (e: any) {
      const msg = e.response?.data?.detail || "Failed to parse JD";
      set({ error: msg });
      return null;
    }
  },

  dismissJob: async (jobId: string) => {
    try {
      await api.post(`/jobs/${jobId}/dismiss`);
      set((state) => ({ jobs: state.jobs.filter((j) => j.id !== jobId) }));
    } catch {
      // silent
    }
  },

  getJob: (jobId: string) => get().jobs.find((j) => j.id === jobId),
}));
