/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'bupt-blue': {
          DEFAULT: '#003d74',
          light: '#0056a3',
          dark: '#002a50',
        },
        'mint-green': {
          DEFAULT: '#10b981',
          light: '#34d399',
          dark: '#059669',
        },
        'primary': '#003d74',
        'accent': '#10b981',
        'bg': {
          'main': '#f3f4f6',
        },
        'text': {
          'main': '#1f2937',
        },
        'border': {
          'main': '#e2e8f0',
        },
        'panel': 'white',
        'hover': {
          'bg': '#eff6ff',
        },
      },
      backdropBlur: {
        xs: '2px',
      },
      animation: {
        'spin-slow': 'spin 3s linear infinite',
      },
      transitionProperty: {
        'all': 'all',
      },
      transitionDuration: {
        '200': '200ms',
        '300': '300ms',
      }
    },
  },
  plugins: [],
}
