#!/usr/bin/env node
/** Browser-level commercial acceptance for the new Merdian Fieldbooks.
 * An unconfigured payment provider must never look like a live checkout.
 * Candidate tests neither collect customer data nor trigger a purchase.
 */
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { existsSync, mkdirSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { setTimeout as pause } from "node:timers/promises";
import puppeteer from "puppeteer-core";

const root = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const screenshots = path.join(root, "artifacts", "commerce");
const base = "http://127.0.0.1:3194";
const browserPath = process.env.CHROME || ["/usr/bin/google-chrome","/usr/bin/chromium"].find(existsSync);
const views = [320,390,768,1440];
const routes = ["/","/fieldbooks","/fieldbooks/from-prompt-to-proof"];
const failures = [];
mkdirSync(screenshots,{recursive:true});
assert.ok(browserPath && existsSync(browserPath), "Chromium required: no skipped browser acceptance");

let server; let browser;
async function ready() {
  for(let i=0;i<65;i++) {
    try { const r=await fetch(base,{signal:AbortSignal.timeout(1400)}); if(r.ok) return; } catch {}
    await pause(300);
  }
  throw new Error("Preview did not start");
}
try {
  assert.ok(existsSync(path.join(root,".next")), "Production build required before browser QA");
  server=spawn(process.execPath, ["node_modules/next/dist/bin/next","start","--port","3194","--hostname","127.0.0.1"],{cwd:root,env:{...process.env,NODE_ENV:"production"},stdio:"ignore"});
  await ready();
  browser=await puppeteer.launch({executablePath:browserPath,headless:true,args:["--no-sandbox","--disable-dev-shm-usage"]});
  for (const route of routes) {
    for (const width of views) {
      const page=await browser.newPage();
      page.on("pageerror", e=>failures.push(`${route} ${width}px runtime ${e.message}`));
      try {
        await page.setViewport({width,height:900,isMobile:width<=390,hasTouch:width<=390,deviceScaleFactor:1});
        const response=await page.goto(base+route,{waitUntil:"networkidle2",timeout:30000});
        assert.equal(response?.status(),200,route+" "+width+" status");
        await page.evaluate(()=>document.fonts.ready);
        const result=await page.evaluate(({route})=>{
          const errors=[];
          const title=document.querySelector("main h1");
          const style=title?getComputedStyle(title):null;
          const outer=document.documentElement.scrollWidth;
          if(!title || !style || style.visibility==="hidden" || style.display==="none") errors.push("main headline not visible");
          if(outer>innerWidth+4) errors.push(`horizontal overflow ${outer} > ${innerWidth}`);
          for(const item of document.querySelectorAll("main h1, main h2, main h3, main p, main a, main button")) {
            const rect=item.getBoundingClientRect();
            const s=getComputedStyle(item);
            if(s.visibility==="hidden"||s.display==="none"||rect.width===0) continue;
            if(rect.left < -5 || rect.right > innerWidth+5) errors.push(`${item.tagName} outside viewport`);
          }
          if(route==="/") {
            if(!document.querySelector(".mi-hero-title")) errors.push("approved homepage premium identity missing");
            if(!document.querySelector('main a[href="/fieldbooks"]')) errors.push("commerce route not discoverable from homepage");
          }
          if(route==="/fieldbooks") {
            if(!document.querySelector(".mi-knowledge-book")) errors.push("premium fieldbook art missing");
            if(!document.querySelector('a[href="/fieldbooks/from-prompt-to-proof"]')) errors.push("working free chapter route missing");
            if(document.querySelector('a[href*="gumroad.com"]')) errors.push("unconfigured live merchant claim");
            if(!document.body.textContent?.includes("MERCHANT CONNECTION PENDING")) errors.push("absent checkout is not disclosed");
          }
          if(route.includes("from-prompt")) {
            if(!document.body.textContent?.includes("Revoked-authority test")) errors.push("technical free chapter truncated");
            if(!document.body.textContent?.includes("Release-regression test")) errors.push("chapter acceptance suite missing");
          }
          return {errors,heading:title?.textContent?.replace(/\s+/g," ").slice(0,100)};
        },{route});
        failures.push(...result.errors.map(x=>route+" "+width+"px "+x));
        if(route==="/fieldbooks"&&width===390) {
          await page.click('a[href="/fieldbooks/from-prompt-to-proof"]');
          await page.waitForSelector(".mi-chapter-hero h1",{timeout:10000});
          const current=await page.evaluate(()=>location.pathname);
          assert.equal(current,"/fieldbooks/from-prompt-to-proof");
        }
        if(route==="/" && width===390) {
          await page.click(".mi-menu-toggle");
          const expanded=await page.$eval(".mi-menu-toggle", el=>el.getAttribute("aria-expanded"));
          assert.equal(expanded,"true","mobile menu did not expand");
          const hrefs=await page.$$eval("#mi-mobile-nav a", a=>a.map(el=>el.getAttribute("href")));
          assert.ok(hrefs.includes("/fieldbooks"),"mobile commerce link missing");
        }
        await page.screenshot({path:path.join(screenshots,route.replaceAll("/","_")||"_home")+"-"+width+".png",fullPage:false});
      } catch(error) {
        failures.push(route+" "+width+"px "+(error instanceof Error?error.message:String(error)));
      } finally { await page.close(); }
    }
  }
  assert.deepEqual(failures,[],"commercial UI rendered with defects");
  console.log("MERDIAN COMMERCIAL BROWSER ACCEPTANCE: PASS — 3 routes x 4 viewports + mobile navigation and free chapter");
} finally {
  await browser?.close();
  server?.kill("SIGTERM");
}
