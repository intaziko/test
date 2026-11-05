import { resolve } from "node:path";
import { defineConfig } from "vite";

// Dos páginas independientes: Mapa 1 (index.html) y Mapa 2 (ruta.html). base "./" permite servir dist/ desde cualquier carpeta.
export default defineConfig({
  base: "./",
  build: {
    target: "es2022",
    chunkSizeWarningLimit: 1500,
    rollupOptions: { input: { index: resolve(import.meta.dirname, "index.html"), ruta: resolve(import.meta.dirname, "ruta.html"), finde: resolve(import.meta.dirname, "finde.html") } },
  },
  server: { host: true, port: 5173 },
  preview: { host: true, port: 4173 },
});
