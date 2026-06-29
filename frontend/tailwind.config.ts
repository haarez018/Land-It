import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        amber: {
          50: "#fffbeb", 100: "#fef3c7", 200: "#fde68a", 300: "#fcd34d",
          400: "#fbbf24", 500: "#f59e0b", 600: "#d97706", 700: "#b45309",
          800: "#92400e", 900: "#78350f",
        },
        navy: {
          50: "#f0f4ff", 100: "#dbe4ff", 200: "#bac8ff", 300: "#91a7ff",
          400: "#748ffc", 500: "#5c7cfa", 600: "#4c6ef5", 700: "#1a2744",
          800: "#141e33", 900: "#0e1624", 950: "#080d18",
        },
        cp: {
          bg: "#060914",
          panel: "#0d1117",
          "panel-2": "#111827",
          hairline: "#1f2937",
          text: "#f0f4ff",
          "text-dim": "#94a3b8",
          "text-mute": "#475569",
          accent: "#00F5A0",
          "accent-dim": "#00c47f",
          purple: "#8A2BE2",
          "purple-dim": "#6d21b8",
          warn: "#FFB020",
          danger: "#FF4D6D",
        },
      },
      fontFamily: {
        sans: ["Inter Tight", "Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "Geist Mono", "ui-monospace", "monospace"],
      },
      backgroundImage: {
        "mesh-dark": `
          radial-gradient(ellipse 80% 60% at 10% 0%, rgba(138,43,226,0.18) 0%, transparent 60%),
          radial-gradient(ellipse 60% 50% at 90% 10%, rgba(0,245,160,0.10) 0%, transparent 55%),
          radial-gradient(ellipse 70% 60% at 50% 100%, rgba(59,130,246,0.12) 0%, transparent 60%),
          radial-gradient(ellipse 50% 40% at 80% 80%, rgba(138,43,226,0.08) 0%, transparent 50%)
        `,
        "mesh-light": `
          radial-gradient(ellipse 80% 60% at 10% 0%, rgba(138,43,226,0.08) 0%, transparent 60%),
          radial-gradient(ellipse 60% 50% at 90% 10%, rgba(0,245,160,0.12) 0%, transparent 55%),
          radial-gradient(ellipse 70% 60% at 50% 100%, rgba(59,130,246,0.07) 0%, transparent 60%)
        `,
        "gradient-radial": "radial-gradient(var(--tw-gradient-stops))",
      },
      animation: {
        "fade-in": "fadeIn 0.5s ease-out",
        "slide-up": "slideUp 0.5s ease-out",
        "scale-in": "scaleIn 0.3s ease-out",
        "dot-pulse": "dotPulse 1.4s ease-in-out infinite",
        "glow-rotate": "glowRotate 3s linear infinite",
        "card-in": "cardIn 0.4s cubic-bezier(0.34,1.56,0.64,1) both",
        "float-up": "floatUp 0.3s ease-out both",
        "shimmer-sweep": "shimmerSweep 2.5s linear infinite",
      },
      keyframes: {
        fadeIn: { "0%": { opacity: "0" }, "100%": { opacity: "1" } },
        slideUp: {
          "0%": { opacity: "0", transform: "translateY(20px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        scaleIn: {
          "0%": { opacity: "0", transform: "scale(0.96)" },
          "100%": { opacity: "1", transform: "scale(1)" },
        },
        dotPulse: {
          "0%, 100%": { opacity: "0.3" },
          "50%": { opacity: "1" },
        },
        glowRotate: {
          "0%": { backgroundPosition: "0% 50%" },
          "50%": { backgroundPosition: "100% 50%" },
          "100%": { backgroundPosition: "0% 50%" },
        },
        cardIn: {
          "0%": { opacity: "0", transform: "translateY(16px) scale(0.96)" },
          "100%": { opacity: "1", transform: "translateY(0) scale(1)" },
        },
        floatUp: {
          "0%": { opacity: "0", transform: "translateY(4px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        shimmerSweep: {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
      },
    },
  },
  plugins: [],
} satisfies Config;
