/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{html,ts}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        'sky-navy': '#02122c',
        'sky-navy-light': '#072044',
        'sky-blue': '#0062e3',
        'sky-blue-hover': '#0050b8',
        'sky-blue-light': '#e8f4fd',
        'sky-teal': '#00776d',
        'sky-teal-accent': '#85ffef',
        'sky-coral': '#ff5452',
        'sky-coral-dark': '#d83b39',
      },
      spacing: {
        '18': '4.5rem',
        '22': '5.5rem',
      },
      borderRadius: {
        '3xl': '1.5rem',
        '4xl': '2rem',
      }
    },
  },
  plugins: [],
};

