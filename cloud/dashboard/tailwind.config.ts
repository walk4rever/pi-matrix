import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        parchment: "#f5f4ed",
        ivory: "#faf9f5",
        terracotta: "#c96442",
        coral: "#d97757",
        nearblack: "#141413",
        "dark-surface": "#30302e",
        "warm-sand": "#e8e6dc",
        "charcoal-warm": "#4d4c48",
        "olive-gray": "#5e5d59",
        "stone-gray": "#87867f",
        "warm-silver": "#b0aea5",
        "border-cream": "#f0eee6",
        "border-warm": "#e8e6dc",
      },
      fontFamily: {
        serif: ["Georgia", "Times New Roman", "serif"],
        sans: ["Inter", "system-ui", "-apple-system", "sans-serif"],
      },
      boxShadow: {
        ring: "0px 0px 0px 1px #d1cfc5",
        "ring-terracotta": "0px 0px 0px 1px #c96442",
        whisper: "rgba(0,0,0,0.05) 0px 4px 24px",
      },
    },
  },
  plugins: [],
};

export default config;
