import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import {
  validBrokerOrigin, validSessionCookie, brokerConfig, parseInvestorGrant,
  authorizeInvestor, parseInvestorProjection, readInvestorProjection,
} from "../lib/investorAccess.ts";

const time = Date.parse("2026-11-12T12:00:00.000Z");
const session = "s".repeat(48);
const config = { origin: "https://investor-broker.estate.example", serviceToken:"t".repeat(48) };
const validGrant = {
  issuer: "meridian-investor-broker", decision: "allow", identityVerified: true, revoked: false,
  mfaVerified: true, mfaVerifiedAt: new Date(time - 2 * 60_000).toISOString(),
  grantId: "investor-grant-001", subject: "guest:111", displayName: "Approved guest",
  issuedAt: new Date(time - 2 * 86400_000).toISOString(),
  expiresAt: new Date(time + 5 * 86400_000).toISOString(),
  lastActivityAt: new Date(time - 60_000).toISOString(),
  identityVerifiedAt: new Date(time - 2 * 86400_000).toISOString(),
  permissions: ["investor:genesis:view", "investor:otto:view"],
};
const projection = {
  schema: "meridian.investor.projection.v1", readOnly: true,
  classification: "INVESTOR_APPROVED", state: "observed",
  surface: "genesis", headline: "Work with greater clarity.",
  introduction: "A carefully selected observation from the research.",
  observedAt: new Date(time - 10_000).toISOString(),
  sourceRevision: "a".repeat(40),
  facts: [{ label: "Status", value: "Observed" }],
  moments: [{ title: "An approved update", description: "Reviewed and approved for this briefing.",
    observedAt: new Date(time - 10_000).toISOString() }],
};

test("only a configured HTTPS service can be the fixed investor broker origin", () => {
  for (const value of ["http://broker.example", "https://localhost", "https://127.0.0.1",
    "https://user:pass@broker.example", "https://broker.example:8443", "https://broker.example/path",
    "https://broker.example/?to=evil", "https://a..b.example", "javascript:alert(1)"])
    assert.equal(validBrokerOrigin(value), null, value);
  assert.equal(validBrokerOrigin(config.origin), config.origin);
  assert.equal(brokerConfig({ INVESTOR_BROKER_ORIGIN: config.origin }, () => undefined), null);
  assert.equal(brokerConfig({ INVESTOR_BROKER_ORIGIN: config.origin,
    INVESTOR_BROKER_SERVICE_TOKEN: config.serviceToken }, () => undefined)?.origin, config.origin);
});

test("refuse missing cookies before network; no anonymous or public fallback", async () => {
  let count = 0;
  const fetcher = async () => { count++; throw Error("should not run"); };
  for (const token of ["", "abc", null, undefined, "<script>", session + "\n"]) {
    assert.equal((await authorizeInvestor(token, config, time, fetcher)).state, "denied");
  }
  assert.equal(count, 0);
  assert.equal(validSessionCookie(session), true);
  assert.equal((await authorizeInvestor(session, null, time, fetcher)).state, "unavailable");
});

test("named, current, non-revoked, verified, scoped grant required on every request", () => {
  const ok = parseInvestorGrant(validGrant, time);
  assert.ok(ok);
  assert.equal(ok.permissions.length, 2);
  assert.ok(parseInvestorGrant({...validGrant,
    issuedAt: new Date(time - 60_000).toISOString(),
    lastActivityAt: new Date(time - 30_000).toISOString(),
    expiresAt: new Date(time - 60_000 + 7 * 86400_000).toISOString()}, time), 'seven-day grant accepted');
  assert.ok(parseInvestorGrant(validGrant, time), 'historic identity verification is permitted only with separately attested fresh MFA');
  for (const changed of [
    { decision: "deny" }, { revoked: true }, { identityVerified: false },
    { mfaVerified: false }, { mfaVerifiedAt: undefined },
    { mfaVerifiedAt: new Date(time - 15 * 60_000).toISOString() },
    { mfaVerifiedAt: new Date(time + 60_000).toISOString() },
    { issuer: "evil-issuer" }, { expiresAt: new Date(time - 1).toISOString() },
    { expiresAt: new Date(time + 8 * 86400_000).toISOString() },
    { issuedAt: undefined }, { lastActivityAt: undefined },
    { issuedAt: new Date(time + 60_000).toISOString() },
    { issuedAt: new Date(time - 3 * 86400_000).toISOString() },
    { lastActivityAt: new Date(time - 30 * 60_000).toISOString() },
    { lastActivityAt: new Date(time + 60_000).toISOString() },
    { lastActivityAt: new Date(time - 3 * 86400_000).toISOString() },
    { identityVerifiedAt: new Date(time + 60_000).toISOString() },
    { permissions: ["investor:genesis:view", "admin:execute"] },
    { permissions: ["investor:otto:view", "investor:otto:view"] },
    { permissions: [] }, { displayName: "<script>" },
  ]) {
    assert.equal(parseInvestorGrant({ ...validGrant, ...changed }, time), null, JSON.stringify(changed));
  }
});

