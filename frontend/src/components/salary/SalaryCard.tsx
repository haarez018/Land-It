/**
 * SalaryCard — salary range visualization with premium/discount factors,
 * negotiation leverage from Standout spikes, and talking points.
 */

interface SalaryEstimateData {
  role_type: string;
  seniority: string;
  location: string;
  company: string;
  estimated_range: [number, number];
  estimated_midpoint: number;
  user_position_in_range: "below_mid" | "at_mid" | "above_mid";
  user_estimated_value: number;
  premium_factors: string[];
  discount_factors: string[];
  negotiation_leverage: string[];
  negotiation_talking_points: string[];
  confidence: "high" | "medium" | "low";
  confidence_reason: string;
}

interface Props {
  estimate: SalaryEstimateData;
}

function formatK(n: number): string {
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(1)}M`;
  return `$${Math.round(n / 1000)}K`;
}

const confidenceColors: Record<string, string> = {
  high: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
  medium: "bg-amber-500/15 text-amber-400 border-amber-500/30",
  low: "bg-red-500/15 text-red-400 border-red-500/30",
};

export default function SalaryCard({ estimate }: Props) {
  const [low, high] = estimate.estimated_range;
  const mid = estimate.estimated_midpoint;
  const userVal = estimate.user_estimated_value;
  const range = high - low;

  // User position as percentage across the bar
  const userPct = range > 0 ? Math.min(100, Math.max(0, ((userVal - low) / range) * 100)) : 50;

  return (
    <div className="space-y-5">
      {/* Range bar */}
      <div className="rounded-xl border border-navy-700 bg-navy-800/60 p-6">
        <div className="flex items-center justify-between">
          <p className="text-xs font-semibold uppercase tracking-widest text-navy-400">
            Estimated Salary Range
          </p>
          <span
            className={`rounded-full border px-2 py-0.5 text-[10px] font-bold ${
              confidenceColors[estimate.confidence]
            }`}
          >
            {estimate.confidence} confidence
          </span>
        </div>

        {/* Visual range bar */}
        <div className="relative mt-6 h-4 w-full rounded-full bg-navy-700">
          {/* Full range fill */}
          <div className="absolute inset-0 rounded-full bg-gradient-to-r from-navy-600 via-amber-500/30 to-navy-600" />

          {/* Midpoint marker */}
          <div
            className="absolute top-1/2 h-6 w-0.5 -translate-y-1/2 bg-navy-400"
            style={{ left: "50%" }}
          />

          {/* User marker */}
          <div
            className="absolute top-1/2 -translate-y-1/2"
            style={{ left: `${userPct}%` }}
          >
            <div className="flex -translate-x-1/2 flex-col items-center">
              <div className="h-6 w-3 rounded-full bg-amber-400 shadow-lg shadow-amber-400/30" />
            </div>
          </div>
        </div>

        {/* Labels */}
        <div className="mt-2 flex items-center justify-between text-sm">
          <span className="text-navy-400">{formatK(low)}</span>
          <div className="text-center">
            <span className="text-xs text-navy-500">Mid: </span>
            <span className="font-medium text-navy-300">{formatK(mid)}</span>
          </div>
          <span className="text-navy-400">{formatK(high)}</span>
        </div>

        {/* User value callout */}
        <div className="mt-4 text-center">
          <p className="text-2xl font-black text-amber-400">{formatK(userVal)}</p>
          <p className="text-xs text-navy-400">
            Your estimated market value (
            {estimate.user_position_in_range === "above_mid"
              ? "above midpoint"
              : estimate.user_position_in_range === "below_mid"
                ? "below midpoint"
                : "at midpoint"}
            )
          </p>
        </div>

        <p className="mt-2 text-center text-[10px] text-navy-500">
          {estimate.confidence_reason}
        </p>
      </div>

      {/* Premium / Discount factors */}
      <div className="grid grid-cols-2 gap-4">
        {estimate.premium_factors.length > 0 && (
          <div className="rounded-lg border border-emerald-500/20 bg-emerald-500/5 p-4">
            <p className="text-xs font-semibold uppercase text-emerald-400">
              Premium Factors
            </p>
            <ul className="mt-2 space-y-1.5">
              {estimate.premium_factors.map((f, i) => (
                <li key={i} className="flex items-start gap-2 text-xs text-navy-200">
                  <span className="mt-0.5 text-emerald-400">+</span> {f}
                </li>
              ))}
            </ul>
          </div>
        )}

        {estimate.discount_factors.length > 0 && (
          <div className="rounded-lg border border-amber-500/20 bg-amber-500/5 p-4">
            <p className="text-xs font-semibold uppercase text-amber-400">
              Discount Factors
            </p>
            <ul className="mt-2 space-y-1.5">
              {estimate.discount_factors.map((f, i) => (
                <li key={i} className="flex items-start gap-2 text-xs text-navy-200">
                  <span className="mt-0.5 text-amber-400">-</span> {f}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {/* Negotiation section */}
      {(estimate.negotiation_leverage.length > 0 ||
        estimate.negotiation_talking_points.length > 0) && (
        <div className="rounded-xl border border-navy-700 bg-navy-800/40 p-5">
          <h3 className="text-sm font-semibold text-white">
            Negotiation Intel
          </h3>

          {estimate.negotiation_leverage.length > 0 && (
            <div className="mt-3">
              <p className="text-[10px] font-bold uppercase tracking-wider text-amber-400">
                Your Leverage
              </p>
              <ul className="mt-1 space-y-1">
                {estimate.negotiation_leverage.map((l, i) => (
                  <li key={i} className="flex items-start gap-2 text-xs text-navy-200">
                    <span className="mt-0.5 text-amber-400">&#9733;</span> {l}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {estimate.negotiation_talking_points.length > 0 && (
            <div className="mt-3">
              <p className="text-[10px] font-bold uppercase tracking-wider text-navy-400">
                Talking Points
              </p>
              <ul className="mt-1 space-y-1">
                {estimate.negotiation_talking_points.map((t, i) => (
                  <li key={i} className="text-xs italic text-navy-300">
                    {t}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
