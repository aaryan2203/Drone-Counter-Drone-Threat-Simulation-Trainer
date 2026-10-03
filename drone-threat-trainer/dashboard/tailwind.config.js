/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: ["class"],
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        border: "hsl(215 28% 17%)",
        input: "hsl(215 28% 17%)",
        ring: "hsl(180 100% 50%)",
        background: "hsl(222 47% 8%)",
        foreground: "hsl(210 40% 98%)",
        primary: {
          DEFAULT: "hsl(180 100% 50%)",
          foreground: "hsl(222 47% 8%)",
        },
        secondary: {
          DEFAULT: "hsl(217 33% 17%)",
          foreground: "hsl(210 40% 98%)",
        },
        destructive: {
          DEFAULT: "hsl(0 84% 60%)",
          foreground: "hsl(210 40% 98%)",
        },
        muted: {
          DEFAULT: "hsl(217 33% 17%)",
          foreground: "hsl(215 20% 65%)",
        },
        accent: {
          DEFAULT: "hsl(48 96% 53%)",
          foreground: "hsl(222 47% 8%)",
        },
        card: {
          DEFAULT: "hsl(222 47% 11%)",
          foreground: "hsl(210 40% 98%)",
        },
      },
      borderRadius: {
        lg: "0.5rem",
        md: "0.375rem",
        sm: "0.25rem",
      },
    },
  },
  plugins: [],
};
