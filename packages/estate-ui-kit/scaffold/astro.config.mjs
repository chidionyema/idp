import { defineConfig } from 'astro/config';
import react from '@astrojs/react';
import tailwindcss from '@tailwindcss/vite';

// Static: the output is files, served by Cloudflare's free tier (ADR 0034 rung 4) through
// wrangler.jsonc's `assets`, 0 CPU on the node. A route that must run code adds @astrojs/cloudflare
// and `output: 'server'`; nothing here needs it.
export default defineConfig({
  site: process.env.SITE_URL ?? 'https://__NAME__.example',
  output: 'static',
  integrations: [react()],
  vite: { plugins: [tailwindcss()] },
});
