import { useEffect, useRef, useState } from "react";

interface DimensionData {
  id: string;
  name: string;
  score: number;
  weight: number;
}

interface ResumeFingerprintProps {
  dimensionScores: DimensionData[];
  combinedScore: number;
  letterGrade: string;
}

const SCORE_COLORS = [
  { max: 30, color: "#EF4444" },
  { max: 50, color: "#F59E0B" },
  { max: 70, color: "#3B82F6" },
  { max: 85, color: "#10B981" },
  { max: 100, color: "#8B5CF6" },
];

function getColor(score: number): string {
  for (const { max, color } of SCORE_COLORS) {
    if (score <= max) return color;
  }
  return "#8B5CF6";
}

function polarToCartesian(cx: number, cy: number, r: number, angleDeg: number) {
  const rad = ((angleDeg - 90) * Math.PI) / 180;
  return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) };
}

function arcPath(
  cx: number,
  cy: number,
  innerR: number,
  outerR: number,
  startAngle: number,
  endAngle: number,
): string {
  const s1 = polarToCartesian(cx, cy, outerR, startAngle);
  const e1 = polarToCartesian(cx, cy, outerR, endAngle);
  const s2 = polarToCartesian(cx, cy, innerR, endAngle);
  const e2 = polarToCartesian(cx, cy, innerR, startAngle);
  const largeArc = endAngle - startAngle > 180 ? 1 : 0;
  return [
    `M ${s1.x} ${s1.y}`,
    `A ${outerR} ${outerR} 0 ${largeArc} 1 ${e1.x} ${e1.y}`,
    `L ${s2.x} ${s2.y}`,
    `A ${innerR} ${innerR} 0 ${largeArc} 0 ${e2.x} ${e2.y}`,
    "Z",
  ].join(" ");
}

export default function ResumeFingerprint({
  dimensionScores,
  combinedScore,
  letterGrade,
}: ResumeFingerprintProps) {
  const [progress, setProgress] = useState(0);
  const svgRef = useRef<SVGSVGElement>(null);
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null);

  useEffect(() => {
    let frame: number;
    const start = performance.now();
    const duration = 1200;
    const tick = (now: number) => {
      const t = Math.min((now - start) / duration, 1);
      const ease = 1 - Math.pow(1 - t, 3);
      setProgress(ease);
      if (t < 1) frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [dimensionScores]);

  const size = 400;
  const cx = size / 2;
  const cy = size / 2;
  const innerR = 70;
  const maxOuterR = 180;
  const gap = 1.5;

  const totalWeight = dimensionScores.reduce((s, d) => s + d.weight, 0) || 1;

  let angle = 0;
  const segments = dimensionScores.map((dim, i) => {
    const arcSpan = (dim.weight / totalWeight) * 360 - gap;
    const startAngle = angle + gap / 2;
    const endAngle = startAngle + Math.max(arcSpan, 2);
    angle += (dim.weight / totalWeight) * 360;

    const scoreRatio = Math.max(dim.score / 100, 0.15);
    const outerR = innerR + (maxOuterR - innerR) * scoreRatio * progress;
    const color = getColor(dim.score);

    const delayFactor = i / dimensionScores.length;
    const segProgress = Math.max(0, Math.min(1, (progress - delayFactor * 0.3) / 0.7));
    const animatedOuterR = innerR + (outerR - innerR) * segProgress;

    return {
      path: arcPath(cx, cy, innerR, animatedOuterR, startAngle, endAngle),
      color,
      opacity: 0.3 + segProgress * 0.7,
      dim,
      midAngle: (startAngle + endAngle) / 2,
    };
  });

  const exportPng = () => {
    if (!svgRef.current) return;
    const svg = svgRef.current;
    const data = new XMLSerializer().serializeToString(svg);
    const blob = new Blob([data], { type: "image/svg+xml;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const canvas = document.createElement("canvas");
    canvas.width = size * 2;
    canvas.height = size * 2;
    const ctx = canvas.getContext("2d");
    const img = new Image();
    img.onload = () => {
      ctx?.drawImage(img, 0, 0, size * 2, size * 2);
      URL.revokeObjectURL(url);
      const a = document.createElement("a");
      a.download = "resume-dna.png";
      a.href = canvas.toDataURL("image/png");
      a.click();
    };
    img.src = url;
  };

  return (
    <div className="flex flex-col items-center gap-4">
      <h3 className="text-lg font-semibold text-white">Your Resume DNA</h3>
      <p className="text-sm text-navy-400">
        Every resume has a unique fingerprint. This is yours.
      </p>

      <div className="relative">
        <svg
          ref={svgRef}
          width={size}
          height={size}
          viewBox={`0 0 ${size} ${size}`}
          className="drop-shadow-lg"
        >
          {/* Max extent ring */}
          <circle
            cx={cx}
            cy={cy}
            r={maxOuterR}
            fill="none"
            stroke="#334155"
            strokeWidth="1"
            opacity="0.3"
          />

          {/* Segments */}
          {segments.map((seg, i) => (
            <path
              key={seg.dim.id}
              d={seg.path}
              fill={seg.color}
              opacity={hoveredIdx === i ? 1 : seg.opacity}
              stroke={hoveredIdx === i ? "#fff" : "transparent"}
              strokeWidth={hoveredIdx === i ? 2 : 0}
              className="transition-opacity duration-200 cursor-pointer"
              onMouseEnter={() => setHoveredIdx(i)}
              onMouseLeave={() => setHoveredIdx(null)}
            />
          ))}

          {/* Center score */}
          <circle cx={cx} cy={cy} r={innerR - 4} fill="#0f172a" />
          <text
            x={cx}
            y={cy - 10}
            textAnchor="middle"
            fill="#ffffff"
            fontSize="32"
            fontWeight="bold"
          >
            {Math.round(combinedScore * progress)}
          </text>
          <text
            x={cx}
            y={cy + 18}
            textAnchor="middle"
            fill="#f59e0b"
            fontSize="20"
            fontWeight="bold"
          >
            {letterGrade}
          </text>
        </svg>

        {/* Tooltip */}
        {hoveredIdx !== null && segments[hoveredIdx] && (
          <div className="absolute top-2 left-1/2 -translate-x-1/2 bg-navy-800 border border-navy-600 rounded-lg px-3 py-2 text-sm text-white shadow-lg pointer-events-none z-10">
            <div className="font-semibold">{segments[hoveredIdx].dim.name}</div>
            <div className="text-navy-300">
              Score: {segments[hoveredIdx].dim.score} &middot; Weight:{" "}
              {(segments[hoveredIdx].dim.weight * 100).toFixed(0)}%
            </div>
          </div>
        )}
      </div>

      <button
        onClick={exportPng}
        className="text-sm text-navy-300 hover:text-amber-400 transition-colors"
      >
        Download as PNG
      </button>
    </div>
  );
}
