import { chromium } from 'playwright';
const b = await chromium.launch({ channel:'chrome', headless:true });
const ctx = await b.newContext({
  userAgent:'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
  viewport:{width:390,height:844}, isMobile:true, hasTouch:true });
const page = await ctx.newPage();
page.on('pageerror', e => {
  const s = String(e.stack||e);
  // print the FULL first frames incl. the source line reference
  console.log('ERR:', s.split('\n').slice(0,3).join(' | '));
});
// Make the /efficiency endpoint return exactly what prod returns: a 401-shaped error frame
await page.route('**/efficiency*', r => r.fulfill({ status:200, contentType:'application/json',
  body: JSON.stringify({ error:{name:'AuthenticationError',message:'login required'},
                         request:{method:'GET',url:'/fleetview/efficiency'},
                         response:{statusCode:401} }) }));
await page.addInitScript(() => {
  Object.defineProperty(navigator,'mediaDevices',{configurable:true,get:()=>undefined});
});
await page.goto('http://localhost:3100/fleet', {waitUntil:'load', timeout:60000});
for (const re of [/^Enter$/i,/enter as a guest/i]) {
  try { await page.getByRole('button',{name:re}).first().click({timeout:5000}); break; } catch {}
}
await page.waitForTimeout(12000);
const hud = await page.$('[data-testid="efficiency-hud"]');
console.log('efficiency-hud present:', !!hud);
if (hud) console.log('hud text:', (await hud.innerText()).replace(/\n+/g,' | ').slice(0,160));
console.log('fleet-mic present:', !!(await page.$('[data-testid="fleet-mic"]')));
await b.close();
