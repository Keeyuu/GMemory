import {
  defineConfig,
  presetUno,
  presetIcons,
  presetTypography,
  transformerDirectives,
  transformerVariantGroup,
} from 'unocss'

export default defineConfig({
  presets: [
    presetUno(),
    presetIcons({
      scale: 1.2,
      cdn: 'https://esm.sh/',
    }),
    presetTypography(),
  ],
  transformers: [
    transformerDirectives(),
    transformerVariantGroup(),
  ],
  theme: {
    colors: {
      // GMemory brand - deep space theme with neural accent
      neural: {
        50: '#f0fdf4',
        100: '#dcfce7',
        200: '#bbf7d0',
        300: '#86efac',
        400: '#4ade80',
        500: '#22c55e',
        600: '#16a34a',
        700: '#15803d',
        800: '#166534',
        900: '#14532d',
      },
      space: {
        50: '#f8fafc',
        100: '#f1f5f9',
        200: '#e2e8f0',
        300: '#cbd5e1',
        400: '#94a3b8',
        500: '#64748b',
        600: '#475569',
        700: '#334155',
        800: '#1e293b',
        900: '#0f172a',
        950: '#020617',
      },
    },
    fontFamily: {
      display: ['JetBrains Mono', 'SF Mono', 'monospace'],
      body: ['Inter', 'system-ui', 'sans-serif'],
      mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
    },
  },
  shortcuts: {
    'btn': 'px-4 py-2 rounded-lg font-medium transition-all duration-200 cursor-pointer',
    'btn-primary': 'btn bg-neural-500 text-white hover:bg-neural-600 active:bg-neural-700',
    'btn-ghost': 'btn bg-transparent text-space-300 hover:bg-space-800 hover:text-white',
    'btn-danger': 'btn bg-red-500/20 text-red-400 hover:bg-red-500/30',
    'card': 'bg-space-900/50 backdrop-blur-sm border border-space-800 rounded-xl',
    'input': 'w-full px-4 py-3 bg-space-900 border border-space-700 rounded-lg text-white placeholder-space-500 focus:outline-none focus:border-neural-500 focus:ring-1 focus:ring-neural-500/50 transition-all',
    'tag': 'inline-flex items-center px-2 py-0.5 text-xs font-medium rounded-md',
    'tag-neural': 'tag bg-neural-500/20 text-neural-400',
    'tag-high': 'tag bg-red-500/20 text-red-400',
    'tag-medium': 'tag bg-amber-500/20 text-amber-400',
    'tag-low': 'tag bg-space-500/20 text-space-400',
  },
})
