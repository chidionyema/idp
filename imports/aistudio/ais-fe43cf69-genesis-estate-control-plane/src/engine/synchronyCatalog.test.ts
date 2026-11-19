import test from 'node:test';
import assert from 'node:assert/strict';
import {
  createInitialBeastGovernorState,
  triggerBeastDisruptiveIncident,
  createInitialBeastSynchronyState,
  refreshBeastSynchronyFromGovernor,
  filterModulesForPersona,
  generateLivingBrochureMarkdown,
} from './beastGovernor';

test('Progressive Persona Menu scopes Sovereign Product Modules cleanly: Founder (10) -> Investor (7) -> Enterprise (5) -> Public (3)', () => {
  const beast = createInitialBeastGovernorState('2026-11-12T09:20:00.000Z');
  const sync = createInitialBeastSynchronyState(beast, '2026-11-12T09:20:00.000Z');

  assert.equal(filterModulesForPersona(sync.productModules, 'FOUNDER_SOVEREIGN').length, 10);
  assert.equal(filterModulesForPersona(sync.productModules, 'INSTITUTIONAL_INVESTOR').length, 7);
  assert.equal(filterModulesForPersona(sync.productModules, 'ENTERPRISE_OPERATOR').length, 5);
  assert.equal(filterModulesForPersona(sync.productModules, 'PUBLIC_VISITOR').length, 3);

  // Every module carries a clickable deepLinkHash and canonical beast:// URI
  for (const mod of sync.productModules) {
    assert.ok(mod.deepLinkHash.startsWith('#'));
    assert.ok(mod.beastUri.startsWith('beast://meridian/'));
  }
});

test('Tempo-Chronos synchrony locks 4 horizons (1s, 1m, 1d, 1w), Forex $0 Free-Lane order book, and elevates BPM on incident', () => {
  const beast = createInitialBeastGovernorState('2026-11-12T09:20:00.000Z');
  const sync = createInitialBeastSynchronyState(beast, '2026-11-12T09:20:00.000Z');

  assert.equal(sync.heartbeatBpm, 60);
  assert.equal(sync.mathematicallySynchronized, true);
  assert.equal(sync.horizons.length, 4);
  assert.ok(sync.forexOrderBook.zeroCostMatchRatioPct > 85);
  assert.equal(sync.forexOrderBook.luldCircuitBreakerState, 'NORMAL_TRADING');

  // Triggering a Beast incident elevates BPM to 118 and clamps LULD circuit breaker
  triggerBeastDisruptiveIncident(beast, 'UNEVALUATED_SESSION', '2026-11-12T09:21:00.000Z');
  refreshBeastSynchronyFromGovernor(sync, beast, undefined, '2026-11-12T09:21:00.000Z');

  assert.equal(sync.heartbeatBpm, 118);
  assert.equal(sync.mathematicallySynchronized, false);
  assert.equal(sync.forexOrderBook.luldCircuitBreakerState, 'VOLATILITY_CLAMPED');
  assert.equal(sync.rankedHeadlines[0]?.severity, 'CRITICAL_INTERRUPT');
});

test('Omni-Node Surface Mapper ingests browser cookie/storage telemetry with zero orphaned/throwaway items', () => {
  const beast = createInitialBeastGovernorState('2026-11-12T09:20:00.000Z');
  const sync = createInitialBeastSynchronyState(beast, '2026-11-12T09:20:00.000Z');
  const prevRoot = sync.synchronyMerkleRootSha256;

  refreshBeastSynchronyFromGovernor(
    sync,
    beast,
    {
      userAgentSummary: 'HeadlessChromium/131',
      viewport: '1440x900',
      cookieCount: 1,
      cookieNames: ['estate_session_hint'],
      localStorageKeyCount: 2,
      localStorageKeys: ['meridian_persona', 'meridian_heartbeat_audio'],
      sessionStorageKeyCount: 0,
      hardwareConcurrency: 8,
      language: 'en-US',
      online: true,
      observedRttMs: 9,
    },
    '2026-11-12T09:22:00.000Z'
  );

  assert.equal(sync.omniSurfaceMap.clientBrowserProbed, true);
  assert.equal(sync.omniSurfaceMap.orphanedThrowawayCount, 0);
  assert.equal(sync.omniSurfaceMap.unmappedFogSectors, 0);
  assert.equal(sync.omniSurfaceMap.untrackedThirdPartyCookies, 0);
  assert.equal(sync.omniSurfaceMap.trackedCookieCount, 1);
  assert.notEqual(sync.synchronyMerkleRootSha256, prevRoot);
});

test('Living Brochure auto-updates with Beast Merkle digests and redacts Founder-only vault telemetry for Public/Investor personas', () => {
  const beast = createInitialBeastGovernorState('2026-11-12T09:20:00.000Z');
  const sync = createInitialBeastSynchronyState(beast, '2026-11-12T09:20:00.000Z');

  const founderMd = generateLivingBrochureMarkdown(sync, beast, 'FOUNDER_SOVEREIGN');
  const investorMd = generateLivingBrochureMarkdown(sync, beast, 'INSTITUTIONAL_INVESTOR');
  const publicMd = generateLivingBrochureMarkdown(sync, beast, 'PUBLIC_VISITOR');

  assert.ok(founderMd.includes('10/10 Sovereign Capabilities Displayed'));
  assert.ok(founderMd.includes('Founder Raw Telemetry'));
  assert.ok(founderMd.includes(beast.fractalConsistencyRootSha256));

  assert.ok(investorMd.includes('7/10 Sovereign Capabilities Displayed'));
  assert.ok(!investorMd.includes('Founder Raw Telemetry'));
  assert.ok(investorMd.includes('Zero-Budget "Mini-NASA" Unit Economics'));

  assert.ok(publicMd.includes('3/10 Sovereign Capabilities Displayed'));
  assert.ok(!publicMd.includes('Founder Raw Telemetry'));
});
