import assert from 'node:assert/strict';
import { mkdirSync, existsSync } from 'node:fs';
import { resolve, join } from 'node:path';
import { createRequire } from 'node:module';
import { pathToFileURL } from 'node:url';

export const widths = [320, 375, 768, 1000, 1001, 1440];
export const scenes = ['MONDAY / 09:00', 'WEDNESDAY / 14:00', 'FRIDAY / 16:00'];
export function checkPage(s, route, width) {
  assert.equal(s.status, 200, `${route}: expected HTTP 200`);
  assert.equal(s.pathname, route, `${route}: unexpected redirect`);
  assert.equal(s.headings, 1, `${route}: expected one visible h1`);
  assert.ok(s.landmarks, `${route}: missing landmarks`);
  assert.ok(s.scrollWidth <= width + 3, `${route}: document overflow`);
  assert.deepEqual(s.clipped, [], `${route}: clipped visible controls/text`);
  if (route === '/investors') {
    assert.ok(s.investor && s.chronosLink && s.contactLink, 'investor journey incomplete');
    assert.ok(s.investorDisclosure && !s.privateEffectLinks, 'public investor boundary violated');
  } else if (route === '/products/chronos') {
    assert.ok(s.chronos && s.concept && s.disclaimer && s.investorLink, 'Chronos concept boundary/journey missing');
  }
}
export function checkScene(s, index) {
  assert.deepEqual(s.pressed, scenes.map((_, i) => i === index ? 'true' : 'false'));
  assert.equal(s.time, scenes[index]);
  assert.ok(s.heading && s.example && s.disclosed && s.live === 'polite', 'walkthrough content or accessible announcement missing');
}
export function checkContact(s, allowed) {
  assert.equal(s.form, allowed, 'contact PII form must be gated by positive availability');
  assert.equal(s.paused, !allowed, 'contact state is not explicit');
}

// These run in the real browser. No fixture-based success is a release receipt.
export function pageSnapshot() {
  const visible = e => !!e && e.getClientRects().length > 0 && getComputedStyle(e).visibility !== 'hidden' && getComputedStyle(e).display !== 'none';
  const links = [...document.querySelectorAll('main a[href]')];
  const hasLink = href => links.some(e => e.getAttribute('href') === href && visible(e));
  const text = document.querySelector('main')?.innerText ?? '';
  const clipped = [...document.querySelectorAll('main h1,main h2,main h3,main p,main a,main button,.mi-nav a,.mi-menu-toggle')].filter(e => {
    if (!visible(e)) return false;
    const b = e.getBoundingClientRect();
    return b.left < -4 || b.right > innerWidth + 4 || e.clientWidth > 0 && e.scrollWidth > e.clientWidth + 4 && getComputedStyle(e).overflowX !== 'visible';
  }).map(e => `${e.tagName}:${(e.innerText ?? '').trim().slice(0, 40)}`);
  return { pathname: location.pathname, headings: [...document.querySelectorAll('main h1')].filter(visible).length,
    landmarks: !!document.querySelector('header nav') && !!document.querySelector('main') && !!document.querySelector('footer'),
    scrollWidth: document.documentElement.scrollWidth, clipped,
    investor: visible(document.querySelector('.mi-investor-page')), chronos: visible(document.querySelector('.mi-chronos-page')),
    chronosLink: hasLink('/products/chronos'), contactLink: hasLink('/contact?topic=investor'), investorLink: hasLink('/investors'),
    investorDisclosure: /not an offer to invest/i.test(text),
    privateEffectLinks: links.some(e => /\/investors\/(?:room|private)|\/api\/|genesis-founder|\/admin/i.test(e.getAttribute('href') ?? '')),
    concept: visible(document.querySelector('.mi-chronos-concept-badge')), disclaimer: /not a live service or measured customer outcome/i.test(text) };
}
export function sceneSnapshot() {
  const scene = document.querySelector('.mi-chronos-scene');
  return { pressed: [...document.querySelectorAll('.mi-chronos-step')].map(e => e.getAttribute('aria-pressed')),
    time: scene?.querySelector('.mi-eyebrow')?.textContent?.trim(), heading: scene?.querySelector('h3')?.textContent?.trim(),
    example: scene?.querySelector('.mi-chronos-scene-example p')?.textContent?.trim(),
    disclosed: /NOT LIVE COMPANY DATA/.test(scene?.textContent ?? ''), live: scene?.getAttribute('aria-live') };
}
export function contactSnapshot() {
  return { form: !!document.querySelector('.mi-contact-form input[type=email]'),
    paused: /Online enquiries are paused\./.test(document.body.innerText) };
}

