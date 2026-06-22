/** Radar chart showing all 14 scoring dimensions — before vs after rewrite.
 *  Uses recharts RadarChart for clean visualization. */

import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
  Legend,
} from "recharts";
import type { DimensionScore } from "../../lib/types";

interface Props {
  dimensions: DimensionScore[];
  afterDimensions?: DimensionScore[];
}

function shortenName(name: string): string {
  const map: Record<string, string> = {
    "Keyword Density & Coverage": "Keywords",
    "Skill Depth & Demonstration": "Skill Depth",
    "Tech Stack Alignment": "Tech Stack",
    "Experience Relevance": "Experience",
    "Quantified Impact": "Impact",
    "Action Verb Strength": "Verbs",
    "Section Ordering": "Ordering",
    "Bullet Point Quality": "Bullets",
    "ATS Parsability": "Parsability",
    "Seniority Calibration": "Seniority",
    "Domain & Industry Knowledge": "Domain",
    "Education Relevance": "Education",
    "Semantic Similarity": "Similarity",
    "Narrative Voice & Consistency": "Voice",
  };
  return map[name] || name.split(" ")[0];
}

export default function WeightageRadar({ dimensions, afterDimensions }: Props) {
  if (!dimensions.length) return null;

  const data = dimensions.map((dim, i) => {
    const entry: Record<string, string | number> = {
      name: shortenName(dim.dimension_name),
      before: dim.raw_score,
    };
    if (afterDimensions?.[i]) {
      entry.after = afterDimensions[i].raw_score;
    }
    return entry;
  });

  return (
    <div className="rounded-xl border border-navy-700 bg-navy-800 p-4">
      <h3 className="mb-2 text-lg font-semibold text-white">Dimension Radar</h3>
      <ResponsiveContainer width="100%" height={350}>
        <RadarChart data={data} cx="50%" cy="50%" outerRadius="70%">
          <PolarGrid stroke="#334155" />
          <PolarAngleAxis
            dataKey="name"
            tick={{ fill: "#94a3b8", fontSize: 10 }}
          />
          <PolarRadiusAxis
            angle={90}
            domain={[0, 100]}
            tick={{ fill: "#64748b", fontSize: 9 }}
          />
          <Radar
            name="Before"
            dataKey="before"
            stroke="#f59e0b"
            fill="#f59e0b"
            fillOpacity={0.2}
            strokeWidth={2}
          />
          {afterDimensions && (
            <Radar
              name="After"
              dataKey="after"
              stroke="#10b981"
              fill="#10b981"
              fillOpacity={0.15}
              strokeWidth={2}
            />
          )}
          <Legend
            wrapperStyle={{ color: "#94a3b8", fontSize: 12 }}
          />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}
