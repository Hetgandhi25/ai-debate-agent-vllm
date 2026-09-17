/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
      },
      colors: {
        background: '#F5F7FC',
        sidebar: '#111A36',
        text: {
          primary: '#17213D',
          secondary: '#64748B'
        },
        border: {
          light: '#E2E8F0'
        },
        debater: {
          a: '#4F7FFF',
          b: '#E11D68',
        }
      },
    },
  },
  plugins: [require("@tailwindcss/typography")],
}