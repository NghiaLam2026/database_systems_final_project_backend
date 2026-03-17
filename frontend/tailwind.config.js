/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        ink: {
          950: '#0b1220',
          900: '#10192c',
          800: '#172340',
        },
        mist: {
          50: '#f6f8ff',
          100: '#eef2ff',
          200: '#e5e7ff',
          300: '#d9ddff',
        },
        brand: {
          600: '#3b82f6',
          500: '#60a5fa',
          400: '#93c5fd',
        },
      },
      boxShadow: {
        soft: '0 12px 30px rgba(15, 23, 42, 0.10)',
        card: '0 16px 40px rgba(2, 6, 23, 0.08)',
      },
      borderRadius: {
        xl2: '1.25rem',
      },
    },
  },
  plugins: [],
}

