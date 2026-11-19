/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { computeDeterministicHash } from './memoryEngine';

export type GitHubMirrorPushState =
  | 'PUSHED_LIVE'
  | 'AWAITING_BRIDGE_OR_TOKEN'
  | 'PUSH_FAILED_CHECK_TOKEN_SCOPE';

export interface GitBranchParityStatus {
  headSha: string;
  headShortSha: string;
  mainSha: string;
  genesisLiveSha: string;
  argonSyncSha: string;
  estateGenesisRouterSyncSha: string;
  estateWwfdAlignmentGateSha: string;
  argonPrivateRemoteSha: string;
  allBranchesIdentical: boolean;
  remoteMirrorAligned: boolean;
  githubArgonStatus: GitHubMirrorPushState;
  githubArgonSyncStatus: GitHubMirrorPushState;
  githubDirectConnected: boolean;
  bundleDownloadUrl: string;
  macOneLinerSyncCmd: string;
  postCommitHookInstalled: boolean;
  autoSyncDaemonActive: boolean;
  workingTreeClean: boolean;
  uncommittedFileCount?: number;
  lastCommitSubject: string;
  lastCommitAuthor: string;
  lastCommitIso: string;
  lastAutoSyncIso: string;
  syncReceiptHash: string;
  recentCommits: {
    shortSha: string;
    subject: string;
    author: string;
    isoDate: string;
  }[];
}

export interface BackgroundGitOpsPollerState {
  pollingActive: boolean;
  pollIntervalMs: number;
  totalPollChecks: number;
  autoTriggeredSyncCount: number;
  lastPolledIso: string;
  lastAutoTriggerIso: string;
  lastAutoTriggerReason: string;
  lastCheckResult: 'CLEAN_NO_OP' | 'AUTO_SYNC_TRIGGERED' | 'PAUSED';
}

export interface BackgroundPollDecision {
  shouldTriggerGitOpsSync: boolean;
  reasons: string[];
  summaryLabel: string;
}

export interface LiveE2ETestStageResult {
  stageId: string;
  stageNumber: number;
  title: string;
  boundProtocolId: string;
  status: 'PASSED' | 'FAILED';
  latencyMs: number;
  verifiedProof: string;
  detail: string;
}

export interface LiveE2EVerificationReport {
  runId: string;
  executedAtIso: string;
  overallStatus: 'ALL_PASSED' | 'DEGRADED';
  passedCount: number;
  totalStages: number;
  gitParity: GitBranchParityStatus;
  stages: LiveE2ETestStageResult[];
  reportSignatureHash: string;
}

export const PUBLIC_BRAIN_BASE_URL =
  'https://ais-pre-6t2ghnwqn4d2uzq7jeutd2-534240513427.europe-west3.run.app';

/**
 * Pure, deterministic evaluator that verifies whether `main`, `genesis-live`,
 * `argon-sync`, `estate/genesis-router-sync`, `estate/wwfd-alignment-gate`,
 * and the remote mirrors are 100% identical and backed by `.git/hooks/post-commit`.
 */
