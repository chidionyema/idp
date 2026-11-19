import test from 'node:test';
import assert from 'node:assert/strict';
import {
  reduceRegisterToScene,
  reconcileSceneAgainstRegister,
  projectTelegram3327PinnedMessage,
  type OpsEvidenceFile,
  type OpsRegisterEntry,
} from './registerProjector';

function buildFixtureStream(): {
  entries: OpsRegisterEntry[];
  evidenceBySeq: Record<number, OpsEvidenceFile>;
  shaBySeq: Record<number, string>;
} {
  const ev1: OpsEvidenceFile = {
    seq: 1,
    insId: 'INS-TEST-001',
    title: 'Thin client pytest collection gate verification',
    repo: 'chidionyema/idp',
    ts: '2026-11-11T14:02:10Z',
    surface: 'MV3 Browser Symbiont',
    formation: 'sniper',
    stage: 'PLANNED',
    verdict: 'pass',
    revoked: 0,
    leaseEpoch: 1,
    command: 'estate_execute plan --ins INS-TEST-001',
    exitCode: 0,
    collectedCount: null,
    stdoutTail: 'Scoped thin_client.py test suite; granted test:exec capability',
    ruleHits: ['one_door_admission'],
    decision: 'advance to ACTUATING',
    capabilityGrants: ['fs:read', 'test:exec'],
    agentNarrationUnverified: 'I will run pytest next and verify all tests pass.',
  };

  // Classic D.1 trap: exit 0 with collected 0 -> deterministic FAIL
  const ev2: OpsEvidenceFile = {
    seq: 2,
    insId: 'INS-TEST-001',
    title: 'Thin client pytest collection gate verification',
    repo: 'chidionyema/idp',
    ts: '2026-11-11T14:03:11Z',
    surface: 'MV3 Browser Symbiont',
    formation: 'sniper',
    stage: 'ACTUATING',
    verdict: 'fail',
    revoked: 0,
    leaseEpoch: 1,
    command: 'estate_execute test',
    exitCode: 0,
    collectedCount: 0,
    stdoutTail: 'pytest exited 0 with 0 items collected',
    ruleHits: ['require_collected_min >= 10'],
    decision: 'ops run test --json',
    capabilityGrants: ['fs:read', 'test:exec'],
    agentNarrationUnverified: 'Tests exited with code 0 so everything looks green!',
  };

  const ev3: OpsEvidenceFile = {
    seq: 3,
    insId: 'INS-07957',
    title: 'Pre-push branch delta verification',
    repo: 'chidionyema/idp',
    ts: '2026-11-11T14:04:00Z',
    surface: 'Greenlane CI',
    formation: 'centurion',
    stage: 'VERIFIED_DONE',
    verdict: 'pass',
    revoked: 0,
    leaseEpoch: 1,
    command: 'ops run test --json',
    exitCode: 0,
    collectedCount: 31,
    stdoutTail: '31 collected, 31 passed in 0.42s',
    ruleHits: ['branch_delta_isolated'],
    decision: 'sealed in Verified Vault',
    capabilityGrants: ['fs:read', 'lane:submit'],
    agentNarrationUnverified: null,
  };

  const sha1 = '1111111111111111111111111111111111111111111111111111111111111111';
  const sha2 = '2222222222222222222222222222222222222222222222222222222222222222';
  const sha3 = '3333333333333333333333333333333333333333333333333333333333333333';

  const entries: OpsRegisterEntry[] = [
    {
      seq: 1,
      insId: ev1.insId,
      title: ev1.title,
      repo: ev1.repo,
      ts: ev1.ts,
      surface: ev1.surface,
      formation: ev1.formation,
      stage: ev1.stage,
      verdict: ev1.verdict,
      revoked: 0,
      leaseEpoch: 1,
      evidenceFile: '.ops/evidence/0001-INS-TEST-001.json',
      evidenceSha256: sha1,
    },
    {
      seq: 2,
      insId: ev2.insId,
      title: ev2.title,
      repo: ev2.repo,
      ts: ev2.ts,
      surface: ev2.surface,
      formation: ev2.formation,
      stage: ev2.stage,
      verdict: ev2.verdict,
      revoked: 0,
      leaseEpoch: 1,
      evidenceFile: '.ops/evidence/0002-INS-TEST-001.json',
      evidenceSha256: sha2,
    },
    {
      seq: 3,
      insId: ev3.insId,
      title: ev3.title,
      repo: ev3.repo,
      ts: ev3.ts,
      surface: ev3.surface,
      formation: ev3.formation,
      stage: ev3.stage,
      verdict: ev3.verdict,
      revoked: 0,
      leaseEpoch: 1,
      evidenceFile: '.ops/evidence/0003-INS-07957.json',
      evidenceSha256: sha3,
    },
  ];

  return {
    entries,
    evidenceBySeq: { 1: ev1, 2: ev2, 3: ev3 },
    shaBySeq: { 1: sha1, 2: sha2, 3: sha3 },
  };
}

