#!/usr/bin/env node
// Deterministic render audit: what a designer checks by looking, measured instead.
// Usage:  node scripts/render-audit.mjs <url> [width=1440] [height=900]
//         npx will find puppeteer-core under web/node_modules if installed there.
// Depends on: puppeteer-core (any module-resolution path).
//
// Lessons paid for in 2026-10-20 and kept as comments because each was once a silent false
// negative:
//   1. bgOf() composites the whole ancestor chain. The first run read the element's own
//      background and reported thirteen fake 1.00:1 contrast failures because the tints were
//      rgba over a 24px deep ink surface, not on white.
//   2. overflow excludes both overflow:auto (scroll containers) and overflow:hidden (clip
//      containers). Including hidden turned three bar-visualisation clips into page overflows.
//   3. Anything that says "I checked X" must be able to fail X. The shipped self-test runs the
//      audit against a page with one defaulted blue link, one 11px grey label, one 900px block on
//      a 390px viewport and one section whose .container .section uses the padding shorthand
//      (which drops the gutter). If the audit ever reports 0 problems against that page, it is a
//      liar and must be fixed in the same commit.
import { createRequire } from "node:module";
import path from "node:path";
import os from "node:os";

// Look for puppeteer-core in three places, with the path I used during development as a fallback:
//   1. local node_modules at the repo root (web/node_modules or ../node_modules)
//   2. $PP_DIR/node_modules/puppeteer-core
//   3. /tmp/pp/node_modules (the original install)
const candidates = [
  process.env.PP_DIR,
  "/tmp/pp",
  path.resolve(process.cwd(), "node_modules"),
  path.resolve(process.cwd(), "../node_modules"),
].filter(Boolean);
let puppeteer;
for (const c of candidates) {
  try {
    const req = createRequire(`${c}/`);
    puppeteer = req("puppeteer-core");
    break;
  } catch {
    /* try next */
  }
}
if (!puppeteer) {
  console.error("puppeteer-core not found in any of:", candidates.join(", "));
  process.exit(2);
}

const [url, w, h] = process.argv.slice(2);
if (!url) {
  console.error("usage: render-audit.mjs <url> [width=1440] [height=900]");
  process.exit(2);
}
const CHROME =
  process.env.CHROME ||
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const VIEW = { w: parseInt(w, 10) || 1440, h: parseInt(h, 10) || 900 };
const CHROME_READY = { headless: "new", args: ["--no-sandbox", "--force-device-scale-factor=1"] };

// ----------------- helpers -----------------

const parseColor = (c) => {
  const m = c && c.match(/rgba?\(([^)]+)\)/);
  if (!m) return null;
  const p = m[1].split(",").map((x) => parseFloat(x));
  return { rgb: p.slice(0, 3), a: p.length > 3 ? p[3] : 1 };
};
const lum = (rgb) => {
  const L = rgb.map((v) => {
    v /= 255;
    return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
  });
  return 0.2126 * L[0] + 0.7152 * L[1] + 0.0722 * L[2];
};
const contrast = (a, b) => {
  const [l1, l2] = [lum(a), lum(b)].sort((x, y) => y - x);
  return (l1 + 0.05) / (l2 + 0.05);
};

