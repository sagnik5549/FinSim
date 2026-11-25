/** @type {import('tailwindcss').Config} */
// Colours are CSS variables (space-separated RGB channels, see src/index.css) so the
// dark and light themes share every class and opacity modifiers keep working.
const v = (name) => `rgb(var(--${name}) / <alpha-value>)`
const soft = (name) => `rgb(var(--${name}) / 0.12)`

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        ink: {
          950: v('ink-950'),
          900: v('ink-900'),
          850: v('ink-850'),
          800: v('ink-800'),
          750: v('ink-750'),
          700: v('ink-700'),
          600: v('ink-600'),
          500: v('ink-500'),
        },
        line: v('line'),
        txt: { DEFAULT: v('txt'), dim: v('txt-dim'), mute: v('txt-mute') },
        up: { DEFAULT: v('up'), soft: soft('up') },
        down: { DEFAULT: v('down'), soft: soft('down') },
        warn: { DEFAULT: v('warn'), soft: soft('warn') },
        info: { DEFAULT: v('info'), soft: soft('info') },
        violet: { DEFAULT: v('violet'), soft: soft('violet') },
        gold: { DEFAULT: v('gold'), soft: soft('gold') },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'Segoe UI', 'sans-serif'],
        mono: ['Inter', 'system-ui', 'sans-serif'],
        display: ['Inter', 'system-ui', 'sans-serif'],
      },
      fontSize: { '2xs': ['11px', '15px'] },
      boxShadow: {
        panel: 'none',
        pop: '0 12px 32px -8px rgb(0 0 0 / 0.45), 0 0 0 1px rgb(var(--line))',
        glowUp: 'none',
        glowDown: 'none',
        glowInfo: 'none',
        glowGold: 'none',
      },
      keyframes: {
        fadeIn: { from: { opacity: 0 }, to: { opacity: 1 } },
        scaleIn: { from: { opacity: 0, transform: 'translateY(4px)' }, to: { opacity: 1, transform: 'none' } },
        flashUp: { '0%': { backgroundColor: 'rgb(var(--up) / 0.22)' }, '100%': { backgroundColor: 'transparent' } },
        flashDown: { '0%': { backgroundColor: 'rgb(var(--down) / 0.22)' }, '100%': { backgroundColor: 'transparent' } },
        pulseDot: { '0%,100%': { opacity: 1 }, '50%': { opacity: 0.35 } },
        stamp: { '0%': { opacity: 0, transform: 'scale(1.3) rotate(-6deg)' }, '100%': { opacity: 1, transform: 'scale(1) rotate(-6deg)' } },
        sweep: { from: { transform: 'translateX(-100%)' }, to: { transform: 'translateX(100%)' } },
        rise: { from: { opacity: 0, transform: 'translateY(8px)' }, to: { opacity: 1, transform: 'none' } },
        slideIn: { from: { opacity: 0, transform: 'translateX(12px)' }, to: { opacity: 1, transform: 'none' } },
      },
      animation: {
        fadeIn: 'fadeIn .15s ease-out both',
        scaleIn: 'scaleIn .15s ease-out both',
        flashUp: 'flashUp .8s ease-out',
        flashDown: 'flashDown .8s ease-out',
        pulseDot: 'pulseDot 1.6s ease-in-out infinite',
        stamp: 'stamp .4s ease-out both',
        sweep: 'sweep 2.4s ease-in-out infinite',
        rise: 'rise .3s ease-out both',
        slideIn: 'slideIn .15s ease-out both',
      },
    },
  },
  plugins: [],
}
