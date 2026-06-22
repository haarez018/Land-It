/** Hook for fetching and managing ATS score + tailor state. */

import { useCallback, useState } from "react";
import api from "../lib/api";
import type { ATSScoreResult, Resume, TailorResult } from "../lib/types";

export function useATSScore() {
  const [score, setScore] = useState<ATSScoreResult | null>(null);
  const [tailorResult, setTailorResult] = useState<TailorResult | null>(null);
  const [resume, setResume] = useState<Resume | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const uploadResume = useCallback(async (file: File) => {
    setLoading(true);
    setError(null);
    try {
      const form = new FormData();
      form.append("file", file);
      const { data } = await api.post<Resume>("/resume/upload", form, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setResume(data);
      return data;
    } catch (e: any) {
      setError(e.response?.data?.detail || "Failed to upload resume");
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  const scoreResume = useCallback(
    async (resumeId: string, jdText: string) => {
      setLoading(true);
      setError(null);
      try {
        const { data } = await api.post<ATSScoreResult>(
          `/resume/${resumeId}/score`,
          { jd_text: jdText }
        );
        setScore(data);
        return data;
      } catch (e: any) {
        setError(e.response?.data?.detail || "Failed to score resume");
        return null;
      } finally {
        setLoading(false);
      }
    },
    []
  );

  const tailorResume = useCallback(
    async (resumeId: string, jdText: string) => {
      setLoading(true);
      setError(null);
      try {
        const { data } = await api.post<TailorResult>(
          `/resume/${resumeId}/tailor`,
          { jd_text: jdText }
        );
        setTailorResult(data);
        // Also update the score to the "before" score
        setScore({
          total_score: data.score_before,
          letter_grade: data.letter_grade_before,
        } as ATSScoreResult);
        return data;
      } catch (e: any) {
        setError(e.response?.data?.detail || "Failed to tailor resume");
        return null;
      } finally {
        setLoading(false);
      }
    },
    []
  );

  return {
    score,
    tailorResult,
    resume,
    loading,
    error,
    uploadResume,
    scoreResume,
    tailorResume,
    setScore,
    setResume,
  };
}
