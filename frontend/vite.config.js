import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  server: {
    // Bind to all interfaces so other machines on the LAN can open the app via
    // http://<host-ip>:5173 (Vite prints the network URLs on startup).
    host: true,
    // Dev: forward /api to the Django dev server so requests stay same-origin
    // (no CORS, shared CSRF cookie) — mirrors the nginx prod setup. Proxying is
    // server-side, so LAN clients still work: they call :5173 and Django is
    // reached on localhost from this machine.
    //
    // changeOrigin stays false: Django's CSRF middleware compares the request's
    // Origin header to request.get_host(), and rewriting the Host to localhost
    // breaks that check whenever the app is opened via the LAN IP (host !=
    // localhost). ALLOWED_HOSTS=["*"] makes the passed-through Host acceptable.
    proxy: {
      '/api': { target: 'http://localhost:8000', changeOrigin: false },
    },
  },
})