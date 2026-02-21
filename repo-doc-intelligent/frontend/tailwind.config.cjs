/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        codeRepo: {
          dark: '#0a0a0f',
          bg: '#12121a',
          surface: '#1a1a24',
          accent: '#6366f1',
          'accent-hover': '#5558e3',
        },
      },
      backgroundImage: {
        'gradient-accent': 'linear-gradient(135deg, #6366f1 0%, #8b5cf6 50%, #a855f7 100%)',
        'gradient-glow': 'radial-gradient(ellipse at 50% 0%, rgba(99, 102, 241, 0.15) 0%, transparent 60%)',
      },
    },
  },
  plugins: [require('@tailwindcss/typography')],
}
