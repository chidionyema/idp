import test from 'node:test';
import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import {
  ARGON_TARGET_REPO,
  ARGON_DEFAULT_LANE_BRANCH,
  validateArgonSyncTarget,
  mapWorkspacePathToArgonPath,
  buildArgonSyncManifest,
  evaluateArgonSyncReadiness,
  generateArgonLaneApplyScript,
} from './argonSync';

function nodeSha256(text: string): string {
  return crypto.createHash('sha256').update(text, 'utf8').digest('hex');
}

test('validateArgonSyncTarget refuses direct main/master sync and enforces lane/* or propose/aistudio-*', () => {
  const mainAttempt = validateArgonSyncTarget('chidionyema/argon', 'main');
  assert.equal(mainAttempt.valid, false);
  if (!mainAttempt.valid) {
    assert.equal(mainAttempt.errorCode, 'BANNED_DIRECT_MAIN_SYNC');
  }

  const refsMainAttempt = validateArgonSyncTarget('chidionyema/argon', 'refs/heads/main');
  assert.equal(refsMainAttempt.valid, false);
  if (!refsMainAttempt.valid) {
    assert.equal(refsMainAttempt.errorCode, 'BANNED_DIRECT_MAIN_SYNC');
  }

  const wrongRepo = validateArgonSyncTarget('chidionyema/idp', 'lane/aistudio-genesis-2100-sync');
  assert.equal(wrongRepo.valid, false);
  if (!wrongRepo.valid) {
    assert.equal(wrongRepo.errorCode, 'UNSUPPORTED_TARGET_REPO');
  }

  const badPrefix = validateArgonSyncTarget('chidionyema/argon', 'feature/untracked');
  assert.equal(badPrefix.valid, false);
  if (!badPrefix.valid) {
    assert.equal(badPrefix.errorCode, 'INVALID_LANE_BRANCH_NAME');
  }

  const validLane = validateArgonSyncTarget('chidionyema/argon', ARGON_DEFAULT_LANE_BRANCH);
  assert.equal(validLane.valid, true);
  if (validLane.valid) {
    assert.equal(validLane.branch, 'lane/aistudio-genesis-2100-sync');
  }

  const validPropose = validateArgonSyncTarget('chidionyema/argon', 'propose/aistudio-2100-cockpit');
  assert.equal(validPropose.valid, true);
});

test('buildArgonSyncManifest maps .ops & .genesis/outbox to Argon root and computes deterministic Merkle SHA-256', () => {
  const sampleApp = 'export default function App() { return null; }\n';
  const sampleReg = '{"seq":1,"insId":"INS-07957"}\n';
  const sampleOutbox = '{"receiptId":"RCPT-1"}\n';

  assert.equal(
    mapWorkspacePathToArgonPath('.ops/register.jsonl').argonRepoPath,
    '.ops/register.jsonl'
  );
  assert.equal(
    mapWorkspacePathToArgonPath('.genesis/outbox/takeover-receipt-20261111.json').argonRepoPath,
    '.genesis/outbox/takeover-receipt-20261111.json'
  );
  assert.equal(
    mapWorkspacePathToArgonPath('src/App.tsx').argonRepoPath,
    'apps/genesis-2100-cockpit/src/App.tsx'
  );

  const files = [
    {
      workspacePath: 'src/App.tsx',
      content: sampleApp,
      sha256: nodeSha256(sampleApp),
      bytes: Buffer.byteLength(sampleApp, 'utf8'),
    },
    {
      workspacePath: '.ops/register.jsonl',
      content: sampleReg,
      sha256: nodeSha256(sampleReg),
      bytes: Buffer.byteLength(sampleReg, 'utf8'),
    },
    {
      workspacePath: '.genesis/outbox/takeover-receipt-20261111.json',
      content: sampleOutbox,
      sha256: nodeSha256(sampleOutbox),
      bytes: Buffer.byteLength(sampleOutbox, 'utf8'),
    },
  ];

  const m1 = buildArgonSyncManifest({
    files,
    idpObservedHeadSha: '65251ecd428a8c7b7c683653dcf3ec382623bf5e',
    handoverReceiptSha256: 'abcd1234',
    registerHeadSeq: 8,
    registerEntryCount: 8,
    generatedAt: '2026-11-11T20:00:00Z',
    sha256Fn: nodeSha256,
  });

  // Reversed input order must yield the exact same Merkle root SHA-256
  const m2 = buildArgonSyncManifest({
    files: [...files].reverse(),
    idpObservedHeadSha: '65251ecd428a8c7b7c683653dcf3ec382623bf5e',
    handoverReceiptSha256: 'abcd1234',
    registerHeadSeq: 8,
    registerEntryCount: 8,
    generatedAt: '2026-11-11T20:05:00Z',
    sha256Fn: nodeSha256,
  });

  assert.equal(m1.merkleRootSha256, m2.merkleRootSha256);
  assert.equal(m1.merkleRootSha256.length, 64);
  assert.equal(m1.fileCount, 3);
  assert.equal(m1.outboxEnvelope.v, 1);
  assert.equal(m1.outboxEnvelope.repo, ARGON_TARGET_REPO);
  assert.equal(m1.outboxEnvelope.governed_branch, ARGON_DEFAULT_LANE_BRANCH);
});

