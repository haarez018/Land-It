/**
 * CompanyProfileBadge — shows when scoring is calibrated for a known company.
 * Displays company name + tooltip with hiring philosophy and key weight changes.
 */

interface CompanyProfileInfo {
  id: string;
  name: string;
  hiring_philosophy: string;
  interview_signals: string[];
  red_flags: string[];
}

interface Props {
  profile: CompanyProfileInfo | null;
}

export default function CompanyProfileBadge({ profile }: Props) {
  if (!profile) return null;

  return (
    <div className="group relative inline-flex items-center gap-2 rounded-full border border-amber-500/30 bg-amber-500/10 px-3 py-1.5">
      <span className="h-2 w-2 rounded-full bg-amber-400" />
      <span className="text-xs font-medium text-amber-300">
        Calibrated for {profile.name}
      </span>

      {/* Tooltip on hover */}
      <div className="absolute left-0 top-full z-50 mt-2 hidden w-80 rounded-lg border border-navy-700 bg-navy-800 p-4 shadow-xl group-hover:block">
        <p className="text-sm font-semibold text-white">{profile.name}</p>
        <p className="mt-1 text-xs text-navy-300">{profile.hiring_philosophy}</p>

        <div className="mt-3">
          <p className="text-[10px] font-bold uppercase tracking-wider text-emerald-400">
            What they look for
          </p>
          <ul className="mt-1 space-y-0.5">
            {profile.interview_signals.map((s, i) => (
              <li key={i} className="flex items-start gap-1.5 text-xs text-navy-300">
                <span className="mt-0.5 text-emerald-400">+</span> {s}
              </li>
            ))}
          </ul>
        </div>

        <div className="mt-2">
          <p className="text-[10px] font-bold uppercase tracking-wider text-red-400">
            Red flags
          </p>
          <ul className="mt-1 space-y-0.5">
            {profile.red_flags.map((f, i) => (
              <li key={i} className="flex items-start gap-1.5 text-xs text-navy-300">
                <span className="mt-0.5 text-red-400">!</span> {f}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
