/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./pages/**/*.{js,jsx}",
    "./components/**/*.{js,jsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          DEFAULT: "#E8612C",
          light:   "#f4a261",
          pale:    "#fde8d8",
          dark:    "#c0392b",
        },
        surface: "#faf9f7",
        card:    "#ffffff",
        ink:     "#1a1a1a",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};
