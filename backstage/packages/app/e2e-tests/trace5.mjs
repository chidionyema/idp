import { chromium } from 'playwright';
const b = await chromium.launch({ channel:'chrome', headless:true });
const ctx = await b.newContext({ userAgent:'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1', viewport:{width:390,height:844}, isMobile:true, hasTouch:true });
const page = await ctx.newPage();
const hudModules = [];
page.on('response', async r => {
  const u = r.url();
  if (/EfficiencyHud/i.test(u)) hudModules.push(u);
});
await page.goto('http://localhost:3100/fleet', {waitUntil:'networkidle', timeout:45000}).catch(()=>{});
console.log('HUD MODULE URLS:');
for (const u of [...new Set(hudModules)]) console.log('  ', u);
await b.close();
