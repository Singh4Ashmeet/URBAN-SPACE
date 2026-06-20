import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#122022",
        muted: "#627071",
        panel: "#ffffff",
        line: "#d8e1df",
        teal: {
          50: "#e9fbf7",
          100: "#c7f3ea",
          500: "#0f9f8f",
          700: "#087669"
        },
        amber: {
          50: "#fff7e8",
          500: "#cc7a00"
        },
        danger: {
          50: "#fff0ee",
          500: "#c93f30"
        }
      },
      boxShadow: {
        soft: "0 18px 50px rgba(18, 32, 34, 0.08)"
      }
    }
  },
  plugins: []
};

export default config;
