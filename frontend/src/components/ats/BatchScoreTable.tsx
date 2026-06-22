import { useState } from "react";

interface BatchEntry {
  jd_id: string;
  jd_title: string;
  jd_company: string;
  ats_score: number;
  standout_score: number;
  combined_score: number;
  callback_probability: number;
  tier: string;
  top_gap: string;
  company_profile_used: string;
}

interface BatchResult {
  resume_id: string;
  entries: BatchEntry[];
  best_fit?: BatchEntry;
  worst_fit?: BatchEntry;
  highest_callback?: BatchEntry;
  avg_combined_score: number;
  avg_callback_probability: number;
  common_gaps: string[];
  strongest_dimension_overall: string;
  weakest_dimension_overall: string;
  recommendation: string;
}

interface Props {
  result: BatchResult;
}

type SortKey = "jd_company" | "ats_score" | "standout_score" | "combined_score" | "callback_probability" | "tier";

const TIER_COLORS: Record<string, string> = {
  Standout: "text-purple-400 bg-purple-500/10",
  Strong: "text-emerald-400 bg-emerald-500/10",
  Solid: "text-blue-400 bg-blue-500/10",
  "Needs Work": "text-amber-400 bg-amber-500/10",
  Weak: "text-red-400 bg-red-500/10",
};

export default function BatchScoreTable({ result }: Props) {
  const [sortKey, setSortKey] = useState<SortKey>("combined_score");
  const [desc, setDesc] = useState(true);

  const toggle = (key: SortKey) => {
    if (sortKey === key) setDesc(!desc);
    else { setSortKey(key); setDesc(true); }
  };

  const sorted = [...result.entries].sort((a, b) => {
    const av = a[sortKey] ?? 0;
    const bv = b[sortKey] ?? 0;
    if (typeof av === "string") return desc ? String(bv).localeCompare(String(av)) : String(av).localeCompare(String(bv));
    return desc ? (bv as number) - (av as number) : (av as number) - (bv as number);
  });

  const isBest = (e: BatchEntry) => e.jd_id === result.best_fit?.jd_id;
  const isWorst = (e: BatchEntry) => e.jd_id === result.worst_fit?.jd_id;

  const hdr = (label: string, key: SortKey) => (
    <th
      className="cursor-pointer px-3 py-2 text-left text-xs font-semibold uppercase text-navy-400 hover:text-white"
      onClick={() => toggle(key)}
    >
      {label} {sortKey === key ? (desc ? "↓" : "↑") : ""}
    </th>
  );

  return (
    <div className="space-y-4 rounded-xl border border-navy-700 bg-navy-800 p-6">
      <h3 className="text-lg font-semibold text-white">Batch Score Results</h3>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-navy-600">
              {hdr("Company", "jd_company")}
              <th className="px-3 py-2 text-left text-xs font-semibold uppercase text-navy-400">Role</th>
              {hdr("ATS", "ats_score")}
              {hdr("Standout", "standout_score")}
              {hdr("Combined", "combined_score")}
              {hdr("Callback %", "callback_probability")}
              {hdr("Tier", "tier")}
              <th className="px-3 py-2 text-left text-xs font-semibold uppercase text-navy-400">Top Gap</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((e) => (
              <tr
                key={e.jd_id}
                className={`border-b border-navy-700/50 ${
                  isBest(e) ? "bg-emerald-500/5" : isWorst(e) ? "bg-amber-500/5" : ""
                }`}
              >
                <td className="px-3 py-2 font-medium text-white">{e.jd_company || "—"}</td>
                <td className="px-3 py-2 text-navy-300">{e.jd_title || "—"}</td>
                <td className="px-3 py-2 text-navy-200">{e.ats_score.toFixed(0)}</td>
                <td className="px-3 py-2 text-navy-200">{e.standout_score.toFixed(0)}</td>
                <td className="px-3 py-2 font-bold text-white">{e.combined_score.toFixed(0)}</td>
                <td className="px-3 py-2 text-navy-200">{(e.callback_probability * 100).toFixed(0)}%</td>
                <td className="px-3 py-2">
                  <span className={`rounded-full px-2 py-0.5 text-xs font-bold ${TIER_COLORS[e.tier] ?? ""}`}>
                    {e.tier}
                  </span>
                </td>
                <td className="px-3 py-2 text-xs text-navy-400">{e.top_gap}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Summary */}
      <div className="grid grid-cols-2 gap-4 pt-2 text-sm">
        {result.common_gaps.length > 0 && (
          <div className="rounded-lg border border-amber-500/20 bg-amber-500/5 p-3">
            <p className="text-xs font-semibold uppercase text-amber-400">Common Gaps</p>
            <ul className="mt-1 space-y-1 text-navy-300">
              {result.common_gaps.slice(0, 3).map((g, i) => (
                <li key={i}>• {g}</li>
              ))}
            </ul>
          </div>
        )}
        {result.recommendation && (
          <div className="rounded-lg border border-navy-600 bg-navy-800/50 p-3">
            <p className="text-xs font-semibold uppercase text-navy-400">Recommendation</p>
            <p className="mt-1 text-navy-200">{result.recommendation}</p>
          </div>
        )}
      </div>
    </div>
  );
}
