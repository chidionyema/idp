import { chromium } from 'playwright';
// Same call, but with the audio INPUT substituted so no OS device is opened at all.
// --use-fake-device-for-media-stream makes Chrome synthesize the audio; the OS mic is
// never touched. If this SUCCEEDS while the real device fails, the failure is the
// host's TCC mic permission for this process chain -- not the page, not the origin.
const b = await chromium.launch({
  headless: true, channel: 'chrome',
  args: ['--use-fake-ui-for-media-stream','--use-fake-device-for-media-stream'],
});
const ctx = await b.newContext({ permissions: ['microphone'] });
const p = await ctx.newPage();
await p.goto('https://example.com', { waitUntil:'domcontentloaded', timeout:30000 });
const g = await p.evaluate(async () => {
  try { const s = await navigator.mediaDevices.getUserMedia({audio:true});
        const t = s.getAudioTracks().map(x=>({label:x.label,state:x.readyState}));
        s.getTracks().forEach(x=>x.stop()); return {ok:true, tracks:t}; }
  catch(e){ return {ok:false,name:e.name,msg:e.message}; }
});
console.log('fake-device getUserMedia:', JSON.stringify(g));
await b.close();