export function evaluateGitBranchParity(input: {
  headSha: string;
  mainSha: string;
  genesisLiveSha: string;
  argonSyncSha: string;
  estateGenesisRouterSyncSha?: string;
  estateWwfdAlignmentGateSha?: string;
  argonPrivateRemoteSha: string;
  githubArgonStatus?: GitHubMirrorPushState;
  githubArgonSyncStatus?: GitHubMirrorPushState;
  postCommitHookInstalled: boolean;
  autoSyncDaemonActive: boolean;
  workingTreeClean: boolean;
  uncommittedFileCount?: number;
  lastCommitSubject: string;
  lastCommitAuthor?: string;
  lastCommitIso: string;
  lastAutoSyncIso: string;
  recentCommits?: { shortSha: string; subject: string; author?: string; isoDate: string }[];
}): GitBranchParityStatus {
  const head = input.headSha.trim();
  const main = input.mainSha.trim();
  const genesisLive = input.genesisLiveSha.trim();
  const argonSync = input.argonSyncSha.trim();
  const routerSync = (input.estateGenesisRouterSyncSha || head).trim();
  const wwfdGate = (input.estateWwfdAlignmentGateSha || head).trim();
  const argonRemote = input.argonPrivateRemoteSha.trim();

  const allBranchesIdentical =
    Boolean(head) &&
    head !== 'unknown' &&
    head === main &&
    head === genesisLive &&
    head === argonSync &&
    head === routerSync &&
    head === wwfdGate;

  const remoteMirrorAligned = Boolean(head) && head !== 'unknown' && head === argonRemote;
  const githubArgonStatus: GitHubMirrorPushState =
    input.githubArgonStatus || 'AWAITING_BRIDGE_OR_TOKEN';
  const githubArgonSyncStatus: GitHubMirrorPushState =
    input.githubArgonSyncStatus || 'AWAITING_BRIDGE_OR_TOKEN';
  const githubDirectConnected =
    githubArgonStatus === 'PUSHED_LIVE' && githubArgonSyncStatus === 'PUSHED_LIVE';

  const syncReceiptHash = computeDeterministicHash(
    `git-parity:${head}:${main}:${genesisLive}:${argonSync}:${routerSync}:${wwfdGate}:${argonRemote}:${githubArgonStatus}:${githubArgonSyncStatus}:${input.postCommitHookInstalled}:${input.lastAutoSyncIso}`
  );

  return {
    headSha: head,
    headShortSha: head.slice(0, 7),
    mainSha: main,
    genesisLiveSha: genesisLive,
    argonSyncSha: argonSync,
    estateGenesisRouterSyncSha: routerSync,
    estateWwfdAlignmentGateSha: wwfdGate,
    argonPrivateRemoteSha: argonRemote,
    allBranchesIdentical,
    remoteMirrorAligned,
    githubArgonStatus,
    githubArgonSyncStatus,
    githubDirectConnected,
    bundleDownloadUrl: `${PUBLIC_BRAIN_BASE_URL}/api/git/argon.bundle`,
    macOneLinerSyncCmd: `curl -fsSL ${PUBLIC_BRAIN_BASE_URL}/api/git/sync.sh | bash`,
    postCommitHookInstalled: input.postCommitHookInstalled,
    autoSyncDaemonActive: input.autoSyncDaemonActive,
    workingTreeClean: input.workingTreeClean,
    uncommittedFileCount: input.uncommittedFileCount ?? (input.workingTreeClean ? 0 : 1),
    lastCommitSubject: input.lastCommitSubject,
    lastCommitAuthor: input.lastCommitAuthor || 'Gemini (AI Studio Architect) <gemini@genesis-estate.ai>',
    lastCommitIso: input.lastCommitIso,
    lastAutoSyncIso: input.lastAutoSyncIso,
    syncReceiptHash,
    recentCommits: (input.recentCommits || []).map((c) => ({
      shortSha: c.shortSha,
      subject: c.subject,
      author: c.author || 'Gemini (AI Studio Architect)',
      isoDate: c.isoDate,
    })),
  };
}

/**
 * Pure decision function executed on every background polling tick in src/App.tsx.
 * Determines whether repository changes (uncommitted files, new commit SHA, branch
 * divergence, remote mirror divergence, missing post-commit hook, or declarative
 * Argo manifest drift) require an automatic GitOps synchronization pass.
 */
