/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#070b14",
        panel: "#0d1524",
        panel2: "#111c2e",
        line: "#1e3a5f",
        accent: "#3ee0c5",
        accent2: "#6ea8fe",
        warn: "#f5a524",
        danger: "#e5484d",
        muted: "#8ba0b5",
      },
      fontFamily: {
        sans: ["IBM Plex Sans", "Segoe UI", "sans-serif"],
        mono: ["IBM Plex Mono", "ui-monospace", "monospace"],
      },
    },
  },
  plugins: [],
};
