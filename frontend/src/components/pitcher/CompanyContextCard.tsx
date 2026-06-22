/** Visual display of researched company context. */

import type { CompanyContext } from "../../lib/types";

interface Props {
  context: CompanyContext;
}

export default function CompanyContextCard({ context }: Props) {
  return (
    <div className="rounded-xl border border-navy-700 bg-navy-800 p-5">
      <div className="flex items-center gap-2">
        <svg className="h-5 w-5 text-amber-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <rect x="2" y="7" width="20" height="14" rx="2" ry="2" />
          <path d="M16 21V5a2 2 0 00-2-2h-4a2 2 0 00-2 2v16" />
        </svg>
        <h3 className="text-lg font-semibold text-white">
          {context.company_name || "Company"} Intel
        </h3>
      </div>

      <div className="mt-4 space-y-3">
        {/* Mission */}
        {context.mission && (
          <div>
            <p className="text-xs uppercase text-navy-500">Mission</p>
            <p className="mt-1 text-sm text-navy-300">{context.mission}</p>
          </div>
        )}

        {/* Industry & Tone */}
        <div className="grid grid-cols-2 gap-4">
          {context.industry && (
            <div>
              <p className="text-xs uppercase text-navy-500">Industry</p>
              <p className="mt-1 text-sm text-navy-200">{context.industry}</p>
            </div>
          )}
          {context.tone && (
            <div>
              <p className="text-xs uppercase text-navy-500">Company Tone</p>
              <p className="mt-1 text-sm text-navy-200">
                {context.tone.replace(/_/g, " ")}
              </p>
            </div>
          )}
        </div>

        {/* Values */}
        {context.values.length > 0 && (
          <div>
            <p className="text-xs uppercase text-navy-500">Values</p>
            <div className="mt-2 flex flex-wrap gap-2">
              {context.values.map((val, i) => (
                <span
                  key={i}
                  className="rounded-full bg-blue-500/10 px-3 py-1 text-xs text-blue-400"
                >
                  {val}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Products */}
        {context.products.length > 0 && (
          <div>
            <p className="text-xs uppercase text-navy-500">Products</p>
            <div className="mt-2 flex flex-wrap gap-2">
              {context.products.map((product, i) => (
                <span
                  key={i}
                  className="rounded-full bg-emerald-500/10 px-3 py-1 text-xs text-emerald-400"
                >
                  {product}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Key Talking Points */}
        {context.key_talking_points.length > 0 && (
          <div>
            <p className="text-xs uppercase text-navy-500">Key Talking Points</p>
            <ul className="mt-2 space-y-1">
              {context.key_talking_points.map((point, i) => (
                <li key={i} className="flex items-start gap-2 text-xs text-navy-300">
                  <span className="mt-0.5 text-amber-500">&#x2022;</span>
                  {point}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Culture Signals */}
        {context.culture_signals.length > 0 && (
          <div>
            <p className="text-xs uppercase text-navy-500">Culture Signals</p>
            <div className="mt-2 flex flex-wrap gap-2">
              {context.culture_signals.map((signal, i) => (
                <span
                  key={i}
                  className="rounded-full bg-purple-500/10 px-3 py-1 text-xs text-purple-400"
                >
                  {signal}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
