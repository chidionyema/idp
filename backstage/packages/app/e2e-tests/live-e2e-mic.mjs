import { chromium, devices } from 'playwright';
const URL = process.argv[2];
const b = await chromium.launch({ headless:true, channel:'chrome',
  args:['--use-fake-ui-for-media-stream','--use-fake-device-for-media-stream','--autoplay-policy=no-user-gesture-required'] });
const ctx = await b.newContext({ ...devices['Pixel 7'], permissions:['microphone'] });
const page = await ctx.newPage();
const appMic = [];   // every getUserMedia the APP itself makes
await page.exposeFunction('__note', () => {});
await page.addInitScript(() => {
  window.__appMic = [];
  const md = navigator.mediaDevices;
  if (md && md.getUserMedia) {
    const o = md.getUserMedia.bind(md);
    md.getUserMedia = async c => {
      const rec = { audio: !!(c&&c.audio), ok:null };
      window.__appMic.push(rec);
      try { const s = await o(c); rec.ok=true; rec.tracks=s.getAudioTracks().map(t=>({label:t.label,state:t.readyState})); return s; }
      catch(e){ rec.ok=false; rec.errName=e.name; rec.err=e.message; throw e; }
    };
  }
});
const errs=[]; page.on('pageerror',e=>errs.push(String(e.message).slice(0,140)));
await page.goto(URL,{waitUntil:'domcontentloaded',timeout:45000});
await page.waitForTimeout(5000);
const enter = page.getByRole('button',{name:/enter|guest|continue/i}).first();
if (await enter.count()) { await enter.click().catch(()=>{}); await page.waitForTimeout(4000); }
console.log('url        :', page.url());
console.log('secure     :', await page.evaluate(()=>window.isSecureContext));
// click the app's own mic control
const mic = page.locator('[data-testid*=mic i]').first();
const n = await page.locator('[data-testid*=mic i]').count();
console.log('mic ctrls  :', n);
if (n) {
  await mic.click({ timeout: 8000 }).catch(e=>console.log('click err:', String(e.message).slice(0,90)));
  await page.waitForTimeout(6000);
}
const calls = await page.evaluate(()=>window.__appMic);
console.log('app getUserMedia calls:', JSON.stringify(calls));
console.log('body after :', (await page.locator('body').innerText()).replace(/\s+/g,' ').slice(0,240));
console.log('pageerrors :', errs.length?errs.slice(0,2):'none');
await b.close();
