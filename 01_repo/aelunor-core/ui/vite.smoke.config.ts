// Wegwerf-Konfiguration für Browser-Verifikation gegen die LLM-freie Smoke-API.
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  base: "/v1/",
  plugins: [react()],
  server: {
    port: 5175,
    strictPort: true,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8077",
        changeOrigin: true,
      },
    },
  },
});
