import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // earthy, calm — suitable for health workers and parents
        leaf: {
          50: "#f2fbf5",
          100: "#e0f6e6",
          200: "#c3ebd1",
          300: "#96d9b1",
          400: "#5fbf8b",
          500: "#39a26b",
          600: "#288254",
          700: "#236845",
          800: "#1f5239",
          900: "#1a4431",
        },
        soil: {
          50: "#fbf7f4",
          100: "#f5ede5",
          200: "#ebd8c8",
          300: "#debaa0",
          400: "#cf9572",
          500: "#c2784f",
          600: "#b5613e",
          700: "#964c32",
          800: "#7d3f2d",
          900: "#653527",
        },
      },
      fontFamily: {
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};

export default config;
