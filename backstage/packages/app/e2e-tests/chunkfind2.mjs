import { chromium } from 'playwright';
const b = await chromium.launch({ channel:'chrome', headless:true });
const ctx = await b.newContext({ userAgent:'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1', viewport:{width:390,height:844}, isMobile:true, hasTouch:true });
const page = await ctx.newPage();
const seen = [];
page.on('response', async r => {
  const u = r.url();
  if (!/\.js(\?|$)/.test(u)) return;
  try { const t = await r.text();
    if (t.includes('cache_hit_pct')) seen.push([u, t.length, t]); } catch {}
});
await page.route('**/efficiency*', r => r.fulfill({ status:200, contentType:'application/json',
  body: JSON.stringify({ error:{name:'AuthenticationError',message:'login required'},
                         request:{method:'GET',url:'/fleetview/efficiency'},
                         response:{statusCode:401} }) }));
await page.goto('http://localhost:3100/fleet', {waitUntil:'load', timeout:60000});
for (const re of [/^Enter$/i,/enter as a guest/i]) {
  try { await page.getByRole('button',{name:re}).first().click({timeout:5000}); break; } catch {}
}
await page.waitForTimeout(13000);
console.log('chunks carrying cache_hit_pct:', seen.length);
for (const [u,len,t] of seen) {
  const i = t.indexOf('cache_hit_pct');
  console.log('== ', u, len, 'hasComplete:', /complete/.test(t));
  console.log('   ', t.slice(Math.max(0,i-300), i+200).replace(/\s+/g,' '));
}
await b.close();
