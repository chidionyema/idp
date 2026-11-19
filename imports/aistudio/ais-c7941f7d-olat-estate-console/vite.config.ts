import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import fs from 'fs';
import path from 'path';
import {defineConfig} from 'vite';

export default defineConfig(() => {
  return {
    plugins: [
      react(),
      tailwindcss(),
      {
        name: 'genesis-health-routes',
        configureServer(server) {
          server.middlewares.use((req, res, next) => {
            if (req.url === '/healthz') {
              res.setHeader('Content-Type', 'application/json');
              res.statusCode = 200;
              res.end(
                JSON.stringify({
                  status: 'ok',
                  version: '1.0.26',
                  epoch: 'EPOCH-2026-1078-ERA1',
                  healthy: true,
                })
              );
              return;
            }
            if (req.url === '/readyz') {
              res.setHeader('Content-Type', 'application/json');
              res.statusCode = 200;
              res.end(
                JSON.stringify({
                  status: 'ready',
                  version: '1.0.26',
                  epoch: 'EPOCH-2026-1078-ERA1',
                  ready: true,
                })
              );
              return;
            }
            if (req.url === '/olat-estate-genesis-main.bundle') {
              const bundlePath = path.resolve(__dirname, 'public/olat-estate-genesis-main.bundle');
              if (fs.existsSync(bundlePath)) {
                res.setHeader('Content-Type', 'application/octet-stream');
                res.statusCode = 200;
                fs.createReadStream(bundlePath).pipe(res);
                return;
              }
            }
            next();
          });
        },
      },
    ],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, '.'),
      },
    },
    server: {
      // HMR is disabled in AI Studio via DISABLE_HMR env var.
      // Do not modify—file watching is disabled to prevent flickering during agent edits.
      hmr: process.env.DISABLE_HMR !== 'true',
      // Disable file watching when DISABLE_HMR is true to save CPU during agent edits.
      watch: process.env.DISABLE_HMR === 'true' ? null : {},
    },
  };
});
