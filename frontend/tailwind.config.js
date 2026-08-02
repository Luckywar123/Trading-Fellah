/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        void: '#0D1012',
        panel: '#161A1D',
        raised: '#1E2327',
        line: '#2A3035',
        amber: {
          DEFAULT: '#F0A030',
          soft: '#F0A03022',
          dim: '#8A6224',
        },
        cyan: {
          DEFAULT: '#4FD1C5',
          soft: '#4FD1C522',
        },
        long: '#34D399',
        short: '#F2545B',
        ink: {
          DEFAULT: '#E8E6E1',
          muted: '#8A8F93',
          faint: '#5A6166',
        },
      },
      fontFamily: {
        display: ['"Space Grotesk"', 'sans-serif'],
        body: ['"IBM Plex Sans"', 'sans-serif'],
        mono: ['"IBM Plex Mono"', 'monospace'],
      },
    },
  },
  plugins: [],
}
