/* DIAGNOSTIC ONLY (#5560) -- draft PR, never merged. Why does iPhone reach "listening" with 0 getUserMedia calls? */
import { test } from '@playwright/test';
test('diag /fleet', async ({ page, context }) => {
  await context.grantPermissions(['microphone'], { origin: new URL(process.env.PLAYWRIGHT_URL ?? 'https://catalogue.mumchimp.com').origin });
  const logs: string[] = [];
  page.on('console', m => logs.push(`[${m.type()}] ${m.text().slice(0, 200)}`));
  page.on('pageerror', e => logs.push(`[pageerror] ${e.message.slice(0, 200)}`));
  page.on('framenavigated', f => f === page.mainFrame() && logs.push(`[nav] ${f.url()}`));
  await page.addInitScript(() => {
    const w = window as any;
    w.__d = { inits: (w.__d?.inits ?? 0) + 1, own: 0, proto: 0, ctx: [] as any[], at: Date.now() };
    const P = (window as any).MediaDevices?.prototype;
    if (P && P.getUserMedia) {
      const o = P.getUserMedia;
      P.getUserMedia = function (c: any) { w.__d.proto++; return o.call(this, c).then((s: any) => { w.__d.ok = s.getAudioTracks().map((t: any) => t.readyState); return s; }, (e: any) => { w.__d.err = e.name + ': ' + e.message; throw e; }); };
    }
    const md = navigator.mediaDevices;
    if (md) { const g = md.getUserMedia; md.getUserMedia = function (c: any) { w.__d.own++; return g.call(md, c); }; }
    const AC = (window as any).AudioContext;
    if (AC) (window as any).AudioContext = class extends AC { constructor(...a: any[]) { super(...a); w.__d.ctx.push(this); } };
  });
  await page.goto('/fleet', { waitUntil: 'load' });
  const enter = page.getByRole('button', { name: /enter/i });
  const mic = page.getByTestId('fleet-mic');
  await enter.or(mic).first().waitFor({ timeout: 60_000 });
  if (await enter.isVisible().catch(() => false)) await enter.first().click();
  await mic.first().waitFor({ timeout: 60_000 });
  console.log('before-reload ' + await page.evaluate(() => JSON.stringify({ inits: (window as any).__d?.inits, md: !!navigator.mediaDevices, own: Object.prototype.hasOwnProperty.call(navigator.mediaDevices || {}, 'getUserMedia') })));
  await page.reload({ waitUntil: 'load' });
  console.log('after-reload ' + await page.evaluate(() => JSON.stringify({ d: !!(window as any).__d, inits: (window as any).__d?.inits, md: !!navigator.mediaDevices, own: Object.prototype.hasOwnProperty.call(navigator.mediaDevices || {}, 'getUserMedia') })));
  await mic.first().waitFor({ timeout: 90_000 });
  await mic.first().click();
  for (let i = 0; i < 25; i++) {
    const s = await page.evaluate(() => {
      const w = window as any;
      return JSON.stringify({ inits: w.__d.inits, own: w.__d.own, proto: w.__d.proto, ok: w.__d.ok, err: w.__d.err, ctx: w.__d.ctx.map((c: any) => c.state + '@' + c.sampleRate), vadLoaded: !!w.vad, title: document.querySelector('[data-testid="fleet-mic"]')?.getAttribute('title') });
    });
    console.log(`t=${i}s ${s}`);
    if (i > 6 && s.includes('listening')) break;
    await page.waitForTimeout(1000);
  }
  console.log(logs.filter(l => !/\[(debug|log)\].*(three|THREE|webgl)/i.test(l)).slice(-40).join('\n'));
});
