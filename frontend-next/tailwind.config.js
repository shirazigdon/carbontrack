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
          DEFAULT: 'hsl(142, 55%, 35%)',
          light: 'hsl(152, 45%, 42%)',
        },
        sidebar: {
          bg: 'hsl(150, 30%, 10%)',
          fg: 'hsl(140, 15%, 85%)',
          border: 'hsl(150, 18%, 18%)',
          accent: 'hsl(150, 22%, 16%)',
        },
        border: 'hsl(140, 15%, 89%)',
        muted: {
          DEFAULT: 'hsl(140, 12%, 93%)',
          fg: 'hsl(150, 10%, 45%)',
        },
        card: '#ffffff',
        bg: 'hsl(140, 10%, 97%)',
        success: 'hsl(152, 60%, 40%)',
        warning: 'hsl(38, 92%, 50%)',
        destructive: 'hsl(0, 72%, 51%)',
      },
      fontFamily: {
        sans: ['Heebo', 'sans-serif'],
      },
      boxShadow: {
        card: '0 1px 3px 0 hsl(150 25% 10% / 0.04), 0 1px 2px -1px hsl(150 25% 10% / 0.04)',
        elevated: '0 10px 25px -5px hsl(150 25% 10% / 0.08), 0 8px 10px -6px hsl(150 25% 10% / 0.04)',
      },
    },
  },
  plugins: [],
};

