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
          DEFAULT: '#52b788',  // sage green — accent only
          light:   '#74c69d',
          50:      '#eef8f2',
          100:     '#d8f3e3',
          200:     '#b7e4c7',
        },
        sky:   '#5b9bd5',   // chart / accent blue
        amber: '#e8a87c',   // chart / warm accent
        earth: '#8b6f47',   // grounding brown
        sidebar: {
          bg:     '#1b4332',
          fg:     '#b7e4c7',
          border: 'rgba(183,228,199,0.12)',
          active: '#95d5b2',
        },
        border:  '#ddd9d0',   // warm parchment border
        muted: {
          DEFAULT: '#f0ede6',
          fg:      '#6b7c6b',
        },
        card:        '#ffffff',
        bg:          '#f6f4ef',  // warm parchment
        success:     '#40916c',
        warning:     '#e9a84c',
        destructive: '#e63946',
      },
      fontFamily: {
        sans: ['Rubik', 'sans-serif'],
      },
      borderRadius: {
        xl:  '1rem',
        '2xl': '1.25rem',
        '3xl': '1.75rem',
      },
      boxShadow: {
        card:     '0 2px 10px rgba(44,62,45,0.06), 0 0 0 1px #ddd9d0',
        elevated: '0 8px 28px rgba(44,62,45,0.10)',
        kpi:      '0 2px 10px rgba(44,62,45,0.07)',
      },
    },
  },
  plugins: [],
};
