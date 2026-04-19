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
          DEFAULT: '#52b788',
          light:   '#74c69d',
          50:      '#f0f7f4',
          100:     '#d8f3e3',
          200:     '#b7e4c7',
        },
        sidebar: {
          bg:     '#1b4332',
          fg:     '#b7e4c7',
          border: 'rgba(183,228,199,0.12)',
          accent: 'rgba(183,228,199,0.08)',
          active: '#95d5b2',
        },
        border:  '#c8e6c9',
        muted: {
          DEFAULT: '#f0f7f4',
          fg:      '#4a7c59',
        },
        card:        '#ffffff',
        bg:          '#f0f7f4',
        success:     '#40916c',
        warning:     '#e9c46a',
        destructive: '#e63946',
      },
      fontFamily: {
        sans: ['Rubik', 'Heebo', 'sans-serif'],
      },
      borderRadius: {
        xl:   '0.875rem',
        '2xl':'1.125rem',
        '3xl':'1.5rem',
      },
      boxShadow: {
        card:     '0 1px 4px 0 rgba(27,67,50,0.06), 0 1px 2px -1px rgba(27,67,50,0.04)',
        elevated: '0 8px 24px -4px rgba(27,67,50,0.10), 0 4px 8px -4px rgba(27,67,50,0.06)',
        kpi:      '0 0 0 1px #c8e6c9, 0 2px 8px 0 rgba(27,67,50,0.07)',
      },
    },
  },
  plugins: [],
};
