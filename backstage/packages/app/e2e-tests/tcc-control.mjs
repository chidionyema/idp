import { chromium } from 'playwright';
const b = await chromium.launch({ headless: true, channel: 'chrome' });
const ctx = await b.newContext({ permissions: ['microphone'] });
const p = await ctx.newPage();
await p.goto('https://example.com', { waitUntil: 'domcontentloaded', timeout: 30000 });
const g = await p.evaluate(async () => {
  try { const s = await navigator.mediaDevices.getUserMedia({audio:true}); s.getTracks().forEach(t=>t.stop()); return {ok:true}; }
  catch(e){ return {ok:false,name:e.name,msg:e.message}; }
});
console.log('example.com (definitely secure) getUserMedia:', JSON.stringify(g));
await b.close();
