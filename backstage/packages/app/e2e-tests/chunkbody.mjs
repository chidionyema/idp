import { chromium } from 'playwright';
const b = await chromium.launch({ channel:'chrome', headless:true });
const ctx = await b.newContext({ userAgent:'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1', viewport:{width:390,height:844}, isMobile:true, hasTouch:true });
const page = await ctx.newPage();
let txt=null;
page.on('response', async r => { if (r.url().includes('FleetReactorApp_tsx.chunk.js')) { try{txt=await r.text();}catch{} }});
await page.goto('http://localhost:3100/fleet', {waitUntil:'load', timeout:60000});
await page.waitForTimeout(6000);
if (txt) {
  const i = txt.indexOf('function useEfficiencyFrame');
  console.log('=== BUNDLED useEfficiencyFrame BODY ===');
  console.log(txt.slice(i, i+1400).replace(/\\n/g,' ').replace(/\s+/g,' '));
}
await b.close();
