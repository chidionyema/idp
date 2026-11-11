import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
const read = (p) => readFileSync(new URL("../" + p, import.meta.url), "utf8");
test("Meridian homepage explicitly offers consultancy, research and ventures", () => {
  const page = read("app/page.tsx");
  for (const label of ["CONSULTANCY", "LABORATORY", "VENTURES", "Mumchimp", "Genesis"]) {
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
  assert.ok(read("app/robots.ts").includes("MERIDIAN_SITE_URL"));
  assert.ok(!read("app/robots.ts").includes("meridian.ai"));
});
test("The visual system includes responsive and reduced-motion handling", () => {
  const css = read("app/merian.css");
  assert.ok(css.includes("prefers-reduced-motion"));
  assert.ok(css.includes("max-width:620px"));
});

test("Commercial routes carry the same Meridian design system and contact remains accessible", () => {
  const contact = read("app/contact/page.tsx");
  const contactMeta = read("app/contact/layout.tsx");
  const insights = read("app/writing/page.tsx");
  const approach = read("app/case-studies/page.tsx");
  for (const source of [contact, insights, approach]) {
    assert.ok(source.includes('className="mi-interior"'), "a public route escaped the branded interior");
    assert.ok(source.includes("mi-page-hero"), "missing branded page hero");
  }
  assert.ok(contact.includes('aria-invalid={Boolean(errors.email)}'));
  assert.ok(contact.includes("validateContact(form)"), "client validation must match the API");
  assert.ok(contact.includes("aria-live"), "form status must be announced");
  assert.ok(contact.includes("Your message has not been sent"), "never claim an undelivered enquiry was accepted");
  assert.ok(contactMeta.includes("Contact | Meridian Intelligence"));
  assert.ok(!contactMeta.includes("Merdian Intelligence"), "old company identity leaked into metadata");
  assert.ok(insights.includes("mi-insights-row"));
  assert.ok(approach.includes("mi-proof-band"));
});

test("The visible Meridian identity is consistent across all customer surfaces", () => {
  for (const path of ["app/page.tsx", "app/layout.tsx", "app/products/page.tsx", "components/Logo.tsx", "components/Footer.tsx", "content/site.ts"]) {
    const source = read(path);
    assert.ok(!source.includes("Merdian"), "legacy spelling in " + path);
  }
  assert.ok(read("app/layout.tsx").includes("https://meridian-intelligence-uk.vercel.app"));
});
