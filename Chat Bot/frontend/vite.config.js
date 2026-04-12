import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  build: {
    lib: {
      entry: "src/main.jsx",
      name: "OrientExpress",
      fileName: "orient-express",
      formats: ["iife"],
    },
    rollupOptions: {
      output: {
        assetFileNames: "orient-express.[ext]",
        inlineDynamicImports: true,
      },
    },
    cssCodeSplit: false,
    outDir: "dist",
  },
  define: {
    "process.env.NODE_ENV": JSON.stringify("production"),
  },
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