test('evaluateArgonSyncReadiness enforces epistemic honesty (U without auth, E1 only with matching 40-char commit SHA)', () => {
  const merkle = 'f'.repeat(64);

  // 1. Unprovisioned credentials -> strictly Authority U (never fake E1!)
  const unprovisioned = evaluateArgonSyncReadiness({
    hasServerGithubToken: false,
    hasGithubOAuthSession: false,
    oauthClientConfigured: false,
    currentMerkleRootSha256: merkle,
    lastRemoteReceipt: null,
  });
  assert.equal(unprovisioned.authority, 'U');
  assert.equal(unprovisioned.syncState, 'STAGED_AWAITING_GITHUB_AUTH');
  assert.equal(unprovisioned.canPushRemoteNow, false);

  // 2. Token present, not yet pushed -> E2 DRIFT_STAGED_LOCAL
  const readyToPush = evaluateArgonSyncReadiness({
    hasServerGithubToken: true,
    hasGithubOAuthSession: false,
    oauthClientConfigured: false,
    currentMerkleRootSha256: merkle,
    lastRemoteReceipt: null,
  });
  assert.equal(readyToPush.authority, 'E2');
  assert.equal(readyToPush.canPushRemoteNow, true);

  // 3. Verified 40-char GitHub commit SHA matching current Merkle root -> E1 SYNCED_REMOTE_E1
  const syncedE1 = evaluateArgonSyncReadiness({
    hasServerGithubToken: true,
    hasGithubOAuthSession: false,
    oauthClientConfigured: false,
    currentMerkleRootSha256: merkle,
    lastRemoteReceipt: {
      pushedAt: '2026-11-11T20:10:00Z',
      targetRepo: ARGON_TARGET_REPO,
      branch: ARGON_DEFAULT_LANE_BRANCH,
      baseMainSha: 'bc61148828d04d84c4862cdef0be33f56060f7b0',
      commitSha: '9a8b7c6d5e4f3a2b1c0d9e8f7a6b5c4d3e2f1a0b',
      treeSha: '1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b',
      pullRequestNumber: 92,
      pullRequestUrl: 'https://github.com/chidionyema/argon/pull/92',
      authMethod: 'SERVER_GITHUB_TOKEN',
      merkleRootSha256: merkle,
    },
  });
  assert.equal(syncedE1.authority, 'E1');
  assert.equal(syncedE1.syncState, 'SYNCED_REMOTE_E1');

  // 4. Subsequent local file/register mutation changes Merkle root -> downgrades from E1 to E2 DRIFT_STAGED_LOCAL
  const driftedAfterPush = evaluateArgonSyncReadiness({
    hasServerGithubToken: true,
    hasGithubOAuthSession: false,
    oauthClientConfigured: false,
    currentMerkleRootSha256: 'a'.repeat(64),
    lastRemoteReceipt: syncedE1.authority === 'E1'
      ? {
          pushedAt: '2026-11-11T20:10:00Z',
          targetRepo: ARGON_TARGET_REPO,
          branch: ARGON_DEFAULT_LANE_BRANCH,
          baseMainSha: 'bc61148828d04d84c4862cdef0be33f56060f7b0',
          commitSha: '9a8b7c6d5e4f3a2b1c0d9e8f7a6b5c4d3e2f1a0b',
          treeSha: '1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b',
          pullRequestNumber: 92,
          pullRequestUrl: 'https://github.com/chidionyema/argon/pull/92',
          authMethod: 'SERVER_GITHUB_TOKEN',
          merkleRootSha256: merkle,
        }
      : null,
  });
  assert.equal(driftedAfterPush.authority, 'E2');
  assert.equal(driftedAfterPush.syncState, 'DRIFT_STAGED_LOCAL');
});

test('generateArgonLaneApplyScript embeds Merkle check, origin guard, and refuses protected main branch', () => {
  const content = 'console.log("ok");\n';
  const manifest = buildArgonSyncManifest({
    files: [
      {
        workspacePath: 'src/main.tsx',
        content,
        sha256: nodeSha256(content),
        bytes: Buffer.byteLength(content, 'utf8'),
      },
    ],
    idpObservedHeadSha: '65251ecd428a8c7b7c683653dcf3ec382623bf5e',
    handoverReceiptSha256: '1234abcd',
    registerHeadSeq: 9,
    registerEntryCount: 9,
    sha256Fn: nodeSha256,
  });

  const script = generateArgonLaneApplyScript({
    manifest,
    bundleDownloadUrl: 'https://ais-dev-example.run.app/api/argon/bundle.json',
  });

  assert.ok(script.includes(manifest.merkleRootSha256));
  assert.ok(script.includes('TARGET_BRANCH="lane/aistudio-genesis-2100-sync"'));
  assert.ok(script.includes('if [[ "$CURRENT_BRANCH" == "main" || "$CURRENT_BRANCH" == "master" ]]; then'));
  assert.ok(script.includes('estate-execute lane-submit --repo argon --branch "$TARGET_BRANCH"'));
});
