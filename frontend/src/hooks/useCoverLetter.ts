/** Hook for generating cover letters via the Pitcher agent. */

import { useCallback, useState } from "react";
import api from "../lib/api";
import type {
  CoverLetter,
  VoiceProfile,
  CompanyContext,
} from "../lib/types";

export interface PitcherResult {
  cover_letter: CoverLetter;
  voice_profile: VoiceProfile;
  company_context: CompanyContext;
  alternative_openings: string[];
}

export function useCoverLetter() {
  const [result, setResult] = useState<PitcherResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const generate = useCallback(
    async (resumeId: string, jdText: string, writingSamples: string[]) => {
      setLoading(true);
      setError(null);
      try {
        const { data } = await api.post<PitcherResult>("/pitcher/generate", {
          resume_id: resumeId,
          jd_text: jdText,
          writing_samples: writingSamples,
        });
        setResult(data);
        return data;
      } catch (e: any) {
        setError(
          e.response?.data?.detail || "Failed to generate cover letter"
        );
        return null;
      } finally {
        setLoading(false);
      }
    },
    []
  );

  const analyzeVoice = useCallback(async (samples: string[]) => {
    setLoading(true);
    setError(null);
    try {
      const { data } = await api.post<VoiceProfile>(
        "/pitcher/voice-analyze",
        samples
      );
      return data;
    } catch (e: any) {
      setError(e.response?.data?.detail || "Failed to analyze voice");
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  const reset = useCallback(() => {
    setResult(null);
    setError(null);
  }, []);

  return {
    result,
    loading,
    error,
    generate,
    analyzeVoice,
    reset,
  };
}
