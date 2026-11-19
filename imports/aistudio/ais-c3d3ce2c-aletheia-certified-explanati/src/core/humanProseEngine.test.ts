import test from 'node:test';
import assert from 'node:assert/strict';
import {
  auditProsePassage,
  compileHumanVoiceRewrite,
  ESTATE_PROSE_PRESETS,
} from './humanProseEngine';

test('auditProsePassage quarantines AI-slop copy containing banned lexicon, throat-clearing, and contrastive triads', () => {
  const preset = ESTATE_PROSE_PRESETS[0];
  const aiReport = auditProsePassage(preset.aiDraft, 'written');

  assert.equal(aiReport.verdict, 'AI_SLOP_QUARANTINED');
  assert.ok(
    aiReport.violations.length >= 6,
    `Expected at least 6 violations in legacy AI draft, got ${aiReport.violations.length}`
  );
  assert.ok(aiReport.humanAuthenticityScore < 0.5);
});

test('auditProsePassage certifies human-authored asymmetric copy with zero violations and high burstiness', () => {
  for (const preset of ESTATE_PROSE_PRESETS) {
    const humanReport = auditProsePassage(preset.certifiedHumanRewrite, preset.channel);
    assert.equal(
      humanReport.violations.length,
      0,
      `Expected 0 violations in preset ${preset.id}, found: ${JSON.stringify(humanReport.violations)}`
    );
    assert.equal(humanReport.verdict, 'ESTATE_CERTIFIED_HUMAN');
    assert.ok(
      humanReport.humanAuthenticityScore >= 0.86,
      `Expected humanAuthenticityScore >= 0.86 for ${preset.id}, got ${humanReport.humanAuthenticityScore}`
    );
  }
});

test('compileHumanVoiceRewrite transforms arbitrary AI-infected text and removes banned RLHF patterns', () => {
  const customSlop =
    "In today's fast-paced world, our platform is not just about data — it's about empowering teams to seamlessly delve into the landscape, ensuring that they leverage holistic synergy.";

  const result = compileHumanVoiceRewrite(customSlop, 'written');
  assert.equal(result.beforeAudit.verdict, 'AI_SLOP_QUARANTINED');
  assert.equal(result.afterAudit.violations.length, 0);
  assert.equal(result.afterAudit.verdict, 'ESTATE_CERTIFIED_HUMAN');
  assert.ok(result.afterAudit.humanAuthenticityScore > result.beforeAudit.humanAuthenticityScore);
});
