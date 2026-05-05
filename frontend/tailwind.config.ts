import type { Config } from 'tailwindcss';

export default {
  content: [
    './app/**/*.{ts,tsx}',
    './components/**/*.{ts,tsx}',
    './lib/**/*.{ts,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        cinetag: {
          red: '#E50914',
          redDark: '#B80710',
          redGlow: '#FF1F2D',
          ink: '#06070A',
          panel: '#0B0D12',
          panelMuted: '#10131A',
          border: '#1F2330',
          borderMuted: '#15181F',
          text: '#F5F7FA',
          textMuted: '#9CA3AF',
        },
      },
      fontFamily: {
        sans: ['ui-sans-serif', 'system-ui', '-apple-system', 'Segoe UI', 'Roboto', 'Helvetica', 'Arial', 'sans-serif'],
        mono: ['ui-monospace', 'SFMono-Regular', 'Menlo', 'Monaco', 'Consolas', 'monospace'],
        display: ['ui-sans-serif', 'system-ui', 'Segoe UI', 'Roboto', 'sans-serif'],
      },
      boxShadow: {
        glow: '0 0 30px rgba(229, 9, 20, 0.35)',
        card: '0 10px 40px -10px rgba(0,0,0,0.6), 0 2px 8px -2px rgba(0,0,0,0.4)',
        cardHover: '0 20px 60px -10px rgba(229, 9, 20, 0.25), 0 4px 16px -4px rgba(0,0,0,0.6)',
      },
      backgroundImage: {
        'cinetag-radial': 'radial-gradient(ellipse 80% 50% at 50% -10%, rgba(229,9,20,0.18), transparent), radial-gradient(ellipse 60% 50% at 80% 100%, rgba(120,58,180,0.12), transparent)',
        'panel-sheen': 'linear-gradient(180deg, rgba(255,255,255,0.04) 0%, rgba(255,255,255,0) 50%)',
        'thumb-1': 'linear-gradient(135deg, #1a1d29 0%, #2b1d3a 50%, #4a1a2e 100%)',
        'thumb-2': 'linear-gradient(135deg, #0e1a2b 0%, #1d3450 50%, #2a5a78 100%)',
        'thumb-3': 'linear-gradient(135deg, #2b1305 0%, #5a2410 50%, #a64923 100%)',
        'thumb-4': 'linear-gradient(135deg, #051a1a 0%, #0e3a3a 50%, #157a6a 100%)',
        'thumb-5': 'linear-gradient(135deg, #1a0926 0%, #311458 50%, #5d1d8a 100%)',
        'thumb-6': 'linear-gradient(135deg, #261705 0%, #58360b 50%, #b27021 100%)',
        'thumb-7': 'linear-gradient(135deg, #051022 0%, #0e2050 50%, #2540a8 100%)',
        'thumb-8': 'linear-gradient(135deg, #1a0a0a 0%, #3a1212 50%, #7a1f24 100%)',
      },
      animation: {
        shimmer: 'shimmer 2.4s ease-in-out infinite',
        pulseSoft: 'pulseSoft 3s ease-in-out infinite',
        floaty: 'floaty 6s ease-in-out infinite',
        scanline: 'scanline 2.4s linear infinite',
      },
      keyframes: {
        shimmer: {
          '0%': { transform: 'translateX(-100%)' },
          '100%': { transform: 'translateX(100%)' },
        },
        pulseSoft: {
          '0%, 100%': { opacity: '0.55' },
          '50%': { opacity: '1' },
        },
        floaty: {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-6px)' },
        },
        scanline: {
          '0%': { transform: 'translateX(-30%)' },
          '100%': { transform: 'translateX(130%)' },
        },
      },
    },
  },
  plugins: [],
} satisfies Config;
