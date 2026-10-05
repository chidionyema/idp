import { chromium } from 'playwright';
const b = await chromium.launch({ channel:'chrome', headless:true });
const ctx = await b.newContext({
  userAgent:'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
  viewport:{width:390,height:844}, isMobile:true, hasTouch:true });
const page = await ctx.newPage();
const errs=[];
page.on('pageerror', e => errs.push(String(e.stack||e).slice(0,2000)));
// EXACTLY what mobile-shell.test.ts does
await page.addInitScript(() => {
  Object.defineProperty(navigator,'mediaDevices',{configurable:true,get:()=>undefined});
});
await page.route('**/efficiency*', r=>r.fulfill({status:200,contentType:'application/json',
  body:JSON.stringify({since:'1h',error:'efficiency report not in this image',available:false})}));
await page.goto(process.argv[2], {waitUntil:'load', timeout:60000});
await page.waitForTimeout(4000);
for (const re of [/^Enter$/i,/enter as a guest/i]) {
  try { await page.getByRole('button',{name:re}).first().click({timeout:5000}); break; } catch {}
}
await page.waitForTimeout(10000);
console.log('url:', page.url());
console.log('errors:', errs.length);
for (const e of errs) console.log('---\n'+e);
const present = await page.$('[data-testid="fleet-mic"]');
console.log('fleet-mic present:', !!present);
await b.close();
