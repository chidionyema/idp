// crew#857: reads the feature register and plan from the ConfigMap mounted
// at /app/feature-register/ and serves them over two endpoints.
// Re-reads on every request, so a ConfigMap update takes effect immediately
// without a pod restart (estate admission requires workloads to reload
// configuration on their own).
//
//   GET /api/feature-register/register  → features.yaml (text/yaml)
//   GET /api/feature-register/plan      → plan.json (application/json)
//
// Both return 503 Service Unavailable when the files are not found
// (development / compose environment without the ConfigMap).
import { createBackendPlugin, coreServices } from '@backstage/backend-plugin-api';
import { Router } from 'express';
import fs from 'fs/promises';

const REGISTER_PATH = '/app/feature-register/features.yaml';
const PLAN_PATH = '/app/feature-register/plan.json';

async function serveFile(res: any, path: string, contentType: string): Promise<void> {
  try {
    const text = await fs.readFile(path, 'utf-8');
    res.status(200);
    res.contentType(contentType);
    res.send(text);
  } catch (err: any) {
    res.status(503);
    res.contentType('application/json');
    res.send(JSON.stringify({
      error: 'feature-register not available',
      detail: `Cannot read ${path}: ${err.message ?? String(err)}`,
    }));
  }
}

export const featureRegisterPlugin = createBackendPlugin({
  pluginId: 'feature-register',
  register(reg) {
    reg.registerInit({
      deps: {
        httpRouter: coreServices.httpRouter,
        logger: coreServices.logger,
      },
      async init({ httpRouter, logger }) {
        const router = Router();

        router.get('/register', (_req, res) => {
          serveFile(res, REGISTER_PATH, 'text/yaml; charset=utf-8');
        });

        router.get('/plan', (_req, res) => {
          serveFile(res, PLAN_PATH, 'application/json; charset=utf-8');
        });

        httpRouter.use(router);
        logger.info('feature-register plugin mounted at /api/feature-register/');
      },
    });
  },
});

export default featureRegisterPlugin;