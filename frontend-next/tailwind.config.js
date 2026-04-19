/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: 'hsl(152, 60%, 32%)',
          light: 'hsl(152, 55%, 40%)',
          50: 'hsl(152, 70%, 96%)',
          100: 'hsl(152, 65%, 90%)',
        },
        sidebar: {
          bg: '#0f1729',
          fg: '#94a3b8',
          border: 'rgba(255,255,255,0.07)',
          accent: 'rgba(255,255,255,0.06)',
          active: '#10b981',
        },
        border: '#e2e8f0',
        muted: {
          DEFAULT: '#f8fafc',
          fg: '#64748b',
        },
        card: '#ffffff',
        bg: '#f1f5f9',
        success: 'hsl(152, 60%, 38%)',
        warning: 'hsl(38, 92%, 50%)',
        destructive: 'hsl(0, 72%, 51%)',
      },
      fontFamily: {
        sans: ['Heebo', 'sans-serif'],
      },
      boxShadow: {
        card: '0 1px 3px 0 rgb(15 23 42 / 0.05), 0 1px 2px -1px rgb(15 23 42 / 0.04)',
        elevated: '0 10px 25px -5px rgb(15 23 42 / 0.08), 0 8px 10px -6px rgb(15 23 42 / 0.04)',
        kpi: '0 0 0 1px #e2e8f0, 0 2px 8px 0 rgb(15 23 42 / 0.06)',
      },
      borderRadius: {
        '2xl': '1rem',
        '3xl': '1.5rem',
      },
    },
  },
  plugins: [],
};