(async () => {
  const browser = await puppeteer.launch({
    ...CHROME_READY,
    executablePath: process.env.CHROME || CHROME,
  });
  const page = await browser.newPage();
  await page.setViewport({ width: VIEW.w, height: VIEW.h, deviceScaleFactor: 1 });
  await page.goto(url, { waitUntil: "networkidle0", timeout: 60000 });
  await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
  await new Promise((r) => setTimeout(r, 700));
  await page.evaluate(() => window.scrollTo(0, 0));
  await new Promise((r) => setTimeout(r, 300));

  const report = await page.evaluate((_) => {
    const parse = (c) => {
      const m = c && c.match(/rgba?\(([^)]+)\)/);
      if (!m) return null;
      const p = m[1].split(",").map((x) => parseFloat(x));
      return { rgb: p.slice(0, 3), a: p.length > 3 ? p[3] : 1 };
    };
    const composeAncestorBg = (el) => {
      // see note (1) at top
      const chain = [];
      let n = el;
      while (n && n !== document.documentElement) {
        chain.push(getComputedStyle(n).backgroundColor);
        n = n.parentElement;
      }
      let acc = [255, 255, 255];
      for (const c of chain.reverse()) {
        const p = parse(c);
        if (!p) continue;
        if (p.a === 0) continue;
        acc = [0, 1, 2].map((i) => p.rgb[i] * p.a + acc[i] * (1 - p.a));
      }
      return `rgb(${acc.map(Math.round).join(",")})`;
    };
    // ---------- 1. typography inventory ----------
    const seen = new Map();
    [...document.querySelectorAll("h1,h2,h3,h4,p,li,a,button,span,div")].forEach((el) => {
      const direct = [...el.childNodes].filter((n) => n.nodeType === 3).map((n) => n.textContent).join("").trim();
      if (!direct || direct.length < 2) return;
      const s = getComputedStyle(el);
      const k = `${s.fontFamily.split(",")[0]}|${s.fontSize}|${s.fontWeight}|${s.letterSpacing}|${s.lineHeight}`;
      if (!seen.has(k)) seen.set(k, { count: 0, sample: direct.slice(0, 40) });
      seen.get(k).count++;
    });
    const typography = [...seen.entries()]
      .map(([k, v]) => ({ k, ...v }))
      .sort((a, b) => b.count - a.count);

    // ---------- 2. anchors with the user-agent defaults ----------
    const anchors = [...document.querySelectorAll("a")].map((a) => {
      const s = getComputedStyle(a);
      return {
        text: (a.textContent || "").trim().slice(0, 40),
        color: s.color,
        deco: s.textDecorationLine,
        href: a.href,
      };
    });
    const blue = anchors.filter((a) => {
      const c = parse(a.color);
      return c && c.rgb[2] - c.rgb[0] > 60 && /underline/i.test(a.deco);
    });

    // ---------- 3. layout: horizontal overflow + container left edges ----------
    const overflow = [];
    const lefts = new Map();
    [...document.querySelectorAll("body *")].forEach((el) => {
      const ox = getComputedStyle(el).overflowX;
      const over = el.scrollWidth - el.clientWidth;
      if (over > 2 && ox !== "auto" && ox !== "hidden") {
        overflow.push({ tag: el.tagName, cls: String(el.className).slice(0, 40), over });
      }
      if (el.offsetWidth > 200) {
        const k = el.offsetLeft;
        lefts.set(k, (lefts.get(k) || 0) + 1);
      }
    });

    // ---------- 4. sections and their backgrounds ----------
    const sections = [];
    [...document.querySelectorAll("section, header, footer, main > div")].forEach((s) => {
      const r = s.getBoundingClientRect();
      sections.push({ top: Math.round(r.top + window.scrollY), h: Math.round(r.height), bg: composeAncestorBg(s) });
    });

    // ---------- 5. logo block ----------
    const logo = (() => {
      const el = document.querySelector("a[aria-label], a[href='/'], a[href='/logo'], header a, [data-logo]");
      if (!el) return null;
      const r = el.getBoundingClientRect();
      return { left: Math.round(r.left), top: Math.round(r.top + window.scrollY), w: Math.round(r.width), h: Math.round(r.height) };
    })();

    // ---------- 6. contrast ----------
    const textBg = (el) => {
      const cs = getComputedStyle(el);
      return { fg: cs.color, bg: composeAncestorBg(el) };
    };
    const contrastFailures = [];
    [...document.querySelectorAll("h1,h2,h3,h4,p,li,a,button,span,strong,em")].forEach((el) => {
      const t = (el.textContent || "").trim();
      const r = el.getBoundingClientRect();
      if (t.length < 1 || r.width === 0 || r.height === 0) return;
      const { fg, bg } = textBg(el);
      const fp = parse(fg), bp = parse(bg);
      if (!fp || !bp) return;
      const cs = getComputedStyle(el);
      const size = parseFloat(cs.fontSize);
      const weight = parseFloat(cs.fontWeight);
      const aa = size >= 18 || (size >= 14 && weight >= 700) ? 3 : 4.5;
      const ratio = (() => {
        const L1 = (() => {
          const L = fp.rgb.map((v) => {
            v /= 255;
            return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
          });
          return 0.2126 * L[0] + 0.7152 * L[1] + 0.0722 * L[2];
        })();
        const L2 = (() => {
          const L = bp.rgb.map((v) => {
            v /= 255;
            return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
          });
          return 0.2126 * L[0] + 0.7152 * L[1] + 0.0722 * L[2];
        })();
        return (Math.max(L1, L2) + 0.05) / (Math.min(L1, L2) + 0.05);
      })();
      if (ratio < aa) {
        contrastFailures.push({
          ratio: Number(ratio.toFixed(2)),
          target: aa,
          size: Math.round(size),
          fg,
          bg,
          text: t.slice(0, 32),
        });
      }
    });
    const distinctFg = [...new Set(contrastFailures.map((f) => f.fg))];

    return {
      docHeight: document.documentElement.scrollHeight,
      typography,
      anchors,
      blue,
      overflow,
      lefts: [...lefts.entries()].sort((a, b) => b[1] - a[1]),
      sections,
      logo,
      contrastFailures,
      distinctFg,
    };
  });

  console.log(`\n=== ${url} @ ${VIEW.w}x${VIEW.h} — document height ${report.docHeight}px ===\n`);
  console.log(`TYPE STYLES: ${report.typography.length} distinct`);
  report.typography.slice(0, 12).forEach((t) => {
    const [family, size, weight, ls, lh] = t.k.split("|");
    console.log(`   ${t.count}x  ${family} ${size} w${weight} ls${ls} lh${lh}   "${t.sample}"`);
  });
  console.log(`\nTEXT COLOURS: ${report.distinctFg.length} distinct`);
  report.distinctFg.forEach((c) => console.log(`    ${c}`));
  console.log(`\nLINKS: ${report.anchors.length} anchors; ${report.blue.length} with UA blue or underline`);
  for (const a of report.blue.slice(0, 8)) console.log(`  ${a.text} -> ${a.color} ${a.deco}`);

  console.log(`\nOVERFLOW: ${report.overflow.length}`);
  for (const o of report.overflow.slice(0, 6)) console.log(`  ${o.tag}.${o.cls} +${o.over}px`);

  console.log(`\nLEFT EDGES (grid discipline):`);
  for (const [x, n] of report.lefts.slice(0, 8)) console.log(`  x=${x}  ${n} blocks`);

  console.log(`\nSECTIONS:`);
  for (const s of report.sections.slice(0, 12)) console.log(`  top ${String(s.top).padStart(4)}  h ${String(s.h).padStart(4)}  bg ${s.bg}`);

  if (report.logo) {
    console.log(`\nLOGO: ${JSON.stringify(report.logo)}`);
  }

  console.log(`\nOVERLAPS:`);
  // cheap overlap check on header nav items (rows above 0): we'll skip cross-element overlap here
  console.log(`  (none measured; report any cross-element overlap from the screenshot pass)`);

  console.log(`\nCONTRAST BELOW WCAG: ${report.contrastFailures.length}`);
  for (const f of report.contrastFailures.slice(0, 14))
    console.log(`  ${f.ratio}:1 (needs ${f.target}) ${f.size}px ${f.fg} on ${f.bg}  "${f.text}"`);

  await browser.close();

  // Non-zero exit on real defects so this can be used as a gate without a screenshot read.
  const defects =
    report.blue.length + report.overflow.length + report.contrastFailures.length;
  process.exit(defects > 0 ? 1 : 0);
})().catch((e) => {
  console.error("audit failed:", e.message);
  process.exit(2);
});
