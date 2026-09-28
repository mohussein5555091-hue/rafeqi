import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { fileURLToPath, URL } from 'node:url';

// The browser only ever talks to this dev server. Requests to /api are forwarded
// to the FastAPI backend, so the app and the API share one origin (the session
// cookie stays same-site, and a phone on the Wi-Fi only needs this one address).
const backend = process.env.RAFEQI_BACKEND_URL ?? 'http://127.0.0.1:8000';
// Also accept requests arriving through a Cloudflare quick tunnel (npm run tunnel).
const allowedHosts = ['.trycloudflare.com'];
// xfwd: pass the visitor's real IP to the API (X-Forwarded-For), so login rate limits are per person.
// Uvicorn only trusts that header from 127.0.0.1, i.e. from this proxy.

export default defineConfig({
  plugins: [react()],
  resolve: { alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) } },
  server: {
    port: 5173,
    strictPort: true,
    allowedHosts,
    proxy: { '/api': { target: backend, changeOrigin: false, xfwd: true } },
  },
  preview: {
    port: 4173,
    allowedHosts,
    proxy: { '/api': { target: backend, changeOrigin: false, xfwd: true } },
  },
});
