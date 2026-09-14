import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        background: "#0B0F19",
        surface: {
          DEFAULT: "#111827",
          hover: "#1F2937",
          border: "#1F2937",
          subtle: "#161F30",
        },
        accent: {
          blue: "#3B82F6",
          emerald: "#10B981",
          amber: "#F59E0B",
          crimson: "#EF4444",
        },
      },
      fontFamily: {
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "Monaco", "Consolas", "Liberation Mono", "monospace"],
      },
    },
  },
  plugins: [],
};

export default config;