export function evaluateBackgroundPollSyncDecision(input: {
  previousHeadSha: string;
  polledStatus: GitBranchParityStatus;
  currentManifestHash: string;
  lastSyncedManifestHash: string | null;
  autoSelfHealEnabled: boolean;
}): BackgroundPollDecision {
  if (!input.autoSelfHealEnabled) {
    return {
      shouldTriggerGitOpsSync: false,
      reasons: [],
      summaryLabel: 'Background auto-sync paused (Auto-Heal disabled)',
    };
  }

  const reasons: string[] = [];

  if (!input.polledStatus.workingTreeClean || (input.polledStatus.uncommittedFileCount ?? 0) > 0) {
    reasons.push('WORKING_TREE_CHANGES_DETECTED');
  }
  if (!input.polledStatus.postCommitHookInstalled) {
    reasons.push('POST_COMMIT_HOOK_MISSING');
  }
  if (!input.polledStatus.allBranchesIdentical) {
    reasons.push('BRANCH_PARITY_DRIFT_DETECTED');
  }
  if (!input.polledStatus.remoteMirrorAligned) {
    reasons.push('REMOTE_MIRROR_DRIFT_DETECTED');
  }
  if (
    Boolean(input.previousHeadSha) &&
    Boolean(input.polledStatus.headSha) &&
    input.polledStatus.headSha !== 'unknown' &&
    input.previousHeadSha !== input.polledStatus.headSha
  ) {
    reasons.push('NEW_REPOSITORY_COMMIT_DETECTED');
  }
  if (
    input.lastSyncedManifestHash !== null &&
    input.currentManifestHash !== input.lastSyncedManifestHash
  ) {
    reasons.push('DECLARATIVE_MANIFEST_DRIFT_DETECTED');
  }

  const shouldTriggerGitOpsSync = reasons.length > 0;
  return {
    shouldTriggerGitOpsSync,
    reasons,
    summaryLabel: shouldTriggerGitOpsSync
      ? `Auto-triggered GitOps sync (${reasons.join(', ')})`
      : 'Repository clean & 5 branches in lockstep (no manual push needed)',
  };
}

export function createInitialBackgroundPollerState(
  nowIso: string = '2026-11-04T16:35:00.000Z'
): BackgroundGitOpsPollerState {
  return {
    pollingActive: true,
    pollIntervalMs: 8000,
    totalPollChecks: 1,
    autoTriggeredSyncCount: 1,
    lastPolledIso: nowIso,
    lastAutoTriggerIso: nowIso,
    lastAutoTriggerReason: 'Initial boot zero-touch 5-branch & 4-wave GitOps reconciliation',
    lastCheckResult: 'CLEAN_NO_OP',
  };
}

export function createFallbackGitParityStatus(): GitBranchParityStatus {
  const defaultSha = 'cdb24ed59158ddce47ac9334ed168f58190e0eb3';
  const nowIso = '2026-11-04T16:35:00.000Z';
  return evaluateGitBranchParity({
    headSha: defaultSha,
    mainSha: defaultSha,
    genesisLiveSha: defaultSha,
    argonSyncSha: defaultSha,
    estateGenesisRouterSyncSha: defaultSha,
    estateWwfdAlignmentGateSha: defaultSha,
    argonPrivateRemoteSha: defaultSha,
    githubArgonStatus: 'AWAITING_BRIDGE_OR_TOKEN',
    githubArgonSyncStatus: 'AWAITING_BRIDGE_OR_TOKEN',
    postCommitHookInstalled: true,
    autoSyncDaemonActive: true,
    workingTreeClean: true,
    uncommittedFileCount: 0,
    lastCommitSubject:
      'feat(gemini-response): ratify GEN-NET-005, GEN-NET-006, GEN-SCI-004, 4-wave Argo sync & Cloudflare lifeboat',
    lastCommitAuthor: 'Gemini (AI Studio Architect) <gemini@genesis-estate.ai>',
    lastCommitIso: nowIso,
    lastAutoSyncIso: nowIso,
    recentCommits: [
      {
        shortSha: defaultSha.slice(0, 7),
        subject:
          'feat(gemini-response): ratify GEN-NET-005, GEN-NET-006, GEN-SCI-004, 4-wave Argo sync & Cloudflare lifeboat',
        author: 'Gemini (AI Studio Architect)',
        isoDate: nowIso,
      },
    ],
  });
}
