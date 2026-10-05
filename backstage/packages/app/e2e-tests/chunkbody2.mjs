import { chromium } from 'playwright';
const b = await chromium.launch({ channel:'chrome', headless:true });
const ctx = await b.newContext({ userAgent:'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1', viewport:{width:390,height:844}, isMobile:true, hasTouch:true });
const page = await ctx.newPage();
let txt=null; const all=[];
page.on('response', async r => {
  if (!/\.js(\?|$)/.test(r.url())) return;
  try { const t = await r.text(); if (t.includes('useEfficiencyFrame')) { all.push(r.url()); if(!txt) txt=t; } } catch {}
});
await page.route('**/efficiency*', r => r.fulfill({ status:200, contentType:'application/json',
  body: JSON.stringify({ error:{name:'Auth',message:'x'}, request:{}, response:{statusCode:401} }) }));
await page.goto('http://localhost:3100/fleet', {waitUntil:'load', timeout:60000});
for (const re of [/^Enter$/i,/enter as a guest/i]) { try{ await page.getByRole('button',{name:re}).first().click({timeout:5000}); break;}catch{} }
await page.waitForTimeout(11000);
console.log('chunks with hook:', all);
if (txt) {
  const i = txt.indexOf('function useEfficiencyFrame');
  console.log('\n=== BUNDLED HOOK (900 chars) ===');
  console.log(txt.slice(i, i+1900).replace(/\\n/g,' ').replace(/\s+/g,' '));
}
await b.close();
