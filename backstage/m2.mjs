import { chromium } from 'playwright-core';
const b = await chromium.launch({ executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless: true });
const p = await b.newPage({ viewport: { width: 1440, height: 900 } });
const errs=[]; p.on('pageerror', e=>errs.push(e.message.slice(0,140)));
p.on('console', m => { if (m.type()==='error') errs.push('CONSOLE: '+m.text().slice(0,110)); });
await p.goto('http://localhost:3100/fleet', { waitUntil: 'domcontentloaded', timeout: 30000 });
await p.waitForTimeout(6000);
const w = await p.$('button:has-text("Enter")'); if (w) { await w.click(); await p.waitForTimeout(16000); }
const pos = await p.evaluate(() => { const c=document.querySelector('canvas'); const r=c.getBoundingClientRect(); return {x:r.x,y:r.y,w:r.width,h:r.height}; });
let f=false;
for (let gy=0.12; gy<=0.92 && !f; gy+=0.06) for (let gx=0.05; gx<=0.96 && !f; gx+=0.04) {
  await p.mouse.click(pos.x+pos.w*gx, pos.y+pos.h*gy); await p.waitForTimeout(120);
  f = await p.evaluate(() => !!document.querySelector('[data-testid="radial-menu"]'));
}
await p.click('[data-testid="mind-trace"]');
for (let i=0;i<8;i++) {
  await p.waitForTimeout(600);
  const t = await p.evaluate(() => document.querySelector('[data-testid="mind-trace-body"]')?.textContent?.trim() || null);
  if (t) { console.log(`at ${i*600}ms: "${t}"`); break; }
  if (i===7) console.log('NEVER APPEARED — panel buttons:', await p.evaluate(()=>Array.from(document.querySelectorAll('[data-testid="mind-panel"] button')).map(b=>b.textContent.trim())));
}
console.log('errors:', errs.slice(0,3));
await b.close();
