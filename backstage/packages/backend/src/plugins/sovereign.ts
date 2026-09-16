import { createBackendModule, coreServices } from '@backstage/backend-plugin-api';
import { Router } from 'express';
import fs from 'fs';
import path from 'path';

const sovereignPlugin = createBackendModule({
  pluginId: 'sovereign',
  register(reg) {
    reg.registerInit({
      deps: { http: coreServices.httpRouter },
      async init({ http }) {
        const router = Router();
        const artifactsDir = process.env.SOVEREIGN_ARTIFACTS_DIR ||
          path.join(__dirname, '../../../artifacts');

        // Serve intent DAG as JSON
        router.get('/intent.dag.json', (req, res) => {
          const filePath = path.join(artifactsDir, 'intent.dag.json');
          try {
            const content = fs.readFileSync(filePath, 'utf-8');
            res.setHeader('Content-Type', 'application/json');
            res.setHeader('Content-Disposition', 'attachment; filename="intent.dag.json"');
            res.send(content);
          } catch (err) {
            res.status(404).json({ error: 'intent.dag.json not found' });
          }
        });

        // Serve intent DAG as GraphViz DOT
        router.get('/intent.dag.dot', (req, res) => {
          const filePath = path.join(artifactsDir, 'intent.dag.dot');
          try {
            const content = fs.readFileSync(filePath, 'utf-8');
            res.setHeader('Content-Type', 'text/plain');
            res.setHeader('Content-Disposition', 'attachment; filename="intent.dag.dot"');
            res.send(content);
          } catch (err) {
            res.status(404).json({ error: 'intent.dag.dot not found' });
          }
        });

        // Serve drift report
        router.get('/drift-report.json', (req, res) => {
          const filePath = path.join(artifactsDir, 'drift-report.json');
          try {
            const content = fs.readFileSync(filePath, 'utf-8');
            res.setHeader('Content-Type', 'application/json');
            res.setHeader('Content-Disposition', 'attachment; filename="drift-report.json"');
            res.send(content);
          } catch (err) {
            res.status(404).json({ error: 'drift-report.json not found' });
          }
        });

        // Metadata endpoint
        router.get('/metadata', (req, res) => {
          res.json({
            name: 'sovereign-topology',
            version: '1.0.0',
            description: 'Infrastructure topology DAG with drift detection',
            exports: [
              { format: 'json', file: 'intent.dag.json', contentType: 'application/json' },
              { format: 'graphviz', file: 'intent.dag.dot', contentType: 'text/plain' },
              { format: 'drift-report', file: 'drift-report.json', contentType: 'application/json' },
            ],
          });
        });

        http.use('/api/sovereign', router);
      },
    });
  },
});

export default sovereignPlugin;
