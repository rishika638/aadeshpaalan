import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        navy: "#0F172A",
        saffron: "#FF6B00",
        risk: {
          overdue: "#DC2626",
          critical: "#EA580C",
          dueSoon: "#D97706",
          watch: "#EAB308",
          compliant: "#16A34A"
        }
      },
      fontFamily: {
        sans: ["\"IBM Plex Sans\"", "ui-sans-serif", "system-ui"],
        mono: ["\"IBM Plex Mono\"", "ui-monospace", "SFMono-Regular"]
      }
    }
  },
  plugins: []
} satisfies Config;

