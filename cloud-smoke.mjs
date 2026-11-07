import assert from 'node:assert/strict';
import { chromium } from 'playwright';

const base = process.argv[2];
assert(base, 'usage: cloud-smoke.mjs https://founder.example');

const modules = [
  ['otto', 'Otto — Universal Agent with Hands'],
  ['idp', 'Gateway & Protocol Cockpit'],
  ['optimus', 'Measured estate evidence'],
  ['omega', 'Omega Codex'],
];

const browser = await chromium.launch({ headless: true });
try {
  for (const [route, expected] of modules) {
    const page = await browser.newPage();
    const pageErrors = [];
    const httpErrors = [];
    page.on('pageerror', (error) => pageErrors.push(String(error)));
    page.on('response', (response) => {
      if (response.url().startsWith(base) && response.status() >= 400) {
        httpErrors.push(`${response.status()} ${response.url()}`);
      }
    });

    await page.goto(`${base}/#${route}`, {
      waitUntil: 'domcontentloaded',
      timeout: 20_000,
    });
    await page.getByText(expected, { exact: false }).first().waitFor({
      state: 'visible',
      timeout: 20_000,
    });
    const text = await page.locator('body').innerText();
    assert.equal(pageErrors.length, 0, `#${route} page errors: ${pageErrors.join('; ')}`);
    assert.equal(httpErrors.length, 0, `#${route} HTTP errors: ${httpErrors.join('; ')}`);
    assert.doesNotMatch(text, /check that the Genesis app is running on your Mac/i);
    assert.doesNotMatch(text, /stream offline/i);
    assert.doesNotMatch(text, /Start the local One-Brain server/i);
    assert.doesNotMatch(text, /Edge hub: offline/i);
    console.log(`ok #${route} rendered ${JSON.stringify(expected)}`);
    await page.close();
  }

  const page = await browser.newPage();
  const state = await page.request.get(`${base}/api/brain/state`);
  assert.equal(state.status(), 200);
  const body = await state.json();
  assert.equal(body.alwaysOnHome, 'cloudflare-pages');
  assert.equal(body.laptopMayBeRequired, false);
  const evidence = await page.request.get(`${base}/api/brain/optimus/evidence?limit=5`);
  assert.equal(evidence.status(), 200);
  const evidenceBody = await evidence.json();
  assert.equal(evidenceBody.writable, false);
  assert.ok(Array.isArray(evidenceBody.records));
  console.log('ok cloud APIs report Cloudflare authority and no Mac dependency');
} finally {
  await browser.close();
}
