import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  base: "/v1/",
  plugins: [react()],
  server: {
    watch: {
      ignored: [
        "**/.runtime/**",
        "**/07_runtime/**",
        "**/.tmp-check/**",
        "**/dist/**",
        "**/public/brand/wallpapers/**",
      ],
    },
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8080",
        changeOrigin: true,
      },
    },
  },
});
