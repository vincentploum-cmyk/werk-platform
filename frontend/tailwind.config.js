/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  // Dark mode is opt-in by class (never set today): the app is deliberately
  // light-first, and this keeps the old half-implemented `dark:` variants inert.
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Brand accent — reserve for primary actions and active state.
        accent: {
          DEFAULT: '#4f46e5', // 6.3:1 with white text (AA)
          hover: '#4338ca',
          soft: '#eef2ff',
        },
        // Semantic state colors, all ≥4.5:1 with white text (WCAG AA).
        state: {
          progress: { DEFAULT: '#b45309', hover: '#92400e' },
          review: { DEFAULT: '#6d28d9', hover: '#5b21b6' },
          done: { DEFAULT: '#047857', hover: '#065f46' },
          danger: { DEFAULT: '#b91c1c', hover: '#991b1b' },
        },
        // Neutrals tinted toward the brand hue (OKLCH, hue 275) so surfaces and
        // text feel cohesive with the accent instead of flat gray.
        // <alpha-value> keeps opacity modifiers (e.g. bg-gray-800/50) working.
        gray: {
          50: 'oklch(98.4% 0.004 275 / <alpha-value>)',
          100: 'oklch(96.6% 0.005 275 / <alpha-value>)',
          200: 'oklch(92.7% 0.007 275 / <alpha-value>)',
          300: 'oklch(86.9% 0.009 275 / <alpha-value>)',
          400: 'oklch(70.9% 0.012 275 / <alpha-value>)',
          500: 'oklch(54.5% 0.015 275 / <alpha-value>)',
          600: 'oklch(44.5% 0.015 275 / <alpha-value>)',
          700: 'oklch(37.2% 0.013 275 / <alpha-value>)',
          800: 'oklch(27.9% 0.011 275 / <alpha-value>)',
          900: 'oklch(20.8% 0.009 275 / <alpha-value>)',
        },
      },
    },
  },
  plugins: [],
}
