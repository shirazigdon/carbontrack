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
          50:      '#eef8f2',
          100:     '#d8f3e3',
          200:     '#b7e4c7',
          300:     '#95d5b2',
        },
        sidebar: {
          bg:     '#1b4332',
          fg:     '#b7e4c7',
          border: 'rgba(183,228,199,0.12)',
          accent: 'rgba(149,213,178,0.15)',
          active: '#95d5b2',
        },
        border:  '#b7e4c7',
        muted: {
          DEFAULT: '#eef8f2',
          fg:      '#4a7c59',
        },
        card:        '#ffffff',
        bg:          '#f7fbf7',
        success:     '#40916c',
        warning:     '#e9c46a',
        destructive: '#e63946',
      },
      fontFamily: {
        sans: ['Rubik', 'sans-serif'],
      },
      borderRadius: {
        DEFAULT: '0.5rem',
        lg: '0.75rem',
        xl: '1rem',
        '2xl': '1.25rem',
        '3xl': '1.75rem',
        '4xl': '2rem',
      },
      boxShadow: {
        card:     '0 2px 12px rgba(27,67,50,0.07), 0 0 0 1.5px #b7e4c7',
        elevated: '0 8px 28px rgba(27,67,50,0.12)',
        kpi:      '0 2px 10px rgba(27,67,50,0.08), 0 0 0 1.5px #b7e4c7',
      },
    },
  },
  plugins: [],
};
