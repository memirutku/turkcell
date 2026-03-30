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
        // Turkcell brand colors
        turkcell: {
          yellow: "#FFD100",
          dark: "#1A1A2E",
          blue: "#0066CC",
          gray: "#F5F5F5",
        },
      },
    },
  },
  plugins: [],
};

export default config;
