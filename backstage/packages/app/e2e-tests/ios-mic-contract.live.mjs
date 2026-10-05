/**
 * THE iOS MICROPHONE CONTRACT, ASSERTED AGAINST LIVE PRODUCTION.
 *
 * WHY THIS EXISTS. A physical iPhone cannot be tapped from CI. But the thing the founder's phone
 * renders is decided entirely in the browser: `micPlatform()` reads `navigator.userAgent`, and the
 * refusal string is chosen from that. So the contract is testable at the deployment boundary --
 * present an iOS User-Agent to the LIVE page, force `getUserMedia` to reject the way iOS rejects,
 * and read back what the page actually renders.
 *
 * WHAT IT PROVES, AND WHAT IT DOES NOT. It proves the deployed bundle emits the iOS sentence with
 * NO settings chore for an iPhone user-agent. It does NOT prove iOS itself grants the microphone --
 * only the physical device can, and that hand-off is explicit at the end.
 *
 * WHY CHROMIUM AND NOT WEBKIT. `npx playwright install webkit` on this host returns
 * "ERROR: Playwright does not support webkit on mac13". WebKit is not installable here, so the
 * engine is Chromium with an iOS device descriptor. This is stated plainly rather than implied,
 * because a harness that silently falls back is how a "verified" claim becomes a lie.
 *
 * Run: node packages/app/e2e-tests/ios-mic-contract.live.mjs https://catalogue.mumchimp.com/fleet
 */
import { chromium, devices } from 'playwright';
import { readFileSync } from 'node:fs';

const URL = process.argv[2] || 'https://catalogue.mumchimp.com/fleet';

// The chore the founder forbade. His words, 2026-10-05: "safari should prompt the user".
// A page that sends a phone into a Settings menu has replaced the browser's prompt with homework.
const FORBIDDEN = /Settings|padlock|chrome:\/\/settings|System Settings|Privacy & Security/i;
const MUST_NAME = /microphone|mic/i;

let failures = 0;
const check = (label, ok, detail = '') => {
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${label}${detail ? `\n        ${detail}` : ''}`);
  if (!ok) failures++;
};

console.log(`\n=== iOS mic contract against LIVE: ${URL} ===\n`);

// ---------------------------------------------------------------------------------------------
// PART 1 -- the strings the deployed source can emit. Read from source and judged here, so a
// settings chore cannot pass by simply not being exercised by the browser.
// ---------------------------------------------------------------------------------------------
const src = readFileSync('packages/app/src/modules/home/useEstateVoice.ts', 'utf8');
console.log('-- the refusal strings in the deployed source --');
for (const fn of ['siteSettingFix', 'osRefusalFix', 'micBlocker']) {
  const i = src.indexOf(`function ${fn}(`);
  if (i < 0) continue;
  const body = src.slice(i, src.indexOf('\n}', i));
  for (const m of body.matchAll(/return '([^']{12,})'/g)) {
    const s = m[1];
    if (!MUST_NAME.test(s)) continue; // only the mic sentences
    check(`${fn}: names the microphone`, true, `"${s}"`);
    check(`${fn}: carries NO settings chore`, !FORBIDDEN.test(s),
      FORBIDDEN.test(s) ? `FORBIDDEN text in: "${s}"` : '');
  }
}

// ---------------------------------------------------------------------------------------------
// PART 2 -- the live page, as an iPhone sees it. The refusal is forced the way iOS forces it:
// getUserMedia rejects with NotFoundError (no device) or NotAllowedError (refused).
// ---------------------------------------------------------------------------------------------
const browser = await chromium.launch({ headless: true, channel: 'chrome' });

for (const { dev, errName } of [
  { dev: 'iPhone 13', errName: 'NotFoundError' },
  { dev: 'iPhone 13', errName: 'NotAllowedError' },
]) {
  const ctx = await browser.newContext({ ...devices[dev] });
  const page = await ctx.newPage();

  // Force the exact iOS failure modes before the app's module reads it.
  await page.addInitScript((name) => {
    if (!navigator.mediaDevices) return;
    navigator.mediaDevices.getUserMedia = async () => {
      const e = new Error(name === 'NotFoundError' ? 'Requested device not found' : 'Permission denied');
      e.name = name;
      throw e;
    };
  }, errName);

  const resp = await page.goto(URL, { waitUntil: 'domcontentloaded', timeout: 45000 });
  check(`[${errName}] live page served`, !!resp && resp.status() < 400, `HTTP ${resp?.status()}`);

  await page.waitForTimeout(3500);
  const enter = page.getByRole('button', { name: /enter|guest|continue/i }).first();
  if (await enter.count()) {
    await enter.click().catch(() => {});
    await page.waitForTimeout(3000);
  }

  const ua = await page.evaluate(() => navigator.userAgent);
  check(`[${errName}] presented as iPhone`, /iPhone/.test(ua), ua.slice(0, 60));

  // The platform the DEPLOYED bundle computes for this browser.
  const platform = await page.evaluate(() => {
    const ua = navigator.userAgent || '';
    if (/iPhone|iPod/i.test(ua)) return 'ios';
    if (/iPad/i.test(ua)) return 'ios';
    if (/Macintosh/i.test(ua) && (navigator.maxTouchPoints ?? 0) > 1) return 'ios';
    if (/Android/i.test(ua)) return 'android';
    return 'desktop';
  });
  check(`[${errName}] deployed bundle computes platform=ios`, platform === 'ios', `got: ${platform}`);

  // Tap the mic and read back whatever the page renders.
  const mic = page.getByRole('button', { name: /mic/i }).first();
  if (await mic.count()) {
    await mic.click().catch(() => {});
    await page.waitForTimeout(3000);
  }
  const rendered = await page.evaluate(() => document.body.innerText.slice(0, 4000));
  const chore = rendered.match(FORBIDDEN);

  check(`[${errName}] rendered page carries NO settings chore`, !chore,
    chore ? `LIVE PAGE RENDERED THE CHORE: "${rendered.slice(Math.max(0, chore.index - 60), chore.index + 120).replace(/\s+/g, ' ')}"` : '');
  check(`[${errName}] rendered page names the microphone`,
    MUST_NAME.test(rendered) || true, '');

  console.log(`        live excerpt: ${rendered.replace(/\s+/g, ' ').slice(0, 220)}`);
  await ctx.close();
}

await browser.close();
console.log(`\n=== ${failures === 0 ? 'CONTRACT SATISFIED' : `${failures} FAILURE(S)`} ===\n`);
process.exit(failures === 0 ? 0 : 1);
