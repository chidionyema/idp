import { defineConfig } from 'astro/config';
import react from '@astrojs/react';
import cloudflare from '@astrojs/cloudflare';
import tailwindcss from '@tailwindcss/vite';

// Static by default: the output is files on Cloudflare's free tier (ADR 0034 rung 4), 0 CPU on the
// node. Switch `output` to 'server' only for a route that must run code.
export default defineConfig({
  site: process.env.SITE_URL ?? 'https://__NAME__.example',
  output: 'static',
  adapter: cloudflare(),
  integrations: [react()],
  vite: { plugins: [tailwindcss()] },
});
