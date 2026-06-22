/** Waveform visualizer for microphone input using Web Audio API. */

import { useEffect, useRef, useState } from "react";

interface Props {
  isRecording: boolean;
  /** Raw audio data for visualization (0-255 range, like AnalyserNode output). */
  audioData?: Uint8Array;
}

export default function VoiceWave({ isRecording, audioData }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animFrameRef = useRef<number>(0);
  const [bars] = useState(() =>
    Array.from({ length: 32 }, () => Math.random() * 0.3)
  );

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const draw = () => {
      const { width, height } = canvas;
      ctx.clearRect(0, 0, width, height);

      const barCount = 32;
      const barWidth = width / barCount - 2;
      const centerY = height / 2;

      for (let i = 0; i < barCount; i++) {
        let amplitude: number;

        if (audioData && audioData.length > 0 && isRecording) {
          // Use real audio data
          const dataIndex = Math.floor(
            (i / barCount) * audioData.length
          );
          amplitude = (audioData[dataIndex] / 255) * height * 0.8;
        } else if (isRecording) {
          // Simulate idle recording
          amplitude =
            (Math.sin(Date.now() / 200 + i * 0.5) * 0.3 + 0.4) *
            height *
            0.4;
        } else {
          // Static idle
          amplitude = bars[i] * height * 0.15;
        }

        const halfAmp = amplitude / 2;
        const x = i * (barWidth + 2) + 1;

        // Gradient color based on amplitude
        const intensity = amplitude / (height * 0.8);
        if (isRecording) {
          ctx.fillStyle = `rgba(245, 158, 11, ${0.4 + intensity * 0.6})`;
        } else {
          ctx.fillStyle = `rgba(100, 116, 139, ${0.3 + intensity * 0.4})`;
        }

        // Draw bar centered vertically
        const radius = Math.min(barWidth / 2, 3);
        roundRect(ctx, x, centerY - halfAmp, barWidth, amplitude, radius);
      }

      animFrameRef.current = requestAnimationFrame(draw);
    };

    draw();
    return () => cancelAnimationFrame(animFrameRef.current);
  }, [isRecording, audioData, bars]);

  return (
    <div className="flex items-center justify-center">
      <canvas
        ref={canvasRef}
        width={320}
        height={80}
        className="w-full max-w-sm"
      />
    </div>
  );
}

function roundRect(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  w: number,
  h: number,
  r: number
) {
  if (h < 1) h = 1;
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.lineTo(x + w - r, y);
  ctx.quadraticCurveTo(x + w, y, x + w, y + r);
  ctx.lineTo(x + w, y + h - r);
  ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
  ctx.lineTo(x + r, y + h);
  ctx.quadraticCurveTo(x, y + h, x, y + h - r);
  ctx.lineTo(x, y + r);
  ctx.quadraticCurveTo(x, y, x + r, y);
  ctx.closePath();
  ctx.fill();
}
