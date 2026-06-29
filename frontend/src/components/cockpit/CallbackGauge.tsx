import { useEffect, useRef } from "react";

interface CallbackGaugeProps {
  value: number;
  confidenceLow: number;
  confidenceHigh: number;
}

export default function CallbackGauge({ value, confidenceLow, confidenceHigh }: CallbackGaugeProps) {
  const progressRef = useRef<SVGPathElement>(null);
  const ghostRef = useRef<SVGPathElement>(null);
  const numberRef = useRef<HTMLSpanElement>(null);

  const cx = 90;
  const cy = 90;
  const r = 70;
  const strokeWidth = 6;

  function polarToXY(angleDeg: number) {
    const rad = ((angleDeg - 180) * Math.PI) / 180;
    return {
      x: cx + r * Math.cos(rad),
      y: cy + r * Math.sin(rad),
    };
  }

  function arc(startDeg: number, endDeg: number) {
    const start = polarToXY(startDeg);
    const end = polarToXY(endDeg);
    const largeArc = endDeg - startDeg > 180 ? 1 : 0;
    return `M ${start.x} ${start.y} A ${r} ${r} 0 ${largeArc} 1 ${end.x} ${end.y}`;
  }

  const totalArc = 180;
  const filledDeg = (value / 100) * totalArc;
  const lowDeg = (confidenceLow / 100) * totalArc;
  const highDeg = (confidenceHigh / 100) * totalArc;

  const trackPath = arc(0, totalArc);
  const filledPath = filledDeg > 0 ? arc(0, filledDeg) : "";
  const ghostPath = highDeg > lowDeg ? arc(lowDeg, highDeg) : "";

  const arcLen = Math.PI * r;
  const filledLen = (filledDeg / totalArc) * arcLen;

  useEffect(() => {
    const el = progressRef.current;
    const numEl = numberRef.current;
    if (!el) return;

    el.style.strokeDasharray = `${arcLen}`;
    el.style.strokeDashoffset = `${arcLen}`;

    let start: number | null = null;
    const duration = 800;

    function step(ts: number) {
      if (start === null) start = ts;
      const elapsed = ts - start;
      const progress = Math.min(elapsed / duration, 1);
      const ease = 1 - Math.pow(1 - progress, 3);

      el!.style.strokeDashoffset = `${arcLen - ease * filledLen}`;

      if (numEl) {
        numEl.textContent = `${Math.round(ease * value)}%`;
      }

      if (progress < 1) requestAnimationFrame(step);
    }

    requestAnimationFrame(step);
  }, [value, filledLen, arcLen]);

  return (
    <div id="cockpit-callback-gauge" className="flex flex-col items-center">
      <svg width="180" height="100" viewBox="0 0 180 100">
        {/* Track */}
        <path
          d={trackPath}
          fill="none"
          stroke="#1E2740"
          strokeWidth={strokeWidth}
          strokeLinecap="round"
        />
        {/* Ghost confidence band */}
        {ghostPath && (
          <path
            ref={ghostRef}
            d={ghostPath}
            fill="none"
            stroke="rgba(0,245,160,0.2)"
            strokeWidth={strokeWidth}
            strokeLinecap="round"
          />
        )}
        {/* Filled arc */}
        {filledPath && (
          <path
            ref={progressRef}
            d={filledPath}
            fill="none"
            stroke="#00F5A0"
            strokeWidth={strokeWidth}
            strokeLinecap="round"
          />
        )}
      </svg>
      <div className="-mt-8 flex flex-col items-center">
        <span
          ref={numberRef}
          className="font-mono text-3xl font-medium text-cp-text"
          style={{ fontWeight: 500 }}
        >
          0%
        </span>
        <span className="font-mono text-[10px] text-cp-text-mute mt-1">
          callback probability
        </span>
      </div>
    </div>
  );
}
