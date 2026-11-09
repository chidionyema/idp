import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
const read = (p) => readFileSync(new URL("../" + p, import.meta.url), "utf8");
test("Merdian homepage explicitly offers consultancy, research and ventures", () => {
  const page = read("app/page.tsx");
  for (const label of ["CONSULTANCY", "LABORATORY", "VENTURES", "Mumchimp", "Genesis", "Blabka"]) {
    assert.ok(page.includes(label), "missing positioning: "+label);
  }
  assert.ok(page.includes("href=\"/consulting\""));
  assert.ok(!page.includes("github.com"), "customer homepage must never link to source control");
});
test("Portfolio keeps Genesis internal and verifies a commercial route", () => {
  const p = read("app/products/page.tsx");
  assert.ok(!p.includes("github.com"), "no source links in commercial portfolio");
  assert.ok(p.includes("https://mumchimp.com"));
  assert.ok(p.includes("RESEARCH + EXPERIMENTAL OPERATIONS"));
});
test("Consultancy describes paid service families, rather than only experiments", () => {
  const c = read("app/consulting/page.tsx");
  for (const label of ["technical advisory","Applied AI engineering","Autonomous operations","Research partnerships"]) assert.ok(c.includes(label));
});
test("Robots metadata uses the canonical deploy hostname", () => {
  assert.ok(read("app/robots.ts").includes("MERDIAN_SITE_URL"));
  assert.ok(!read("app/robots.ts").includes("meridian.ai"));
});
test("The visual system includes responsive and reduced-motion handling", () => {
  const css = read("app/merian.css");
  assert.ok(css.includes("prefers-reduced-motion"));
  assert.ok(css.includes("max-width:620px"));
});
