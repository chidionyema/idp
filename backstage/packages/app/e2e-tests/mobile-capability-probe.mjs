// Can this machine run a MOBILE browser at all, and what does the mic path look like there?
//
// This is the proof-of-capability for mobile test infra. It answers, by running:
//   1. does WebKit (iPhone) launch here, and does Chromium (Pixel) in mobile mode launch?
//   2. on each, does /fleet load, or is it bounced to the OCI login wall? (the 2026-04-10 defect)
//   3. on each, is getUserMedia reachable, and what error does the page show when it is refused?
//
// It does NOT claim the mic works -- it measures what the mobile engine actually does, which is
// the whole point: a desktop fake-flag result is not evidence about a phone.
import { webkit, chromium, devices } from 'playwright';

const URL = process.env.URL || 'https://catalogue.mumchimp.com/fleet';
const targets = [
  ['iPhone 13 (WebKit)', webkit, devices['iPhone 13']],
  ['Pixel 7 (Chromium)', chromium, devices['Pixel 7']],
];

for (const [label, engine, device] of targets) {
  const out = { label, url: URL };
  try {
    const browser = await engine.launch({ headless: true });
    const ctx = await browser.newContext({ ...device, permissions: ['microphone'] });
    const page = await ctx.newPage();

    await page.addInitScript(() => {
      window.__mic = { calls: [], sr: false };
      const md = navigator.mediaDevices;
      window.__mic.hasMediaDevices = !!md;
      window.__mic.hasGetUserMedia = !!(md && md.getUserMedia);
      // getUserMedia requires a secure context; record that too.
      window.__mic.isSecureContext = window.isSecureContext;
      if (md && md.getUserMedia) {
        const o = md.getUserMedia.bind(md);
        md.getUserMedia = async c => {
          const rec = { audio: !!(c && c.audio), ok: null, err: null };
          window.__mic.calls.push(rec);
          try { const s = await o(c); rec.ok = true;
            rec.tracks = s.getAudioTracks().map(t => ({ label: t.label, state: t.readyState }));
            return s;
          } catch (e) { rec.ok = false; rec.errName = e.name; rec.err = String(e.message); throw e; }
        };
      }
      window.__mic.sr = !!(window.SpeechRecognition || window.webkitSpeechRecognition);
    });

    const bad = [];
    page.on('response', r => { if (r.status() >= 400) bad.push(`${r.status()} ${r.url().slice(0, 110)}`); });

    await page.goto(URL, { waitUntil: 'domcontentloaded', timeout: 45000 });
    await page.waitForTimeout(6000);

    let pressed = false;
    for (const re of [/tap to talk/i, /tap me/i, /^talk$/i]) {
      try { await page.getByText(re).first().click({ timeout: 4000 }); pressed = true; break; } catch {}
    }
    await page.waitForTimeout(4000);

    out.finalUrl = page.url();
    out.bouncedToLogin = /oraclecloud\.com|identity\.oraclecloud|idcs-/.test(page.url());
    out.canvases = await page.$$eval('canvas', e => e.length).catch(() => 'n/a');
    out.pressedTalk = pressed;
    out.mic = await page.evaluate(() => window.__mic);
    out.badResponses = bad.slice(0, 5);
    out.bodyText = (await page.evaluate(() => document.body.innerText)).slice(0, 180);

    await browser.close();
  } catch (e) {
    out.launchError = `${e.name}: ${String(e.message).split('\n')[0]}`;
  }
  console.log(JSON.stringify(out, null, 2));
  console.log('---');
}
