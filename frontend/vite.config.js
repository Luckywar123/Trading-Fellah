import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: { port: 5173 },
  build: {
    // pecah bundle 900KB+ jadi beberapa chunk biar load awal lebih ringan
    rollupOptions: {
      output: {
        manualChunks: {
          react: ['react', 'react-dom', 'react-router-dom'],
          charts: ['recharts'],
          web3: ['ethers'],
        },
      },
    },
    chunkSizeWarningLimit: 700,
  },
})