test('reduceRegisterToScene deduplicates SSE replays, projects exit-0/collected-0 as failing mood, and supports seq scrubbing', () => {
  const { entries, evidenceBySeq } = buildFixtureStream();
  // Replay seq 2 twice to verify idempotency
  const duplicated = [...entries, entries[1]];

  const headScene = reduceRegisterToScene(duplicated, evidenceBySeq);
  assert.equal(headScene.maxSeq, 3);
  assert.equal(headScene.totalPackets, 2);
  // INS-TEST-001 is ACTUATING (in-flight), INS-07957 is VERIFIED_DONE (not in-flight)
  assert.equal(headScene.inFlightCount, 1);
  assert.equal(headScene.verifiedDoneCount, 1);
  assert.equal(headScene.failingCount, 1);

  const testActor = headScene.actors.find((a) => a.insId === 'INS-TEST-001')!;
  assert.equal(testActor.mood, 'failing');
  assert.equal(testActor.verdict, 'fail');
  assert.equal(testActor.scriptLines.length, 2);
  assert.ok(testActor.scriptLines[1].formattedLine.includes('exit 0 · collected 0'));
  assert.ok(testActor.scriptLines[1].formattedLine.includes('require_collected_min >= 10'));

  // Scrub back to seq 1: INS-TEST-001 was still PLANNED + pass, INS-07957 not yet minted
  const rewound = reduceRegisterToScene(duplicated, evidenceBySeq, { scrubSeq: 1 });
  assert.equal(rewound.cursorSeq, 1);
  assert.equal(rewound.totalPackets, 1);
  assert.equal(rewound.actors[0].stage, 'PLANNED');
  assert.equal(rewound.actors[0].verdict, 'pass');
});

test('reconcileSceneAgainstRegister passes on truthful projection and catches R1 hash, R2 optimistic verdict, and R3 count lies', () => {
  const { entries, evidenceBySeq, shaBySeq } = buildFixtureStream();
  const scene = reduceRegisterToScene(entries, evidenceBySeq);

  // 1. Honest projection passes R1, R2, and R3
  const honestClaims = scene.actors.map((a) => ({
    insId: a.insId,
    seq: a.latestSeq,
    stage: a.stage,
    verdict: a.verdict,
    revoked: a.revoked,
    evidenceSha256: a.latestEvidenceSha256,
  }));

  const cleanReport = reconcileSceneAgainstRegister({
    renderedInFlightCount: scene.inFlightCount,
    renderedActors: honestClaims,
    diskRegisterEntries: entries,
    diskEvidenceBySeq: evidenceBySeq,
    diskSha256BySeq: shaBySeq,
    nowIso: '2026-11-11T14:05:00Z',
  });
  assert.equal(cleanReport.passed, true);
  assert.equal(cleanReport.discrepancies.length, 0);

  // 2. Corrupt renderer claim: paint INS-TEST-001 green ("pass") despite evidence verdict="fail", forge hash, and drift count
  const lyingClaims = honestClaims.map((c) =>
    c.insId === 'INS-TEST-001'
      ? { ...c, verdict: 'pass' as const, evidenceSha256: 'deadbeef'.repeat(8) }
      : c
  );

  const failedReport = reconcileSceneAgainstRegister({
    renderedInFlightCount: 9,
    renderedActors: lyingClaims,
    diskRegisterEntries: entries,
    diskEvidenceBySeq: evidenceBySeq,
    diskSha256BySeq: shaBySeq,
    nowIso: '2026-11-11T14:05:05Z',
  });

  assert.equal(failedReport.passed, false);
  assert.equal(failedReport.r1HashAgreement.passed, false);
  assert.equal(failedReport.r2VerdictAgreement.passed, false);
  assert.equal(failedReport.r3CountAgreement.passed, false);
  assert.equal(failedReport.discrepancies.length, 3);

  const pinText = projectTelegram3327PinnedMessage(scene, failedReport);
  assert.ok(pinText.includes('GENESIS 3327 PIN'));
  assert.ok(pinText.includes('DRIFT REFUSED'));
  assert.ok(pinText.includes('[FAIL] INS-TEST-001'));
});

test('AFTER UPDATE revoked=1 kills actor mood and removes packet from active in-flight count', () => {
  const { entries, evidenceBySeq } = buildFixtureStream();
  const revokeEv: OpsEvidenceFile = {
    ...evidenceBySeq[2],
    seq: 4,
    ts: '2026-11-11T14:04:30Z',
    verdict: 'revoked',
    revoked: 1,
    leaseEpoch: 2,
    command: 'd1_trigger after_update_revoke',
    stdoutTail: 'Capability grant revoked by epoch fence',
    ruleHits: ['lease_revoked_trigger'],
    decision: 'halt actor immediately',
  };
  const revokeEntry: OpsRegisterEntry = {
    seq: 4,
    insId: 'INS-TEST-001',
    title: revokeEv.title,
    repo: revokeEv.repo,
    ts: revokeEv.ts,
    surface: revokeEv.surface,
    formation: revokeEv.formation,
    stage: 'ACTUATING',
    verdict: 'revoked',
    revoked: 1,
    leaseEpoch: 2,
    evidenceFile: '.ops/evidence/0004-INS-TEST-001.json',
    evidenceSha256: '4'.repeat(64),
  };

  const scene = reduceRegisterToScene(
    [...entries, revokeEntry],
    { ...evidenceBySeq, 4: revokeEv }
  );
  const actor = scene.actors.find((a) => a.insId === 'INS-TEST-001')!;
  assert.equal(actor.revoked, 1);
  assert.equal(actor.mood, 'revoked_dead');
  assert.equal(scene.inFlightCount, 0);
  assert.equal(scene.revokedCount, 1);
});
