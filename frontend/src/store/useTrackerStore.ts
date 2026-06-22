/**
 * Zustand store — application pipeline / Kanban state.
 *
 * Shared between Tracker (Kanban board) and Dashboard (stats).
 */

import { create } from "zustand";
import api from "../lib/api";
import type { ApplicationStatus } from "../lib/types";

export interface TrackedApp {
  id: string;
  job_id: string;
  status: ApplicationStatus;
  fit_score: number;
  ats_score_before: number | null;
  ats_score_after: number | null;
  priority: number;
  notes: string;
}

export interface DashboardStats {
  applications_this_week: number;
  interviews_scheduled: number;
  avg_ats_score: number;
  cover_letters_generated: number;
  coaching_sessions: number;
  total_applications: number;
}

interface TrackerState {
  /* ── Data ───────────────────────────────────────── */
  apps: TrackedApp[];
  stats: DashboardStats | null;
  loading: boolean;
  error: string | null;

  /* ── Actions ────────────────────────────────────── */
  fetchApps: () => Promise<void>;
  fetchStats: () => Promise<void>;
  updateStatus: (appId: string, newStatus: ApplicationStatus) => Promise<void>;
  /** Optimistic: move a card locally before the API call confirms */
  moveOptimistic: (appId: string, newStatus: ApplicationStatus) => void;
}

export const useTrackerStore = create<TrackerState>((set, get) => ({
  apps: [],
  stats: null,
  loading: false,
  error: null,

  fetchApps: async () => {
    set({ loading: true, error: null });
    try {
      const { data } = await api.get<TrackedApp[]>("/applications/");
      set({ apps: data, loading: false });
    } catch {
      set({ loading: false });
    }
  },

  fetchStats: async () => {
    try {
      const { data } = await api.get<DashboardStats>("/planner/stats");
      set({ stats: data });
    } catch {
      // silent
    }
  },

  moveOptimistic: (appId: string, newStatus: ApplicationStatus) => {
    set((state) => ({
      apps: state.apps.map((a) =>
        a.id === appId ? { ...a, status: newStatus } : a,
      ),
    }));
  },

  updateStatus: async (appId: string, newStatus: ApplicationStatus) => {
    // Optimistic update first
    get().moveOptimistic(appId, newStatus);
    try {
      await api.patch(`/applications/${appId}`, { status: newStatus });
    } catch (e: any) {
      // Revert by re-fetching
      await get().fetchApps();
      set({ error: e.response?.data?.detail || "Failed to update status" });
    }
  },
}));
