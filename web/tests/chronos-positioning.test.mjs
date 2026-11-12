import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
const read=p=>readFileSync(new URL("../"+p,import.meta.url),"utf8");
test("Chronos is marketed from the homepage, portfolio, footer and sitemap",()=>{
  const home=read("app/page.tsx");
  const products=read("app/products/page.tsx");
  const footer=read("components/Footer.tsx");
  const sitemap=read("app/sitemap.ts");
  for(const src of [home,products,footer,sitemap]) assert.ok(src.includes("/products/chronos"),"Chronos navigation missing");
  assert.match(home,/RESEARCH CONCEPT/);
  assert.match(products,/NOT GENERALLY AVAILABLE/);
});
test("Chronos detail route tells the story without claiming a shipped platform",()=>{
  const page=read("app/products/chronos/page.tsx");
  for(const item of ["CHRONOS","RESEARCH CONCEPT","NOT GENERALLY AVAILABLE","SECONDS","QUARTERS","obligation","evidence","recovery","/contact"]) {
    assert.ok(page.toLowerCase().includes(item.toLowerCase()),"Missing Chronos concept claim: "+item);
  }
  for(const bad of ["Merdian","Blabka","Trusted by","99.9% uptime","available now","book a live demo","production SLA"]) {
    assert.ok(!page.toLowerCase().includes(bad.toLowerCase()),"Unsupported or obsolete Chronos claim: "+bad);
  }
  assert.match(page,/mi-interior mi-chronos/);
  assert.match(page,/export const metadata: Metadata/);
  assert.match(page,/aria-labelledby/);
});
test("Chronos mobile presentation and motion accessibility are part of the public release",()=>{
  const css=read("app/merian.css");
  assert.match(css,/\.mi-chronos-hero/);
  assert.match(css,/@media\(max-width:620px\)[\s\S]*?\.mi-chronos/);
  assert.match(css,/@media\(prefers-reduced-motion:reduce\)\{\.mi-chronos-ring/);
  assert.match(css,/\.mi-chronos :is\(a,button\):focus-visible/);
});
