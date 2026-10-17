import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{js,ts,jsx,tsx,mdx}", "./components/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        bg: "var(--bg)", ink: "var(--ink)", "ink-2": "var(--ink-2)", "ink-3": "var(--ink-3)",
        rule: "var(--rule)", "rule-2": "var(--rule-2)",
        accent: "var(--accent)", "accent-dk": "var(--accent-dk)",
        signal: "var(--signal)", ok: "var(--ok)", panel: "var(--panel)",
      },
      fontFamily: {
        serif: ["var(--serif)", "Georgia", "serif"],
        sans: ["var(--sans)", "system-ui", "sans-serif"],
        mono: ["var(--mono)", "Courier New", "monospace"],
      },
    },
  },
  plugins: [],
};

export default config;
