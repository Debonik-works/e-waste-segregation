import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/predict": "http://127.0.0.1:8080",
      "/latest": "http://127.0.0.1:8080",
      "/health": "http://127.0.0.1:8080",
      "/config": "http://127.0.0.1:8080",
      "/device-config": "http://127.0.0.1:8080",
      "/lan-info": "http://127.0.0.1:8080",
      "/events": {
        target: "http://127.0.0.1:8080",
        changeOrigin: true,
      },
    },
  },
});
