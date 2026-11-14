import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync, existsSync } from "node:fs";

const root = new URL("../", import.meta.url);
const read = p => readFileSync(new URL(p, root), "utf8");

test("the public investor journey is present without private investor endpoints", () => {
  assert.ok(existsSync(new URL("app/investors/page.tsx", root)));
  const page = read("app/investors/page.tsx");
  assert.match(page, /\/contact\?topic=investor/);
  assert.doesNotMatch(page, /href="\/investors\/room"/);
  for (const p of [
    "app/investors/room/page.tsx",
    "app/investors/access/route.ts",
    "app/investors/activate/route.ts",
    "app/api/investors/surfaces/route.ts",
  ]) assert.equal(existsSync(new URL(p, root)), false, "private endpoint not authorized in public release: "+p);
});

test("Chronos is labelled as a development-stage concept", () => {
  assert.match(read("app/products/chronos/page.tsx"), /Chronos is in development/);
  assert.match(read("components/ChronosWalkthrough.tsx"), /ILLUSTRATIVE EXPERIENCE/);
});

test("investor discoverability and legal privacy link are preserved", () => {
  assert.match(read("components/Nav.tsx"), /href: "\/investors"/);
  assert.match(read("components/Footer.tsx"), /href="\/privacy"/);
  assert.match(read("app/sitemap.ts"), /\/investors/);
});
