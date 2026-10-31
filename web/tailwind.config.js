/** @type {import('tailwindcss').Config} */
// Colours come from the CSS variables defined once in app/globals.css (the "Coastal Minimal" palette).
module.exports = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  darkMode: "media",
  theme: {
    extend: {
      colors: {
        background: "var(--background)",
        surface: "var(--surface)",
        "surface-2": "var(--surface-2)",
        ink: "var(--ink)",
        muted: {
          DEFAULT: "var(--muted)",
          foreground: "var(--color-muted-foreground)",
        },
        line: "var(--line)",
        brand: "var(--brand)",
        "brand-hover": "var(--brand-hover)",
        "brand-soft": "var(--brand-soft)",
        "brand-ink": "var(--brand-ink)",
        accent: "var(--accent)",
        "accent-soft": "var(--accent-soft)",
        gap: "var(--gap)",
        warn: "var(--warn)",
        "warn-soft": "var(--warn-soft)",
        ok: "var(--ok)",
        "ok-soft": "var(--ok-soft)",
        bad: "var(--bad)",
        "bad-soft": "var(--bad-soft)",
        sand: "var(--sand)",

        // Names the existing components already use, pointed at the new tokens.
        border: "var(--border)",
        text: "var(--text)",
        "text-muted": "var(--text-muted)",
        success: "var(--success)",
        warning: "var(--warning)",
        danger: "var(--danger)",
        info: "var(--info)",
        foreground: "var(--color-foreground)",
        card: {
          DEFAULT: "var(--color-card)",
          foreground: "var(--color-card-foreground)",
        },
        ring: "var(--color-ring)",
        "chart-2": "var(--color-chart-2)",
      },
    },
  },
  plugins: [],
};