import type { Config } from 'tailwindcss';
import forms from '@tailwindcss/forms';
import typography from '@tailwindcss/typography';

const config: Config = {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        bg: {
          0: '#000000',
          1: '#0b0b0f',
          2: '#1a1a1f',
          3: '#2a2a31',
        },
        text: {
          0: '#ffffff',
          1: '#b3b3b3',
          2: '#777777',
        },
        accent: {
          DEFAULT: '#e50914',
          dark: '#831010',
        },
        success: '#46d369',
        warning: '#f5a623',
        danger: '#e87c03',
      },
      fontFamily: {
        display: [
          'Inter',
          'system-ui',
          '-apple-system',
          'Segoe UI',
          'Roboto',
          'Helvetica',
          'Arial',
          'sans-serif',
        ],
      },
      letterSpacing: {
        tightest: '-0.02em',
        wider: '0.05em',
      },
      maxWidth: {
        rail: '1440px',
      },
      boxShadow: {
        card: '0 8px 24px rgba(0,0,0,0.7)',
        glow: '0 0 0 2px rgba(229,9,20,0.5), 0 8px 24px rgba(0,0,0,0.7)',
      },
      keyframes: {
        shimmer: {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
        'card-rise': {
          '0%': { transform: 'scale(1)', boxShadow: '0 0 0 rgba(0,0,0,0)' },
          '100%': { transform: 'scale(1.08)', boxShadow: '0 8px 24px rgba(0,0,0,0.7)' },
        },
        'fade-in': {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
      },
      animation: {
        shimmer: 'shimmer 1.6s linear infinite',
        'card-rise': 'card-rise 250ms ease-out forwards',
        'fade-in': 'fade-in 150ms ease-out',
      },
      backgroundImage: {
        'fade-right': 'linear-gradient(90deg, #000 0%, transparent 60%)',
        'fade-bottom': 'linear-gradient(180deg, transparent 30%, #000 100%)',
      },
    },
  },
  plugins: [forms, typography],
};

export default config;
