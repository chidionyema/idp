import { chromium } from 'playwright-core';
const b = await chromium.launch({ executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless: true });
const p = await b.newPage({ viewport: { width: 1440, height: 900 } });
const errs=[]; p.on('pageerror', e=>errs.push('PE: '+e.message.slice(0,200)));
await p.goto('http://localhost:3100/fleet', { waitUntil:'commit', timeout:12000 });
await p.waitForTimeout(6000);
const w = await p.$('button:has-text("Enter")'); if (w) { await w.click(); await p.waitForTimeout(14000); }
const r = await p.evaluate(() => ({
  title: document.querySelector('h1')?.innerText,
  canvas: document.querySelectorAll('canvas').length,
  sonar: [...document.querySelectorAll('button')].map(b=>b.textContent.trim()).filter(Boolean),
}));
console.log(JSON.stringify(r));
console.log('errors:', errs.slice(0,3));
await b.close();
