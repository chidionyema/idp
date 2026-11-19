import test from 'node:test';
import assert from 'node:assert/strict';
import {
  createInitialGenesisAcademyState,
  completeMicroSparkChallenge,
  evaluateInteractiveAcademyLab,
  simulateAsymmetricAcademyEconomics,
  verifyAcademyCredentialDigest,
  generateVerifiableAcademyCredentialMarkdown,
} from './beastGovernor';

test('Genesis Academy boots with 4 Human Learning Lenses, 6 playable 45s Micro-Sparks, 3 Live Labs, and CERT_L1 unlocked', () => {
  const state = createInitialGenesisAcademyState('2026-11-12T10:00:00.000Z');
  assert.equal(state.lenses.length, 4);
  assert.equal(state.sparks.length, 6);
  assert.equal(state.labs.length, 3);
  assert.equal(state.competitorMatrix.length, 4);
  assert.equal(state.learner.totalXp, 180);
  assert.equal(state.certifications[0].unlocked, true);
  assert.equal(state.certifications[1].unlocked, false);

  // Every Micro-Spark adapts copy across Kids, Everyday/Grandparents, Career Builders, and Founder Architect
  for (const spark of state.sparks) {
    for (const lens of state.lenses) {
      const copy = spark.byLens[lens.id];
      assert.ok(copy.hook5Sec.length > 10);
      assert.ok(copy.insight20Sec.length > 20);
      assert.ok(copy.superpower20Sec.length > 15);
      assert.equal(copy.quickCheckOptions.length, 3);
    }
  }
});

test('Completing Micro-Sparks and Live Labs enforces safety clamps, awards XP, and unlocks cryptographic SHA-256 credentials', () => {
  const state = createInitialGenesisAcademyState('2026-11-12T10:00:00.000Z');

  // Out-of-bounds prompt entropy (0.42 H > 0.08 H) triggers Geburah safety clamp
  const clamped = evaluateInteractiveAcademyLab(
    state,
    {
      labId: 'LAB_SPECGATE_PROMPT_SHIELD',
      sliderValue: 0.42,
      secondaryToggle: true,
    },
    '2026-11-12T10:01:00.000Z'
  );
  assert.equal(clamped.passed, false);
  assert.equal(clamped.stateLabel, 'SAFETY_CLAMP_TRIGGERED');
  assert.equal(clamped.xpAwarded, 0);

  // Completing SPARK-02 under EXPLORER_KIDS lens awards 60 XP (180 -> 240 XP) and increments streak
  const sparkOut = completeMicroSparkChallenge(
    state,
    {
      sparkId: 'SPARK-02',
      selectedOptionIndex: 0,
      lens: 'EXPLORER_KIDS',
    },
    '2026-11-12T10:02:00.000Z'
  );
  assert.equal(sparkOut.passed, true);
  assert.equal(sparkOut.xpAwarded, 60);
  assert.equal(state.learner.activeLens, 'EXPLORER_KIDS');
  assert.equal(state.learner.totalXp, 240);
  assert.equal(state.learner.streakDays, 4);

  // Passing Lab 02 inside [0.01..0.08 H] awards 120 XP (240 -> 360 XP, 2 completed labs) and unlocks CERT_L2!
  const verified = evaluateInteractiveAcademyLab(
    state,
    {
      labId: 'LAB_SPECGATE_PROMPT_SHIELD',
      sliderValue: 0.04,
      secondaryToggle: true,
    },
    '2026-11-12T10:03:00.000Z'
  );
  assert.equal(verified.passed, true);
  assert.equal(verified.stateLabel, 'NOMINAL_VERIFIED');
  assert.equal(verified.xpAwarded, 120);
  assert.equal(state.learner.totalXp, 360);

  const certL2 = state.certifications.find((c) => c.tierId === 'CERT_L2');
  assert.ok(certL2);
  assert.equal(certL2.unlocked, true);
  assert.ok(certL2.credentialSha256 && certL2.credentialSha256.length === 64);

  // Employer / Investor digest verification succeeds on prefix or full hash
  const check = verifyAcademyCredentialDigest(state, certL2.credentialSha256!.slice(0, 16));
  assert.equal(check.valid, true);
  assert.equal(check.matchedTier?.tierId, 'CERT_L2');

  const md = generateVerifiableAcademyCredentialMarkdown(state, 'aabbccddeeff0011');
  assert.ok(md.includes('Level 2 · Certified SpecGate BDD & White-Box Memory Practitioner'));
});

test('Asymmetric Academy Venture Simulator sustains >96% gross margin via $0 Free-Lane compute routing', () => {
  const econ = simulateAsymmetricAcademyEconomics({
    freeSocialLearnersMonthly: 80_000,
    proBuilderConversionPct: 5.0,
    proMonthlyPriceUsd: 29,
    enterpriseSeatsAnnual: 800,
    enterpriseSeatAnnualUsd: 499,
    verifiedHiresMonthly: 20,
  });

  assert.equal(econ.paidProSubscribers, 4000);
  assert.equal(econ.proMrrUsd, 116_000);
  assert.ok(econ.totalMrrUsd > 180_000);
  assert.ok(econ.annualizedArrUsd > 2_100_000);
  assert.ok(econ.grossMarginPct >= 96);
  assert.equal(econ.cacUsd, 0);
});
