import path from "path"
import tailwindcss from "@tailwindcss/vite"
import react from "@vitejs/plugin-react"
import { defineConfig } from "vite"

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
  },
  server: {
    proxy: {
      "/api": {
        target: "http://localhost:8004",
        changeOrigin: true,
      },
    },
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          "vendor-react": ["react", "react-dom", "@base-ui/react"],
          "vendor-router": ["@tanstack/react-router", "@tanstack/react-router-devtools"],
          "vendor-query": ["@tanstack/react-query", "axios"],
          "vendor-state": ["zustand", "nuqs"],
          "vendor-ui": ["react-resizable-panels", "sonner", "class-variance-authority", "clsx", "tailwind-merge"],
        },
      },
    },
  },
})
