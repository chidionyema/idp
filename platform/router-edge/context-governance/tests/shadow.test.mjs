import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { pathToFileURL } from 'node:url';

const moduleUrl = process.env.GOVERNOR_TS
  ? pathToFileURL(process.env.GOVERNOR_TS)
  : new URL('../ts/context-budget-middleware/index.ts', import.meta.url);
const { gateRouterIngress } = await import(moduleUrl.href);
const policy = JSON.parse(fs.readFileSync(new URL('../governance/context-policy.v1.json', import.meta.url)));

test('SHADOW preserves the request and sends no rotation command', async () => {
  const body = { model: 'glm-5.3-flash', messages: [{ role: 'user', content: 'x'.repeat(120000) }] };
  const before = JSON.stringify(body);
  const ledger = { getSession: async () => null, putSession: async () => {}, getMissionTotal: async () => 0 };
  const result = await gateRouterIngress(body, new Headers(), policy, ledger);
  assert.equal(result.allowed, true);
  assert.equal(result.status, 200);
  assert.equal(result.responseHeaders['X-Meridian-Context-Directive'], 'ALLOW');
  assert.equal(JSON.stringify(result.clampedBody), before);
});
