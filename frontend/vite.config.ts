import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/health": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
      "/score": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
      "/predict/applyhome-cutoff": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
      "/predict/applyhome-classify": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
});
