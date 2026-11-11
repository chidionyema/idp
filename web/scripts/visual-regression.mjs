#!/usr/bin/env node
// Fail-closed browser quality check: customer pages, critical interactions and mobile geometry.
// Requires Puppeteer Core and an installed Chrome/Chromium executable.
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { existsSync, mkdirSync } from "node:fs";
import { setTimeout as sleep } from "node:timers/promises";
import { fileURLToPath } from "node:url";
import path from "node:path";
import puppeteer from "puppeteer-core";

const root = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const port = 3112;
const base = `http://127.0.0.1:${port}`;
const chrome = process.env.CHROME || "/usr/bin/google-chrome";
const viewports = [320, 390, 768, 1440];
const routes = ["/", "/research", "/writing/agentic-routing-for-enterprise", "/contact"];
const failures = [];
const outDir = path.join(root, "artifacts", "visual");
mkdirSync(outDir, { recursive: true });

async function waitForServer() {
  for (let attempt = 0; attempt < 80; attempt++) {
    try {
      const response = await fetch(base, { signal: AbortSignal.timeout(1000) });
      if (response.ok) return;
    } catch { /* still starting */ }
    await sleep(350);
  }
  throw new Error("Next.js production server failed to start for visual inspection");
}

async function inspect(page, route, width) {
  return page.evaluate(({ route, width }) => {
    const failures = [];
    const visible = element => {
      const style = getComputedStyle(element);
      const box = element.getBoundingClientRect();
      return style.visibility !== "hidden" && style.display !== "none" && box.width > 0 && box.height > 0;
    };
    if (document.documentElement.scrollWidth > innerWidth + 3) {
      failures.push("document horizontal overflow: " + document.documentElement.scrollWidth + " > " + innerWidth);
    }
    for (const element of document.querySelectorAll("h1,h2,h3,p,a,button,input,textarea,.mi-qa-panel,.mi-qa-theme,.mi-footer-links")) {
      // Skip links are correctly positioned off-screen until keyboard focus.
      if (element.classList.contains("skip-link") && document.activeElement !== element) continue;
      if (!visible(element)) continue;
      const box = element.getBoundingClientRect();
      const style = getComputedStyle(element);
      if (box.left < -4 || box.right > innerWidth + 4) {
        failures.push(element.tagName + "." + String(element.className).slice(0,40) + " extends outside viewport");
      }
      if (element.matches("button,input,textarea") && style.fontSize && parseFloat(style.fontSize) < 12) {
        failures.push("interactive control with unreadable font");
      }
    }

    const header = document.querySelector(".mi-header");
    const footer = document.querySelector(".mi-footer");
    const main = document.querySelector("#main");
    if (!header || !footer || !main) failures.push("missing site landmark");
    const h1 = document.querySelector("main h1");
    if (!h1 || !visible(h1)) failures.push("missing visible page heading");

    if (width <= 768) {
      const menu = document.querySelector(".mi-menu-toggle");
      if (!menu || !visible(menu)) failures.push("mobile navigation toggle missing");
      else if (menu.getBoundingClientRect().height < 44) failures.push("mobile menu touch target smaller than 44px");
    }
    if (route === "/") {
      const body = document.body.textContent ?? "";
      if (/Blabka|More information will be shared|Further details will be published/.test(body)) {
        failures.push("public placeholder content was rendered");
      }
      for (const anchor of document.querySelectorAll('a[href^="/"]')) {
        if (anchor.textContent?.includes("↗")) failures.push("internal link uses external arrow: " + anchor.getAttribute("href"));
      }
      const markers = [
        ["01 / MANIFESTO", document.querySelector(".mi-manifesto .mi-eyebrow")],
        ["02 / CONSULTANCY", document.querySelector(".mi-services .mi-eyebrow")],
        ["03 / THE LABORATORY", document.querySelector(".mi-lab .mi-eyebrow")],
        ["04 / VENTURES + PRODUCTS", document.querySelector(".mi-ventures .mi-eyebrow")],
      ];
      for (const [expected, el] of markers) {
        if (!el?.textContent?.includes(expected)) failures.push("section numbering drift: " + expected);
      }
      const luminance = rgb => {
        const v = rgb.match(/\d+(?:\.\d+)?/g)?.slice(0, 3).map(Number);
        if (!v || v.length !== 3) return 0;
        const c = v.map(x => { const n=x/255; return n<=.04045 ? n/12.92 : ((n+.055)/1.055)**2.4; });
        return .2126*c[0]+.7152*c[1]+.0722*c[2];
      };
      for (const selector of [".mi-manifesto", ".mi-services", ".mi-ventures"]) {
        const section=document.querySelector(selector);
        const eyebrow=section?.querySelector(".mi-eyebrow");
        if (!section || !eyebrow) { failures.push("contrast landmark absent: "+selector); continue; }
        const bg=luminance(getComputedStyle(section).backgroundColor);
        const fg=luminance(getComputedStyle(eyebrow).color);
        const ratio=(Math.max(bg,fg)+.05)/(Math.min(bg,fg)+.05);
        if (ratio<4.5) failures.push(selector+" eyebrow contrast "+ratio.toFixed(2)+":1 below WCAG AA");
      }
      for (const selector of [".mi-hero-title", ".mi-close h2"]) {
        const el=document.querySelector(selector);
        if (!el) continue;
        const style=getComputedStyle(el);
        const spacing=parseFloat(style.letterSpacing) / parseFloat(style.fontSize);
        if (Number.isFinite(spacing) && spacing<-.055) failures.push(selector+" letter-spacing crushes word boundaries");
      }
      const art=document.querySelector(".mi-hero-art");
      const ring=art?.querySelector(".mi-orbit-outer")?.getBoundingClientRect();
      const top=art?.querySelector(".mi-art-label-top")?.getBoundingClientRect();
      const bottom=art?.querySelector(".mi-art-label-bottom")?.getBoundingClientRect();
      const buttons=[...document.querySelectorAll(".mi-hero-actions .mi-button")];
      const intersects=(a,b)=> a.left<b.right && a.right>b.left && a.top<b.bottom && a.bottom>b.top;
      if (!ring || !top || !bottom) failures.push("hero orbital graphic labels missing");
      else {
        for (const [label,r] of [["upper",top],["lower",bottom]]) {
          if (width<=850 && intersects(r,ring)) failures.push(label+" orbital label intersects outer diagram");
          if (r.right>innerWidth+2 || r.left<0) failures.push(label+" orbital caption clipped at viewport");
        }
        if (width<=850 && buttons.some(button=>intersects(button.getBoundingClientRect(),ring))) {
          failures.push("orbital geometry intersects a hero action on mobile/tablet");
        }
      }
      if (width<=620) {
        if (buttons.length!==2 || buttons[1].getBoundingClientRect().top < buttons[0].getBoundingClientRect().bottom-2) {
          failures.push("mobile hero actions are not full-width stacked");
        }
      }
    }
    if (route === "/research") {
      const workspace = document.querySelector(".mi-qa-workspace");
      const input = document.querySelector("#mi-research-question");
      const sidebar = document.querySelector(".mi-qa-sidebar");
      const panel = document.querySelector(".mi-qa-panel");
      if (!workspace || !input || !sidebar || !panel) failures.push("research desk missing");
      else {
        const ib = input.getBoundingClientRect();
        const sb = sidebar.getBoundingClientRect();
        const pb = panel.getBoundingClientRect();
        if (ib.width < 185) failures.push("research search input collapsed to " + Math.round(ib.width) + "px");
        if (width <= 768 && pb.top < sb.bottom - 5) failures.push("research panel did not stack below form");
        if (pb.right > innerWidth + 3) failures.push("research panel extends beyond viewport");
      }
    }
    if (route.startsWith("/writing/")) {
      const body = document.querySelector(".mi-article-body");
      if (!body || !visible(body)) failures.push("article content missing");
      else if (parseFloat(getComputedStyle(body.querySelector("p")).fontSize) < 16) failures.push("article body text below 16px");
    }
    if (route === "/contact" && !document.querySelector(".mi-contact-form input[type=email]")) {
      if (!document.body.textContent?.includes("Online enquiries are paused.")) {
        failures.push("contact must show a form or an explicit delivery-unavailable state");
      }
    }
    return { route, width, failures };
  }, { route, width });
}

