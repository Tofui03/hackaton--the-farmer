/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: {
        editorial: ['"Playfair Display"', 'serif'],
        display: ['Syne', 'sans-serif'],
        sans: ['"Plus Jakarta Sans"', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
      },
      colors: {
        carbon: {
          950: '#060709',
          900: '#0d0f12',
          850: '#12151a',
          800: '#1a1e24',
          700: '#262c36',
          600: '#323a46',
          500: '#485262',
        },
        klein: {
          DEFAULT: '#002fa7',
          glow: '#2563eb',
        },
      },
    },
  },
  plugins: [],
};

