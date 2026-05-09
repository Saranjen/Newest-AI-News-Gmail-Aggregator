import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/subscribe": { target: "http://127.0.0.1:8000", changeOrigin: true },
      "/demo": { target: "http://127.0.0.1:8000", changeOrigin: true },
      "/health": { target: "http://127.0.0.1:8000", changeOrigin: true },
    },
  },
  build: {
    // Local: repo-root `static/` for uvicorn. Vercel: `app/spa_dist/` so hashed assets ship inside the
    // Python bundle (repo-root `public/` is often CDN-only and missing from the serverless filesystem).
    outDir: process.env.VERCEL ? "../app/spa_dist" : "../static",
    emptyOutDir: true,
  },
});
