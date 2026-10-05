// Verify the refusal wording contract against the REAL source, in a real Chrome on the live origin.
// The three rules the founder set (mobile-shell.test.ts): never a Settings/padlock chore, never
// blame https on an https page, always name the microphone.
import { chromium, devices } from 'playwright';
const URL = process.argv[2];
const FORBID = /Settings|padlock|chrome:\/\/settings/i;
const b = await chromium.launch({ headless:true, channel:'chrome',
  args:['--use-fake-ui-for-media-stream','--use-fake-device-for-media-stream'] });
const ctx = await b.newContext({ ...devices['iPhone 13'], permissions:['microphone'] });
const page = await ctx.newPage();
await page.goto(URL, { waitUntil:'domcontentloaded', timeout:45000 });
await page.waitForTimeout(4000);
const enter = page.getByRole('button',{name:/enter|guest|continue/i}).first();
if (await enter.count()) { await enter.click().catch(()=>{}); await page.waitForTimeout(4000); }
// Read what the page would say, by asking the same query the source asks.
const probe = await page.evaluate(async () => {
  const r = { secure: window.isSecureContext, hasMd: !!(navigator.mediaDevices?.getUserMedia) };
  try { r.state = (await navigator.permissions.query({name:'microphone'})).state; }
  catch(e){ r.state = 'THREW ' + e.name; }
  return r;
});
console.log('page origin state:', JSON.stringify(probe));
// the strings the source now produces, read straight from source
import { readFileSync } from 'node:fs';
const src = readFileSync('packages/app/src/modules/home/useEstateVoice.ts','utf8');
for (const label of ['siteSettingFix','osRefusalFix']) {
  const i = src.indexOf(`function ${label}()`);
  const body = src.slice(i, src.indexOf('\n}', i));
  const strs = [...body.matchAll(/return '(.*?)'/g)].map(m=>m[1]);
  for (const s of strs) {
    const ok = !FORBID.test(s) && !/not on https/i.test(s) && /microphone|mic/i.test(s);
    console.log(`${ok?'PASS':'FAIL'} ${label}: "${s}"`);
  }
}
await b.close();
