import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
import { viteSingleFile } from 'vite-plugin-singlefile';
import { fileURLToPath } from 'node:url';

// The kit gallery: every component in every state, every template with sample data, both themes.
// Built as one HTML file so it can sit behind the portal (or be published) with no server.
export default defineConfig({
  root: fileURLToPath(new URL('.', import.meta.url)),
  plugins: [react(), tailwindcss(), viteSingleFile()],
  build: { outDir: fileURLToPath(new URL('../dist-gallery', import.meta.url)), emptyOutDir: true },
});
