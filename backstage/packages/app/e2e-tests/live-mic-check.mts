// Live /fleet and /face microphone probe, in the real browser.
//
// WHY. The estate kept "verifying" the mic with probes that never called getUserMedia, and then
// read a macOS refusal as the founder's cause when the founder was on a phone. This drives a real
// browser against the live site, records every getUserMedia call and its exact outcome, and prints
// the network/console errors so a failure names itself.
//
// HONESTY. This runs system Chrome on macOS -- the only engine installed on this laptop (Playwright
// ships no WebKit or Chromium for macOS 13). It is evidence about desktop Chrome on the live site.
// It is NOT evidence about an iPhone: that needs WebKit in CI (playwright.mobile.config.ts).
import { chromium } from 'playwright';

const URL = process.argv[2] || 'https://catalogue.mumchimp.com/fleet';

const browser = await chromium.launch({
  channel: 'chrome', // system Chrome is the only browser on this laptop
  headless: true,
  args: [
    '--use-fake-ui-for-media-stream',
    '--use-fake-device-for-media-stream',
    '--autoplay-policy=no-user-gesture-required',
  ],
});
const ctx = await browser.newContext({ permissions: ['microphone'] });
const page = await ctx.newPage();

await page.addInitScript(() => {
  const w = window as any;
  w.__m = {
    secure: window.isSecureContext,
    hasMediaDevices: !!navigator.mediaDevices,
    hasGetUserMedia: !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia),
    calls: [],
  };
  const md = navigator.mediaDevices;
  if (md && md.getUserMedia) {
    const orig = md.getUserMedia.bind(md);
    md.getUserMedia = async (c: MediaStreamConstraints) => {
      const rec: any = { audio: !!(c && c.audio) };
      w.__m.calls.push(rec);
      try {
        const s = await orig(c);
        rec.ok = true;
        rec.tracks = s.getAudioTracks().map((t: MediaStreamTrack) => t.label);
        return s;
      } catch (e: any) {
        rec.ok = false;
        rec.err = `${e?.name}: ${e?.message}`;
        throw e;
      }
    };
  }
});

const bad: string[] = [];
page.on('response', r => {
  if (r.status() >= 400) bad.push(`${r.status()} ${r.url().slice(0, 100)}`);
});
page.on('console', m => {
  if (m.type() === 'error') bad.push(`console: ${m.text().slice(0, 130)}`);
});

await page.goto(URL, { waitUntil: 'domcontentloaded', timeout: 45_000 });
await page.waitForTimeout(7_000);

console.log('finalUrl:', page.url());

// Backstage's own sign-in gate comes first: a signed-out browser sees "Enter as a Guest User"
// with an Enter button, and the app does not mount until it is pressed. The 2026-10-04 measurement
// that showed 0 canvases had skipped this, so the probe -- not the page -- was what never reached
// the mic. Press it the way a person does, then look for the mic.
let entered = false;
for (const re of [/^Enter$/i, /enter as a guest/i, /^Enter as a Guest User\.?$/i]) {
  try {
    await page.getByRole('button', { name: re }).first().click({ timeout: 5_000 });
    entered = true;
    break;
  } catch {
    /* next shape */
  }
}
await page.waitForTimeout(8_000);

let tapped = false;
for (const re of [/tap to talk/i, /tap me/i, /^talk$/i, /start listening/i]) {
  try {
    await page.getByText(re).first().click({ timeout: 4_000 });
    tapped = true;
    break;
  } catch {
    /* next shape */
  }
}
// The page's own mic button, by the testid its own test uses (fleet-mic). The text patterns above
// are a guess and a guess is not a measurement: this is the element the page actually exposes.
let clickedMic = false;
try {
  await page.getByTestId('fleet-mic').first().click({ timeout: 5_000 });
  clickedMic = true;
} catch {
  /* not mounted, or named otherwise -- reported, not assumed */
}
await page.waitForTimeout(5_000);

console.log('entered:', entered);
console.log('tapped:', tapped, 'clickedMicTestid:', clickedMic);
console.log('canvasesAfterEnter:', await page.$$eval('canvas', e => e.length).catch(() => 'n/a'));
console.log('mic:', JSON.stringify(await page.evaluate(() => (window as any).__m)));
console.log('bad:', JSON.stringify([...new Set(bad)].slice(0, 8)));
console.log('bodyText:', (await page.evaluate(() => document.body.innerText)).slice(0, 200).replace(/\n+/g, ' | '));

await browser.close();
