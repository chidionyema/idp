import { chromium } from 'playwright';
const b = await chromium.launch({ channel:'chrome', headless:true });
const ctx = await b.newContext({
  userAgent:'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
  viewport:{width:390,height:844}, isMobile:true, hasTouch:true });
const page = await ctx.newPage();
page.on('pageerror', e => console.log('STACK:\n'+String(e.stack||e).split('\n').slice(0,4).join('\n')));
await page.addInitScript(() => {
  Object.defineProperty(navigator,'mediaDevices',{configurable:true,get:()=>undefined});
});
// Log EVERY /efficiency response body so we see the real frame shape
await page.route('**/*', async route => {
  const u = route.request().url();
  if (/efficiency|\/n\?|\/n$/.test(u)) {
    console.log('REQ:', u.slice(0,120));
    try { const r = await route.fetch(); const body = await r.text();
      console.log('  ->', r.status(), body.slice(0,200)); await route.fulfill({response:r, body}); }
    catch(e){ console.log('  fetch err', String(e).slice(0,80)); await route.continue(); }
    return;
  }
  await route.continue();
});
await page.goto(process.argv[2], {waitUntil:'load', timeout:60000});
for (const re of [/^Enter$/i,/enter as a guest/i]) {
  try { await page.getByRole('button',{name:re}).first().click({timeout:5000}); break; } catch {}
}
await page.waitForTimeout(12000);
await b.close();
