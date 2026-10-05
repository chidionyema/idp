import { chromium } from 'playwright';
const URL = process.argv[2];
const b = await chromium.launch({ channel:'chrome', headless:true,
  args:['--use-fake-ui-for-media-stream','--use-fake-device-for-media-stream'] });
const ctx = await b.newContext({
  userAgent:'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
  viewport:{width:390,height:844}, isMobile:true, hasTouch:true, permissions:['microphone'] });
const page = await ctx.newPage();

// THE EXACT STATE THE FAILING TEST FORCES: mediaDevices hidden.
await page.addInitScript(() => {
  Object.defineProperty(navigator,'mediaDevices',{configurable:true,get:()=>undefined});
});
page.on('pageerror', e => console.log('PAGEERROR:', String(e).slice(0,160)));
await page.route('**/efficiency*', r=>r.fulfill({status:200,contentType:'application/json',
  body:JSON.stringify({since:'1h',error:'not in image',available:false})}));

await page.goto(URL,{waitUntil:'load',timeout:60000});
await page.waitForTimeout(5000);
console.log('url:', page.url());

// press Enter like a person
for (const re of [/^Enter$/i,/enter as a guest/i]) {
  try { await page.getByRole('button',{name:re}).first().click({timeout:5000}); console.log('entered'); break; } catch {}
}
await page.waitForTimeout(8000);

const id='fleet-mic';
try { await page.getByTestId(id).first().click({timeout:20000}); console.log('clicked mic'); }
catch { console.log('mic not found'); }
await page.waitForTimeout(4000);

const out = await page.evaluate(x=>{
  const el=document.querySelector(`[data-testid="${x}"]`);
  return { present:!!el, title:el?.getAttribute('title')??'(none)',
           body:(document.body.innerText||'').replace(/\n+/g,' | ').slice(0,250) };
}, id);

const detail = out.title;
console.log('\n=== MEASURED ===');
console.log('mic present :', out.present);
console.log('TITLE       :', detail);
console.log('\n=== THE THREE ASSERTIONS FROM mobile-shell.test.ts:324 ===');
console.log('1 not /not on https/        :', !/not on https/i.test(detail) ? 'PASS' : 'FAIL');
console.log('2 not /Settings|padlock|chrome/ :', !/Settings|padlock|chrome:\/\/settings/i.test(detail) ? 'PASS' : 'FAIL');
console.log('3 matches /microphone|mic/i :', /microphone|mic/i.test(detail) ? 'PASS' : 'FAIL');
console.log('\n=== THE OLD DEFECT ===');
console.log('renders raw V8 TypeError    :', /Cannot read properties of undefined/.test(detail) ? 'STILL PRESENT (FAIL)' : 'GONE (fixed)');
await b.close();
