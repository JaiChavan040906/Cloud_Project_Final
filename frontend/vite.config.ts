import tailwindcss from "@tailwindcss/vite"
import react from "@vitejs/plugin-react"
import path from "path"
import { defineConfig } from "vite"

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: { "@": path.resolve(__dirname, "./src") },
  },
  server: {
    proxy: {
      "/api": "http://54.147.40.134:8000",
      "/auth": "http://54.147.40.134:8000",
      "/health": "http://54.147.40.134:8000",
    },
  },
})
