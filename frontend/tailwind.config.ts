import type { Config } from 'tailwindcss';

// Rafeqi colour tokens (palette 1b · Soft indigo) on Organic type/spacing. Values live as CSS variables in src/index.css
// (:root = light, .dark = dark) so every utility switches theme automatically.
const ramp = (name: string, steps = [100, 200, 300, 400, 500, 600, 700, 800, 900]) =>
  Object.fromEntries(steps.map((s) => [s, `var(--color-${name}-${s})`]));

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        bg: 'var(--color-bg)',
        surface: 'var(--color-surface)',
        ink: 'var(--color-text)',
        divider: 'var(--color-divider)',
        'on-accent': 'var(--color-on-accent)', // white text/icons on accent fills (both themes)
        accent: { DEFAULT: 'var(--color-accent)', ...ramp('accent') }, // indigo — main buttons, selected tab, today
        sage: { DEFAULT: 'var(--color-accent-2)', ...ramp('accent-2') }, // green — progress, "on track"
        attn: ramp('attn', [100, 200, 300, 500, 600, 700, 800]), // amber — "needs attention"
        neutral: ramp('neutral'),
        warn: ramp('warn', [100, 200, 300, 600, 700, 800]), // red — warnings, pain, health flags
      },
      fontFamily: {
        heading: 'var(--font-heading)',
        body: 'var(--font-body)',
      },
      spacing: {
        'o-1': '4.4px',
        'o-2': '8.8px',
        'o-3': '13.2px',
        'o-4': '17.6px',
        'o-6': '26.4px',
        'o-8': '35.2px',
        tap: '44px', // minimum touch target
      },
      minHeight: { tap: '44px' },
      minWidth: { tap: '44px' },
      borderRadius: {
        sm: '8px',
        md: '16px',
        lg: '28px',
        card: '32px',
        pill: '999px',
      },
      boxShadow: {
        sm: 'var(--shadow-sm)',
        md: 'var(--shadow-md)',
        lg: 'var(--shadow-lg)',
      },
      keyframes: {
        breathe: { '0%,100%': { transform: 'scale(.92)' }, '50%': { transform: 'scale(1.04)' } },
        pulseSoft: { '0%,100%': { opacity: '.45' }, '50%': { opacity: '1' } },
      },
      animation: {
        breathe: 'breathe 5s ease-in-out infinite',
        'pulse-soft': 'pulseSoft 1.6s ease-in-out infinite',
      },
    },
  },
  plugins: [],
} satisfies Config;
