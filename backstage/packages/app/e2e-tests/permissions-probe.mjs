import { chromium, devices, webkit } from 'playwright';
const URL = process.argv[2] || 'https://catalogue.mumchimp.com/fleet';
const out = {};
const b = await chromium.launch({ headless:true, channel:'chrome' });
for (const dev of ['iPhone 13','Pixel 7']) {
  const ctx = await b.newContext({ ...devices[dev] });
  const p = await ctx.newPage();
  await p.goto(URL, { waitUntil:'domcontentloaded', timeout:45000 });
  await p.waitForTimeout(3000);
  out[dev] = await p.evaluate(async () => {
    const r = { ua: navigator.userAgent.slice(0,60), hasPerm: !!navigator.permissions };
    if (navigator.permissions) {
      try { const q = await navigator.permissions.query({name:'microphone'}); r.mic = q.state; }
      catch(e){ r.mic = 'THREW: ' + e.name + ' ' + String(e.message).slice(0,60); }
    }
    r.secure = window.isSecureContext;
    r.md = !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia);
    return r;
  });
  await ctx.close();
}
console.log(JSON.stringify(out, null, 2));
await b.close();
