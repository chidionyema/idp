#!/usr/bin/env node
/**
 * Independent public readback for the Meridian company site.
 *
 * The canary reads the visitor-facing origins, not Vercel READY or a source
 * commit. It never submits contact forms or posts customer information.
 */
const ORIGINS = [
  'https://merdian-intelligence.vercel.app',
  'https://meridian-intelligence-uk.vercel.app',
  'https://merian-intelligence.vercel.app',
];
const PRIMARY = ORIGINS[1];
const failures = [];
const audit = [];
const OLD = 'AI infrastructure consulting for companies shipping production LLM systems';

async function read(url) {
  let lastError = null;
  for (let attempt = 0; attempt < 2; attempt++) {
    try {
      const cacheBuster = (url.includes('?') ? '&' : '?') + 'merdian_canary=' + Date.now();
      const response = await fetch(url + cacheBuster, {
        redirect: 'follow',
        cache: 'no-store',
        headers: { 'user-agent': 'Meridian-Public-Release-Canary/2.0', accept: 'text/html, */*' },
        signal: AbortSignal.timeout(15000),
      });
      const html = await response.text();
      if (!response.ok) throw new Error('HTTP ' + response.status);
      return { html, status: response.status, finalUrl: response.url };
    } catch (error) {
      lastError = error;
      if (attempt === 0) await new Promise(r => setTimeout(r, 1800));
    }
  }
  throw lastError;
}
function assert(condition, reason) {
  if (!condition) failures.push(reason);
}
async function checkHome(origin) {
  try {
    const { html, status } = await read(origin + '/');
    const identity = html.includes('Meridian Intelligence') &&
      !html.includes('Merdian Intelligence') &&
      html.includes('mi-hero-title') &&
      html.includes('mi-hero') &&
      html.includes('mi-services-grid') &&
      html.includes('INTELLIGENCE') && html.includes('MADE') &&
      html.includes('REAL');
    assert(identity, origin + ': public homepage is NOT the approved premium company design');
    assert(!html.includes(OLD), origin + ': retired consulting-only homepage resurfaced');
    assert(!html.includes('Blabka'), origin + ': unsubstantiated placeholder venture shown to visitors');
    assert(!html.includes('MERDIAN INTELLIGENCE'), origin + ': uppercase legacy spelling survived');
    assert(!html.includes('More information will be shared'), origin + ': content-debt promise published');
    assert(html.includes('01 / MANIFESTO') && html.includes('02 / CONSULTANCY') &&
      html.includes('03 / THE LABORATORY') && html.includes('04 / VENTURES + PRODUCTS'),
      origin + ': information architecture drifted from canonical hierarchy');
    assert(!html.includes('http://localhost:3000'), origin + ': localhost leaked into SEO metadata');
    assert(!html.includes('https://meridian.ai'), origin + ': unowned domain leaked into public metadata');
    assert(html.includes('href="/consulting"') && html.includes('href="/research"'),
      origin + ': core commercial journeys missing');
    audit.push({ origin, status, identity });
  } catch (error) {
    failures.push(origin + ': ' + (error instanceof Error ? error.message : String(error)));
  }
}
async function checkRoute(origin, path, marker) {
  try {
    const { html, status } = await read(origin + path);
    assert(!html.includes('Merdian Intelligence'), origin + path + ': legacy spelling on sibling page');
    assert(html.includes(marker), origin + path + ': required company section missing: ' + marker);
    if (path === '/products') {
      assert(!html.includes('Blabka'), origin + path + ': placeholder venture visible');
      assert(!html.includes('Further details will be published'), origin + path + ': unsubstantiated promise visible');
    }
    assert(!html.includes(OLD), origin + path + ': retired product promise resurfaced');
    assert(!html.includes('http://localhost:3000'), origin + path + ': localhost in HTML');
    audit.push({ origin: origin + path, status, marker: html.includes(marker) });
  } catch (error) {
    failures.push(origin + path + ': ' + (error instanceof Error ? error.message : String(error)));
  }
}

// Every alias gets the same visitor-facing sibling route audit; checking the
// homepage on all origins and interior only on PRIMARY previously missed drift.
for (const origin of ORIGINS) {
  await checkHome(origin);
  for (const [path, marker] of [
    ['/consulting', 'mi-interior'],
    ['/research', 'mi-interior'],
    ['/products', 'mi-interior'],
    ['/contact', 'mi-interior'],
  ]) await checkRoute(origin, path, marker);
}
// Customer conversion is an actual commercial requirement at EVERY ingress.
// This is a read-only readiness probe, not proof of a delivered enquiry.
// Never submit visitor PII, nor close the incident without a synthetic receipt.
for (const origin of ORIGINS) {
  try {
    const { html, status } = await read(origin + '/api/contact');
    const statusBody = JSON.parse(html);
    const accepting = statusBody && statusBody.acceptingEnquiries === true;
    assert(accepting, origin + '/api/contact: commercial enquiry delivery unavailable');
    audit.push({ origin: origin + '/api/contact', status, accepting });
  } catch (error) {
    failures.push(origin + '/api/contact: ' + (error instanceof Error ? error.message : String(error)));
  }
}

// SEO is a public side effect on every assigned ingress; an alias can serve
// stale robots/sitemap independently of the main host.
for (const origin of ORIGINS) {
  for (const path of ['/robots.txt', '/sitemap.xml']) {
    try {
      const { html, status } = await read(origin + path);
      assert(!html.includes('localhost'), origin + path + ': localhost leaked into indexable metadata');
      assert(!html.includes('meridian.ai'), origin + path + ': unowned domain leaked into indexable metadata');
      assert(!html.includes('https://merdian-intelligence.vercel.app'), origin + path + ': obsolete canonical URL is indexed');
      audit.push({ origin: origin + path, status });
    } catch (error) {
      failures.push(origin + path + ': ' + (error instanceof Error ? error.message : String(error)));
    }
  }
}
const summary = {
  timestamp: new Date().toISOString(),
  primary: PRIMARY,
  checked: audit.length,
  failures,
  evidence: audit,
};
console.log(JSON.stringify(summary, null, 2));
if (failures.length) {
  console.error('MERIDIAN PUBLIC SITE INCIDENT — ' + failures.join('; '));
  process.exitCode = 1;
} else {
  console.log('MERIDIAN PUBLIC READBACK: PASS');
}
