import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import path from 'path';
import {defineConfig, type Plugin} from 'vite';

function genesisBundleSyncPlugin(): Plugin {
  let scheduledTimer: ReturnType<typeof setTimeout> | null = null;
  let running = false;

  const triggerSync = (delayMs: number, trigger: 'vite_boot' | 'file_watch') => {
    if (scheduledTimer) clearTimeout(scheduledTimer);
    scheduledTimer = setTimeout(async () => {
      if (running) return;
      running = true;
      try {
        const {pushBundleToIngest} = await import('./src/engine/debugPackBuilder');
        await pushBundleToIngest(process.cwd(), {timeoutMs: 4500, trigger});
      } catch {
        // Non-blocking background sync: never crash Vite/Express dev server
      } finally {
        running = false;
      }
    }, delayMs);
    if (typeof scheduledTimer.unref === 'function') {
      scheduledTimer.unref();
    }
  };

  return {
    name: 'genesis-bundle-sync',
    configureServer(server) {
      // Runs automatically on every npm run dev / container boot without LLM intervention
      triggerSync(10000, 'vite_boot');
      server.watcher?.on('change', (changedPath: string) => {
        if (
          changedPath.includes(`${path.sep}dist-exports${path.sep}`) ||
          changedPath.includes(`${path.sep}.git${path.sep}`) ||
          changedPath.includes(`${path.sep}dist${path.sep}`)
        ) {
          return;
        }
        triggerSync(1800, 'file_watch');
      });
    },
  };
}

export default defineConfig(() => {
  return {
    plugins: [react(), tailwindcss(), genesisBundleSyncPlugin()],
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