test("broker rechecks grant with service authentication; revocation and downtime fail closed", async () => {
  const called = [];
  const fetcher = async (url, init) => {
    called.push({ url, init });
    return new Response(JSON.stringify(validGrant), { status: 200 });
  };
  const accepted = await authorizeInvestor(session, config, time, fetcher);
  assert.equal(accepted.state, "allowed");
  assert.equal(called.length, 1);
  assert.equal(called[0].url, config.origin + "/v1/investor/introspect");
  assert.equal(called[0].init.method, "POST");
  assert.equal(called[0].init.cache, "no-store");
  assert.equal(called[0].init.headers.Authorization, "Bearer " + config.serviceToken);
  assert.ok(called[0].init.body.includes(session));
  const revoked = await authorizeInvestor(session, config, time,
    async () => new Response(JSON.stringify({ ...validGrant, revoked:true }), { status: 200 }));
  assert.equal(revoked.state, "denied");
  const expired = await authorizeInvestor(session, config, time,
    async () => new Response("", { status: 410 }));
  assert.deepEqual(expired, {state:"denied",reason:"expired"});
  const unavailable = await authorizeInvestor(session, config, time,
    async () => { throw Error("offline"); });
  assert.equal(unavailable.state, "unavailable");
});

test("only current, explicitly approved, read-only Genesis or OTTO projections can be presented", () => {
  assert.equal(parseInvestorProjection(projection, "genesis", time)?.facts[0].value, "Observed");
  assert.equal(parseInvestorProjection(projection, "otto", time), null);
  for (const changed of [
    { state: "fixture" }, { readOnly: false }, { classification: "INTERNAL" },
    { observedAt: new Date(time - 6 * 60_000).toISOString() },
    { sourceRevision: "unknown" }, { headline: "<secret>" },
    { facts: [{ label:"Cookie", value: "<TOKEN>" }] },
    { moments: [{title:"Bad",description:"Unsafe",observedAt:"not a date"}] },
  ]) {
    assert.equal(parseInvestorProjection({...projection,...changed}, "genesis", time), null,
      JSON.stringify(changed));
  }
  const parsed = parseInvestorProjection({...projection, internalSecrets:"must-never-pass"}, "genesis", time);
  assert.ok(parsed);
  assert.ok(!JSON.stringify(parsed).includes("must-never-pass"));
});

test("grant scope denies projection fetch before network and never assumes unavailable means zero", async () => {
  const access = parseInvestorGrant({...validGrant,permissions:["investor:genesis:view"]}, time);
  assert.ok(access);
  let calls = 0;
  const refused = await readInvestorProjection(session, access, "otto", config, time, async () => {calls++;throw Error("called");});
  assert.equal(refused.state,"unavailable");
  assert.equal(calls,0);
  const current = await readInvestorProjection(session, access, "genesis", config, time,
    async () => new Response(JSON.stringify(projection),{status:200}));
  assert.equal(current.state,"available");
  const stale = await readInvestorProjection(session, access, "genesis", config, time,
    async () => new Response(JSON.stringify({...projection,observedAt:new Date(time - 900_000).toISOString()}),{status:200}));
  assert.equal(stale.state,"unavailable");
});

test("private investor room never links directly to founder operations or embeds unfiltered surfaces", () => {
  const room=readFileSync(new URL("../components/InvestorRoom.tsx",import.meta.url),"utf8");
  const handler=readFileSync(new URL("../app/api/investors/surfaces/route.ts",import.meta.url),"utf8");
  const entry=readFileSync(new URL("../app/investors/access/route.ts",import.meta.url),"utf8");
  const activate=readFileSync(new URL("../app/investors/activate/route.ts",import.meta.url),"utf8");
  const exit=readFileSync(new URL("../app/investors/leave/route.ts",import.meta.url),"utf8");
  assert.doesNotMatch(room, /<iframe|genesis-founder-surface\.pages\.dev|api\/brain\/state|api\/ott|github\.com/);
  assert.match(handler,/authorizeInvestor/);
  assert.match(handler,/readInvestorProjection/);
  assert.match(handler,/no-store/);
  assert.match(handler,/Vary/);
  assert.match(entry,/code_challenge_method/);
  assert.match(entry,/httpOnly: true, secure: true/);
  assert.match(activate,/timingSafeEqual/);
  assert.match(activate,/authorizeInvestor/);
  assert.match(activate,/httpOnly: true, secure: true/);
  assert.doesNotMatch(activate,/new URL\([^\n]+req\.url/,"redirect must never reflect request Host");
  assert.doesNotMatch(entry,/new URL\([^\n]+req\.url/,"login errors must not reflect request Host");
  assert.match(activate,/validBrokerOrigin\(process\.env\.MERIDIAN_SITE_URL/);
  assert.match(entry,/validBrokerOrigin\(process\.env\.MERIDIAN_SITE_URL/);
  assert.match(exit,/cookies\.delete/);
});