async function run() {
  const base = new URL(process.env.MERIDIAN_QA_ORIGIN || 'http://127.0.0.1:3112');
  assert.ok(['127.0.0.1', 'localhost', '[::1]'].includes(base.hostname) && base.protocol === 'http:', 'fixture interception is restricted to a local candidate server');
  assert.equal(base.pathname, '/');
  const root = resolve(process.env.MERIDIAN_WEB_ROOT || 'web');
  assert.ok(existsSync(join(root, '.next', 'BUILD_ID')), 'build the exact admitted candidate first');
  const require = createRequire(join(root, 'package.json'));
  const puppeteer = require('puppeteer-core');
  const output = resolve(process.env.MERIDIAN_QA_ARTIFACTS || join(root, 'artifacts', 'investor-qa'));
  mkdirSync(output, { recursive: true });
  const browser = await puppeteer.launch({ executablePath: process.env.CHROME || '/usr/bin/google-chrome', headless: true,
    args: ['--no-sandbox', '--disable-dev-shm-usage'] });
  try {
    for (const width of widths) {
      const page = await browser.newPage();
      const pageErrors = [];
      page.on('pageerror', error => pageErrors.push(String(error)));
      await page.setViewport({ width, height: 900, deviceScaleFactor: 1 });
      async function open(route) {
        const response = await page.goto(new URL(route, base).href, { waitUntil: 'networkidle2', timeout: 30000 });
        await page.evaluate(() => document.fonts.ready);
        return response?.status();
      }
      assert.equal(await open('/'), 200);
      if (width <= 1000) {
        await page.click('.mi-menu-toggle');
        await page.waitForSelector('#mi-mobile-nav a[href="/investors"]', { visible: true });
        await page.keyboard.press('Escape');
        await page.waitForSelector('#mi-mobile-nav', { hidden: true });
        await page.click('.mi-menu-toggle');
        await page.click('#mi-mobile-nav a[href="/investors"]');
      } else {
        await page.click('.mi-nav-links a[href="/investors"]');
      }
      await page.waitForFunction(() => location.pathname === '/investors' && !!document.querySelector('.mi-investor-page'));
      const investorStatus = await open('/investors');
      checkPage({ ...await page.evaluate(pageSnapshot), status: investorStatus }, '/investors', width);
      await page.screenshot({ path: join(output, `investors-${width}.png`), fullPage: true });
      await page.click('main a[href="/products/chronos"]');
      await page.waitForFunction(() => location.pathname === '/products/chronos' && !!document.querySelector('.mi-chronos-page'));
      const status = await open('/products/chronos');
      checkPage({ ...await page.evaluate(pageSnapshot), status }, '/products/chronos', width);
      for (const index of [0, 1, 2, 0]) {
        const selector = `.mi-chronos-step:nth-child(${index + 1})`;
        await page.focus(selector);
        await page.keyboard.press('Enter');
        await page.waitForFunction(i => document.querySelectorAll('.mi-chronos-step')[i]?.getAttribute('aria-pressed') === 'true', {}, index);
        checkScene(await page.evaluate(sceneSnapshot), index);
      }
      await page.screenshot({ path: join(output, `chronos-${width}.png`), fullPage: true });
      assert.deepEqual(pageErrors, [], 'uncaught browser exceptions');
      await page.close();
    }
    for (const fixture of [
      { status: 200, body: '{"acceptingEnquiries":false}', allowed: false },
      { status: 200, body: '{"acceptingEnquiries":"true"}', allowed: false },
      { status: 200, body: 'not json', allowed: false },
      { status: 503, body: '{"acceptingEnquiries":true}', allowed: false },
      { abort: true, allowed: false },
      { status: 200, body: '{"acceptingEnquiries":true}', allowed: true },
    ]) {
      const page = await browser.newPage();
      let posts = 0;
      await page.setRequestInterception(true);
      page.on('request', request => {
        const u = new URL(request.url());
        if (u.origin === base.origin && u.pathname === '/api/contact') {
          if (request.method() !== 'GET') { posts++; void request.abort(); return; }
          if (fixture.abort) { void request.abort(); return; }
          void request.respond({ status: fixture.status, contentType: 'application/json', body: fixture.body }); return;
        }
        void request.continue();
      });
      const response = await page.goto(new URL('/contact?topic=investor', base).href, { waitUntil: 'networkidle2' });
      assert.equal(response?.status(), 200);
      await page.waitForFunction(() => !document.body.innerText.includes('Checking availability.'));
      checkContact(await page.evaluate(contactSnapshot), fixture.allowed);
      assert.equal(posts, 0, 'unexpected contact write');
      await page.close();
    }
    console.log('PASS: candidate browser journeys and local contact readiness falsifiers; NOT actual delivery or deployment proof');
  } finally { await browser.close(); }
}
if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  await run();
}
