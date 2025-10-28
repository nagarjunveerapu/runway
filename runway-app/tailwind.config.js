// tailwind.config.js
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
    "./public/index.html",
  ],
  theme: {
    extend: {
      colors: {
        runwayTeal: '#007C91',     // Calm confidence
        runwayOrange: '#FFB74D',   // Hope & lift-off
        runwayGray: '#F4F7F8',     // Soft neutral background
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      borderRadius: {
        '2xl': '1rem',
      },
    },
  },
  plugins: [],
};