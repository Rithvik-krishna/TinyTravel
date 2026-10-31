/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  darkMode: "media",
  theme: {
    extend: {
      colors: {
        surface: "var(--surface)",
        "surface-2": "var(--surface-2)",
        border: "var(--border)",
        text: "var(--text)",
        "text-muted": "var(--text-muted)",
        brand: "var(--brand)",
        success: "var(--success)",
        warning: "var(--warning)",
        danger: "var(--danger)",
        info: "var(--info)",

        // Landing tokens (defined under .tt in globals.css; prefixed because --surface etc. already exist)
        "tt-bg": "var(--bg)",
        "tt-surface": "var(--surface)",
        "tt-surface2": "var(--surface2)",
        "tt-line": "var(--line)",
        "tt-fg": "var(--fg)",
        "tt-muted": "var(--muted)",
        "tt-brass": "var(--brass)",
        "tt-brass-hi": "var(--brass-hi)",
        "tt-brass-lo": "var(--brass-lo)",
        "tt-ok": "var(--ok)",
        "tt-warn": "var(--warn)",
        "tt-bad": "var(--bad)",
        "tt-info": "var(--info)",
        "tt-tag-bg": "var(--tag-bg)",
        "tt-tag-fg": "var(--tag-fg)",
        "tt-tag-muted": "var(--tag-muted)",
        "tt-tag-line": "var(--tag-line)",
        "tt-on-brass": "var(--on-brass)",

        // Compatibility aliases for rail gallery / shadcn styles
        background: "var(--color-background)",
        foreground: "var(--color-foreground)",
        card: {
          DEFAULT: "var(--color-card)",
          foreground: "var(--color-card-foreground)",
        },
        muted: {
          DEFAULT: "var(--color-muted)",
          foreground: "var(--color-muted-foreground)",
        },
        ring: "var(--color-ring)",
        "chart-2": "var(--color-chart-2)",
      },
    },
  },
  plugins: [],
};
