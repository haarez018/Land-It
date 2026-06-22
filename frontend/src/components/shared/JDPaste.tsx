/** Job description paste textarea with parse trigger. */

interface Props {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
}

export default function JDPaste({ value, onChange, placeholder }: Props) {
  return (
    <textarea
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="h-32 w-full rounded-lg border p-3 text-sm resize-none transition-colors input-theme focus:ring-1 focus:ring-[var(--accent)]"
      placeholder={placeholder || "Paste the job description here..."}
    />
  );
}
