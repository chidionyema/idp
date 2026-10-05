import { chromium } from 'playwright';
const b = await chromium.launch({ channel:'chrome', headless:true });
const ctx = await b.newContext({ userAgent:'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1', viewport:{width:390,height:844}, isMobile:true, hasTouch:true });
const page = await ctx.newPage();
const seen = [];
page.on('response', async r => {
  const u = r.url();
  if (!/\.js(\?|$)/.test(u)) return;
  try { const t = await r.text(); if (/cache_hit_pct|EfficiencyHud|efficiency-hud/.test(t)) seen.push([u, t.length, t]); } catch {}
});
await page.goto('http://localhost:3100/fleet', {waitUntil:'networkidle', timeout:45000}).catch(()=>{});
for (const [u,len,t] of seen) {
  console.log('== CHUNK', u, len, 'bytes');
  const i = t.indexOf('cache_hit_pct');
  console.log('   has "complete"?', /complete/.test(t));
  console.log('   ctx:', t.slice(Math.max(0,i-260), i+220).replace(/\s+/g,' '));
}
if (!seen.length) console.log('no js chunk carried the HUD');
await b.close();
