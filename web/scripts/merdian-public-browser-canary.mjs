#!/usr/bin/env node
/**
 * Independent customer-visible visual canary. Unlike candidate screenshots,
 * this visits the real public aliases and renders the approved premium DOM.
 * It never submits contact forms or handles customer information.
 *
 * Run: CHROME=/usr/bin/google-chrome node scripts/merdian-public-browser-canary.mjs
 */
import { existsSync, mkdirSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import puppeteer from 'puppeteer-core';

export const PUBLIC_ORIGINS = [
  'https://merdian-intelligence.vercel.app',
  'https://meridian-intelligence-uk.vercel.app',
  'https://merian-intelligence.vercel.app',
];
const output = path.join(path.dirname(dirname(fileURLToPath(import.meta.url))), 'artifacts', 'public-readback');
mkdirSync(output, { recursive: true });
const chrome = process.env.CHROME || '/usr/bin/google-chrome';
const viewports = [390, 1440];
const results = [];
const failures = [];
let browser;
try {
  if (!existsSync(chrome)) throw new Error(`Chrome is unavailable: ${chrome}`);
  browser = await puppeteer.launch({
    executablePath: chrome,
    headless: true,
    args: ['--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu'],
  });
  for (const origin of PUBLIC_ORIGINS) {
    const hostname = new URL(origin).hostname;
    for (const width of viewports) {
      const page = await browser.newPage();
      try {
        await page.setViewport({ width, height: 900, deviceScaleFactor: 1, isMobile: width <= 430, hasTouch: width <= 430 });
        await page.setCacheEnabled(false);
        const response = await page.goto(origin + '/?ui_canary=' + Date.now(), { waitUntil: 'domcontentloaded', timeout: 30000 });
        if (!response || !response.ok()) throw new Error('Homepage HTTP ' + (response?.status() ?? 'missing'));
        await page.evaluate(() => document.fonts.ready);
        const result = await page.evaluate(({ width }) => {
          const errors = [];
          const hero = document.querySelector('.mi-hero');
          const h1 = document.querySelector('.mi-hero-title');
          const header = document.querySelector('.mi-header');
          const footer = document.querySelector('.mi-footer');
          const main = document.querySelector('main#main');
          const label = h1?.textContent?.replace(/\\s+/g, ' ').trim() ?? '';
          const visible = el => {
            if (!el) return false;
            const r = el.getBoundingClientRect();
            const s = getComputedStyle(el);
            return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none';
          };
          if (!hero || !h1 || !header || !footer || !main) errors.push('approved premium landmarks missing');
          if (!visible(hero) || !visible(h1)) errors.push('premium homepage hero not visible');
          if (!/INTELLIGENCE/i.test(label) || !/MADE/i.test(label) || !/REAL/i.test(label)) errors.push('premium brand headline missing');
          if (document.documentElement.scrollWidth > innerWidth + 4) errors.push('horizontal document overflow');
          const heroRect = hero?.getBoundingClientRect();
          if (heroRect && (heroRect.left < -4 || heroRect.right > innerWidth + 4)) errors.push('hero extends beyond viewport');
          const bg = hero ? getComputedStyle(hero).backgroundColor.match(/[0-9]+/g)?.slice(0, 3).map(Number) : null;
          if (!bg || bg.length < 3 || Math.max(...bg) > 70) errors.push('premium dark hero colour absent');
          if (!document.querySelector('a[href="/consulting"]') || !document.querySelector('a[href="/research"]') || !document.querySelector('a[href="/products"]')) {
            errors.push('company pillars missing from customer navigation');
          }
          if (width <= 430) {
            const menu = document.querySelector('.mi-menu-toggle');
            if (!visible(menu) || menu.getBoundingClientRect().height < 44) errors.push('mobile menu inaccessible');
          }
          return { headline: label.slice(0, 140), width, rgb: bg, problems: errors };
        }, { width });
        if (width <= 430 && !result.problems.length) {
          const menu = await page.$('.mi-menu-toggle');
          if (menu) {
            await menu.click();
            const expanded = await page.$eval('.mi-menu-toggle', el => el.getAttribute('aria-expanded'));
            const links = await page.$$eval('#mi-mobile-nav a', els => els.length);
            if (expanded !== 'true' || links < 4) result.problems.push('mobile menu did not open navigable company links');
            await menu.click();
          }
        }
        await page.screenshot({ path: path.join(output, hostname + '-' + width + '.jpg'), type: 'jpeg', quality: 67, fullPage: false });
        results.push({ origin, ...result });
        failures.push(...result.problems.map(p => `${hostname} ${width}px: ${p}`));
      } catch (error) {
        failures.push(`${hostname} ${width}px: ${error instanceof Error ? error.message : String(error)}`);
      } finally {
        await page.close();
      }
    }
  }
} catch (error) {
  failures.push('visual canary unavailable: ' + (error instanceof Error ? error.message : String(error)));
} finally {
  await browser?.close();
}
console.log(JSON.stringify({ at: new Date().toISOString(), inspected: results.length, failures, evidence: results }, null, 2));
if (failures.length) {
  console.error('MERDIAN PUBLIC BROWSER REGRESSION — ' + failures.join('; '));
  process.exitCode = 1;
} else {
  console.log('MERDIAN PUBLIC BROWSER READBACK: PASS — all 3 aliases at 390 and 1440px');
}