let server;
let browser;
try {
  assert.ok(existsSync(path.join(root, ".next", "BUILD_ID")), "run npm run build before browser QA");
  assert.ok(existsSync(chrome), `Chrome executable not found: ${chrome}`);
  server = spawn(process.execPath, ["node_modules/next/dist/bin/next", "start", "--port", String(port)], {
    cwd: root,
    stdio: "ignore",
    env: { ...process.env, NODE_ENV: "production", CONTACT_WEBHOOK_URL: "" },
  });
  await waitForServer();
  browser = await puppeteer.launch({
    executablePath: chrome,
    headless: true,
    args: ["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
  });
  for (const width of viewports) {
    const page = await browser.newPage();
    await page.setViewport({ width, height: 900, deviceScaleFactor: 1, isMobile: width <= 430, hasTouch: width <= 430 });
    for (const route of routes) {
      const response = await page.goto(base + route, { waitUntil: "networkidle2", timeout: 30000 });
      if (!response || !response.ok()) {
        failures.push(`${width}px ${route}: HTTP ${response?.status() ?? "none"}`);
        continue;
      }
      await page.evaluate(() => document.fonts.ready);
      if (route === "/contact") {
        await page.waitForFunction(() => !document.body.textContent?.includes("Checking availability."), { timeout: 6000 });
      }
      const report = await inspect(page, route, width);
      failures.push(...report.failures.map(f => `${width}px ${route}: ${f}`));
      await page.screenshot({
        path: path.join(outDir, `${route.replaceAll("/", "_") || "home"}-${width}.png`),
        fullPage: true,
      });
      if (route === "/research" && width === 390) {
        const suggestion = await page.$(".mi-qa-suggestion");
        assert.ok(suggestion, "research suggestions missing");
        await suggestion.click();
        const selected = await page.$eval("#mi-research-question", el => el.value);
        if (!selected.includes("SPIFFE")) failures.push("research suggestion did not fill the query");
        await page.click(".mi-qa-input-row button");
        try {
          await page.waitForSelector(".mi-qa-source a, a.mi-qa-source", { timeout: 9000 });
        } catch {
          failures.push("research question did not resolve to a linked published source");
        }
      }
      if (route === "/" && width === 390) {
        await page.click(".mi-menu-toggle");
        try {
          await page.waitForSelector("#mi-mobile-nav a", { timeout: 2500 });
        } catch {
          failures.push("mobile menu did not open");
        }
      }
    }
    await page.close();
  }
  if (failures.length) {
    console.error("VISUAL REGRESSION FAILURES:\n" + failures.join("\n"));
    process.exitCode = 1;
  } else {
    console.log(`PASS: ${routes.length} customer pages × ${viewports.length} viewports, including mobile navigation and research query`);
  }
} catch (error) {
  console.error("Browser QA aborted:", error);
  process.exitCode = 1;
} finally {
  await browser?.close();
  server?.kill("SIGTERM");
}
