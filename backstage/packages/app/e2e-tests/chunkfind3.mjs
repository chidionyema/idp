import { chromium } from 'playwright';
const b = await chromium.launch({ channel:'chrome', headless:true });
const ctx = await b.newContext({ userAgent:'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1', viewport:{width:390,height:844}, isMobile:true, hasTouch:true });
const page = await ctx.newPage();
let txt=null;
page.on('response', async r => { if (r.url().includes('FleetReactorApp_tsx.chunk.js')) { try{txt=await r.text();}catch{} }});
await page.route('**/efficiency*', r => r.fulfill({ status:200, contentType:'application/json',
  body: JSON.stringify({ error:{name:'Auth',message:'x'}, request:{}, response:{statusCode:401} }) }));
await page.goto('http://localhost:3100/fleet', {waitUntil:'load', timeout:60000});
for (const re of [/^Enter$/i,/enter as a guest/i]) { try{ await page.getByRole('button',{name:re}).first().click({timeout:5000}); break;}catch{} }
await page.waitForTimeout(10000);
if (!txt) { console.log('no chunk'); } else {
  const i = txt.indexOf('normalizeFrame');
  console.log('normalizeFrame occurrences in served chunk:', (txt.match(/normalizeFrame/g)||[]).length);
  if (i>=0) console.log('CTX:', txt.slice(i-80, i+520).replace(/\s+/g,' '));
  // show the poll guard
  const j = txt.indexOf('available');
  if (j>=0) console.log('\nGUARD CTX:', txt.slice(j-260, j+220).replace(/\s+/g,' '));
}
await b.close();
