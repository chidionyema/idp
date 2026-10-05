import { chromium } from 'playwright';
const b = await chromium.launch({ channel:'chrome', headless:true });
const ctx = await b.newContext({
  userAgent:'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
  viewport:{width:390,height:844}, isMobile:true, hasTouch:true });
const page = await ctx.newPage();
page.on('pageerror', e => {
  console.log('=== PAGE ERROR ===');
  console.log(String(e.stack || e).slice(0, 1500));
});
await page.goto(process.argv[2], {waitUntil:'load', timeout:60000});
await page.waitForTimeout(4000);
for (const re of [/^Enter$/i,/enter as a guest/i]) {
  try { await page.getByRole('button',{name:re}).first().click({timeout:5000}); break; } catch {}
}
await page.waitForTimeout(9000);
console.log('=== url:', page.url());
await b.close();
