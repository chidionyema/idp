import { chromium, devices } from 'playwright';
const URL = process.argv[2];
const b = await chromium.launch({ headless: true, channel: 'chrome' });
const ctx = await b.newContext({
  ...devices['Pixel 7'],
  permissions: ['microphone'],
  args: ['--use-fake-ui-for-media-stream','--use-fake-device-for-media-stream'],
});
const page = await ctx.newPage();
const errs = [];
page.on('pageerror', e => errs.push(String(e.message).slice(0,160)));
page.on('console', m => { if (m.type()==='error') errs.push('console: '+m.text().slice(0,140)); });
await page.goto(URL, { waitUntil: 'domcontentloaded', timeout: 45000 });
await page.waitForTimeout(5000);
console.log('URL       :', page.url());
console.log('secure    :', await page.evaluate(()=>window.isSecureContext));
// pass the guest gate
const enter = page.getByRole('button', { name: /enter|guest|continue/i }).first();
if (await enter.count()) { await enter.click().catch(()=>{}); await page.waitForTimeout(4000); }
console.log('after gate:', page.url());
// find the talk/mic control
const sels = ['[data-testid*=mic i]','[data-testid*=talk i]','button[aria-label*=mic i]','button[aria-label*=talk i]','[class*=mic i]','button:has-text("Talk")'];
let found=null;
for (const s of sels) { const c = page.locator(s); if (await c.count()) { found = s+` (${await c.count()})`; break; } }
console.log('mic ctrl  :', found || 'NONE FOUND');
// call getUserMedia directly on the live origin
const g = await page.evaluate(async () => {
  try {
    const md = navigator.mediaDevices;
    if (!md || !md.getUserMedia) return { ok:false, why:'no mediaDevices' };
    const s = await md.getUserMedia({ audio:true });
    const t = s.getAudioTracks().map(x=>({label:x.label,state:x.readyState}));
    s.getTracks().forEach(x=>x.stop());
    return { ok:true, tracks:t };
  } catch (e) { return { ok:false, name:e.name, msg:String(e.message).slice(0,140) }; }
});
console.log('getUserMedia:', JSON.stringify(g));
console.log('pageerrors :', errs.length ? errs.slice(0,3) : 'none');
await b.close();
