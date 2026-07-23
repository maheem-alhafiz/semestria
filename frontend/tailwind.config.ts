import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ["var(--font-inter)", "system-ui", "sans-serif"],
      },
      colors: {
        // Dark "semestria." fintech aesthetic. brand.* is kept as an
        // alias to the teal accent so any bg-brand/text-brand usages in
        // files outside this pass (e.g. the old "/" search page) don't
        // break -- they'll just pick up the new accent color instead of
        // the old UM blue.
        brand: {
          DEFAULT: "#5EC8D8",
          dark: "#3FA3B3",
          light: "#1A2E30",
        },
        canvas: "#0A0A0A",
        panel: "#1A1A1A",
        elevated: "#242424",
        hairline: "#333333",
        paper: "#F2ECE0",
        muted: "#9A9A9A",
        accent: "#5EC8D8",
        success: "#8CD17D",
        warning: "#E8C468",
        danger: "#F27983",
      },
    },
  },
  plugins: [],
};

export default config;
