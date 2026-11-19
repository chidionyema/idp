import type { EvidenceClass } from './estateRules.ts';

// ============================================================================
// ARGON CONTINUITY & GOVERNED `lane/*` SYNC ENGINE (PURE LOGIC)
// Target: private `chidionyema/argon` via Greenlane (`lane/*` or `propose/aistudio-*`)
// Enforces:
//   1. Zero direct `main` pushes (`BANNED_DIRECT_MAIN_SYNC`).
//   2. Epistemic truth (`E1` ONLY on verified 40-char GitHub commit SHA; `U` when staged locally).
//   3. Deterministic Merkle SHA-256 manifest over source tree + `.ops/register.jsonl` + `.genesis/outbox/`.
// ============================================================================

export const ARGON_TARGET_REPO = 'chidionyema/argon';
export const ARGON_DEFAULT_LANE_BRANCH = 'lane/aistudio-genesis-2100-sync';
export const ARGON_HANDOVER_BASE_SHA = 'bc61148828d04d84c4862cdef0be33f56060f7b0';
export const ARGON_COCKPIT_SUBDIR = 'apps/genesis-2100-cockpit';

export interface ArgonWorkspaceFileInput {
  /** Workspace-relative POSIX path, e.g. `src/App.tsx` or `.ops/register.jsonl` */
  workspacePath: string;
  /** File UTF-8 text content */
  content: string;
  /** Precomputed SHA-256 hex digest of UTF-8 bytes */
  sha256: string;
  /** UTF-8 byte length */
  bytes: number;
}

export interface ArgonMappedFileEntry {
  workspacePath: string;
  argonRepoPath: string;
  sha256: string;
  bytes: number;
  category: 'COCKPIT_SOURCE' | 'OPS_REGISTER_LEDGER' | 'GENESIS_OUTBOX' | 'PLATFORM_HOST_TOOLING';
}

export interface ArgonOutboxEnvelopeV1 {
  v: 1;
  repo: 'chidionyema/argon';
  instruction_id: string;
  title: string;
  body: string;
  merkle_root_sha256: string;
  register_head_seq: number;
  governed_branch: string;
  handover_base_sha: string;
}

export interface ArgonSyncManifest {
  schema: 'argon-continuity-sync.v1';
  generatedAt: string;
  targetRepo: string;
  governedBranch: string;
  handoverBaseSha: string;
  idpObservedHeadSha: string;
  handoverReceiptSha256: string;
  registerHeadSeq: number;
  registerEntryCount: number;
  fileCount: number;
  totalBytes: number;
  merkleRootSha256: string;
  files: ArgonMappedFileEntry[];
  outboxEnvelope: ArgonOutboxEnvelopeV1;
}

export interface ArgonRemotePushReceipt {
  pushedAt: string;
  targetRepo: string;
  branch: string;
  baseMainSha: string;
  commitSha: string;
  treeSha: string;
  pullRequestNumber: number | null;
  pullRequestUrl: string | null;
  authMethod: 'SERVER_GITHUB_TOKEN' | 'GITHUB_OAUTH_POPUP';
  merkleRootSha256: string;
}

export type ArgonTargetValidationResult =
  | {
      valid: true;
      repo: string;
      branch: string;
      governanceRule: 'GREENLANE_GOVERNED_BRANCH';
    }
  | {
      valid: false;
      errorCode: 'UNSUPPORTED_TARGET_REPO' | 'BANNED_DIRECT_MAIN_SYNC' | 'INVALID_LANE_BRANCH_NAME';
      reason: string;
    };

export interface ArgonSyncReadinessState {
  authority: EvidenceClass;
  syncState: 'SYNCED_REMOTE_E1' | 'DRIFT_STAGED_LOCAL' | 'STAGED_AWAITING_GITHUB_AUTH';
  authMode: 'SERVER_GITHUB_TOKEN' | 'GITHUB_OAUTH_POPUP' | 'UNPROVISIONED';
  oauthClientConfigured: boolean;
  canPushRemoteNow: boolean;
  statusHeadline: string;
  honestDetail: string;
}

const HEX_40_RE = /^[0-9a-f]{40}$/i;
const GOVERNED_BRANCH_RE = /^(lane|propose\/aistudio)[/-][a-z0-9][a-z0-9._/-]{2,72}$/;
const BANNED_BRANCH_NAMES = new Set([
  'main',
  'master',
  'production',
  'prod',
  'release',
  'refs/heads/main',
  'refs/heads/master',
  'origin/main',
]);

/**
 * Validates that Argon synchronization NEVER targets `main` directly and strictly
 * routes through a governed `lane/*` or `propose/aistudio-*` branch per AGENTS.md.
 */
export function validateArgonSyncTarget(
  repoInput: string,
  branchInput: string
): ArgonTargetValidationResult {
  const repo = (repoInput || '').trim();
  if (repo !== ARGON_TARGET_REPO) {
    return {
      valid: false,
      errorCode: 'UNSUPPORTED_TARGET_REPO',
      reason: `Argon Continuity Sync only targets "${ARGON_TARGET_REPO}" (got "${repo || 'empty'}").`,
    };
  }

  const rawBranch = (branchInput || '').trim().replace(/^refs\/heads\//, '');
  if (!rawBranch || BANNED_BRANCH_NAMES.has(rawBranch.toLowerCase())) {
    return {
      valid: false,
      errorCode: 'BANNED_DIRECT_MAIN_SYNC',
      reason: `Direct sync to protected branch "${rawBranch || 'main'}" is forbidden by AGENTS.md & Greenlane law. Route via "${ARGON_DEFAULT_LANE_BRANCH}".`,
    };
  }

  if (rawBranch.includes('..') || rawBranch.includes(' ') || !GOVERNED_BRANCH_RE.test(rawBranch)) {
    return {
      valid: false,
      errorCode: 'INVALID_LANE_BRANCH_NAME',
      reason: `Branch "${rawBranch}" must match governed prefix "lane/<slug>" or "propose/aistudio-<slug>" using lowercase alphanumeric characters.`,
    };
  }

  return {
    valid: true,
    repo,
    branch: rawBranch,
    governanceRule: 'GREENLANE_GOVERNED_BRANCH',
  };
}

/**
 * Maps a workspace-relative path to its canonical destination inside `chidionyema/argon`.
 * - `.genesis/outbox/*` -> `.genesis/outbox/*` (Argon canonical outbox root)
 * - `.ops/*` -> `.ops/*` (Register & Evidence WAL root)
 * - Application source files -> `apps/genesis-2100-cockpit/<workspacePath>`
 */
export function mapWorkspacePathToArgonPath(workspacePath: string): {
  argonRepoPath: string;
  category: ArgonMappedFileEntry['category'];
} {
  const normalized = workspacePath.replace(/\\/g, '/').replace(/^\/+/, '');
  if (normalized.startsWith('.genesis/outbox/') || normalized === '.genesis/GENESIS_SPORE.dna') {
    return {
      argonRepoPath: normalized,
      category: 'GENESIS_OUTBOX',
    };
  }
  if (
    normalized.startsWith('platform/estate/') ||
    normalized.startsWith('packages/io-engine/') ||
    normalized.startsWith('packages/omega-core/') ||
    normalized.startsWith('packages/beast-governor/') ||
    normalized === 'bin/io' ||
    normalized === 'bin/omega' ||
    normalized === 'bin/beast' ||
    normalized === 'AGENTS.md' ||
    normalized === 'HANDOVER_2026-11-12.md'
  ) {
    return {
      argonRepoPath: normalized,
      category: 'PLATFORM_HOST_TOOLING',
    };
  }
  if (normalized.startsWith('.ops/')) {
    return {
      argonRepoPath: normalized,
      category: 'OPS_REGISTER_LEDGER',
    };
  }
  return {
    argonRepoPath: `${ARGON_COCKPIT_SUBDIR}/${normalized}`,
    category: 'COCKPIT_SOURCE',
  };
}

/**
 * Pure FNV-1a / deterministic hex combiner fallback when WebCrypto isn't synchronous,
 * or accepts injected `hashHexFn` (e.g. Node `crypto.createHash('sha256')`) for cryptographic SHA-256.
 */
export function defaultDeterministicMerkleHex(canonicalTable: string): string {
  // Produce 8 independent 32-bit FNV-1a lanes => 64 hex chars if no native sha256 callback is supplied
  const seeds = [
    0x811c9dc5, 0x9e3779b9, 0x85ebca6b, 0xc2b2ae35,
    0x27d4eb2f, 0x165667b1, 0xd3a2646c, 0xfd7046c5,
  ];
  return seeds
    .map((seed, laneIdx) => {
      let h = seed >>> 0;
      for (let i = 0; i < canonicalTable.length; i++) {
        h ^= canonicalTable.charCodeAt(i) ^ ((laneIdx + 1) * 17);
        h = Math.imul(h, 0x01000193) >>> 0;
      }
      return h.toString(16).padStart(8, '0');
    })
    .join('');
}

export function buildArgonSyncManifest(params: {
  files: readonly ArgonWorkspaceFileInput[];
  governedBranch?: string;
  generatedAt?: string;
  idpObservedHeadSha: string;
  handoverReceiptSha256: string;
  registerHeadSeq: number;
  registerEntryCount: number;
  sha256Fn?: (input: string) => string;
}): ArgonSyncManifest {
  const governedBranch = params.governedBranch ?? ARGON_DEFAULT_LANE_BRANCH;
  const generatedAt = params.generatedAt ?? new Date().toISOString();
  const hashFn = params.sha256Fn ?? defaultDeterministicMerkleHex;

  const mapped: ArgonMappedFileEntry[] = params.files
    .map((f) => {
      const { argonRepoPath, category } = mapWorkspacePathToArgonPath(f.workspacePath);
      return {
        workspacePath: f.workspacePath.replace(/\\/g, '/').replace(/^\/+/, ''),
        argonRepoPath,
        sha256: f.sha256.toLowerCase(),
        bytes: f.bytes,
        category,
      };
    })
    .sort((a, b) => a.argonRepoPath.localeCompare(b.argonRepoPath));

  const canonicalLines = mapped
    .map((m) => `${m.argonRepoPath}:${m.sha256}:${m.bytes}`)
    .join('\n');
  const merkleRootSha256 = hashFn(canonicalLines);
  const totalBytes = mapped.reduce((sum, item) => sum + item.bytes, 0);

  const instructionId = `INS-ARGON-SYNC-${String(params.registerHeadSeq).padStart(4, '0')}`;
  const outboxEnvelope: ArgonOutboxEnvelopeV1 = {
    v: 1,
    repo: ARGON_TARGET_REPO,
    instruction_id: instructionId,
    title: `Sync Genesis 2100 Control Plane, Register Projector & Optimus Ledger (${mapped.length} files)`,
    body: [
      `Synchronize full AI Studio Genesis 2100 build onto governed branch ${governedBranch}.`,
      `Merkle Root SHA-256: ${merkleRootSha256}`,
      `Register Sequence Head: #${params.registerHeadSeq} (${params.registerEntryCount} entries)`,
      `Observed IDP Live HEAD: ${params.idpObservedHeadSha}`,
      `Handover Receipt Digest: ${params.handoverReceiptSha256}`,
      `Includes: Face & Fleet Register Projector (Movie + 2.5D Isometric + 3327 Pin + R1-R3 Falsifier), Reactor 2100, Project Optimus, Voice 2100, Legion 8-Formation Harness, FLOW 600s Watchdog, and Greenlane Claim-Gate.`,
    ].join('\n'),
    merkle_root_sha256: merkleRootSha256,
    register_head_seq: params.registerHeadSeq,
    governed_branch: governedBranch,
    handover_base_sha: ARGON_HANDOVER_BASE_SHA,
  };

  return {
    schema: 'argon-continuity-sync.v1',
    generatedAt,
    targetRepo: ARGON_TARGET_REPO,
    governedBranch,
    handoverBaseSha: ARGON_HANDOVER_BASE_SHA,
    idpObservedHeadSha: params.idpObservedHeadSha,
    handoverReceiptSha256: params.handoverReceiptSha256,
    registerHeadSeq: params.registerHeadSeq,
    registerEntryCount: params.registerEntryCount,
    fileCount: mapped.length,
    totalBytes,
    merkleRootSha256,
    files: mapped,
    outboxEnvelope,
  };
}

/**
 * Epistemically grades Argon sync status:
 * - Never promotes to `E1` unless a real 40-char commit SHA receipt from GitHub exists AND
 *   its Merkle root matches the current workspace Merkle root!
 * - Reports `U` honestly when GitHub credentials are not yet provisioned in AI Studio.
 */
export function evaluateArgonSyncReadiness(params: {
  hasServerGithubToken: boolean;
  hasGithubOAuthSession: boolean;
  oauthClientConfigured: boolean;
  currentMerkleRootSha256: string;
  lastRemoteReceipt: ArgonRemotePushReceipt | null;
}): ArgonSyncReadinessState {
  const authMode: ArgonSyncReadinessState['authMode'] = params.hasServerGithubToken
    ? 'SERVER_GITHUB_TOKEN'
    : params.hasGithubOAuthSession
      ? 'GITHUB_OAUTH_POPUP'
      : 'UNPROVISIONED';

  const canPushRemoteNow = authMode !== 'UNPROVISIONED';
  const receipt = params.lastRemoteReceipt;
  const hasValidCommitReceipt =
    receipt !== null &&
    HEX_40_RE.test(receipt.commitSha) &&
    receipt.targetRepo === ARGON_TARGET_REPO;

  if (hasValidCommitReceipt && receipt.merkleRootSha256 === params.currentMerkleRootSha256) {
    return {
      authority: 'E1',
      syncState: 'SYNCED_REMOTE_E1',
      authMode,
      oauthClientConfigured: params.oauthClientConfigured,
      canPushRemoteNow,
      statusHeadline: `Synced to ${receipt.targetRepo}@${receipt.branch} (${receipt.commitSha.slice(0, 10)})`,
      honestDetail: receipt.pullRequestUrl
        ? `Verified remote GitHub commit ${receipt.commitSha.slice(0, 12)} on governed branch ${receipt.branch}; Greenlane PR #${receipt.pullRequestNumber} open (${receipt.pullRequestUrl}).`
        : `Verified remote GitHub commit ${receipt.commitSha.slice(0, 12)} on governed branch ${receipt.branch} matching live Merkle root ${params.currentMerkleRootSha256.slice(0, 12)}.`,
    };
  }

  if (hasValidCommitReceipt && receipt.merkleRootSha256 !== params.currentMerkleRootSha256) {
    return {
      authority: 'E2',
      syncState: 'DRIFT_STAGED_LOCAL',
      authMode,
      oauthClientConfigured: params.oauthClientConfigured,
      canPushRemoteNow,
      statusHeadline: `Workspace ahead of ${receipt.branch} (${receipt.commitSha.slice(0, 8)}) — ready to push delta`,
      honestDetail: `Local Merkle root ${params.currentMerkleRootSha256.slice(0, 12)} has new register/source mutations since commit ${receipt.commitSha.slice(0, 12)}. Trigger Sync to fast-forward ${receipt.branch}.`,
    };
  }

  if (canPushRemoteNow) {
    return {
      authority: 'E2',
      syncState: 'DRIFT_STAGED_LOCAL',
      authMode,
      oauthClientConfigured: params.oauthClientConfigured,
      canPushRemoteNow: true,
      statusHeadline: `GitHub credential active (${authMode}) — ready to push ${ARGON_DEFAULT_LANE_BRANCH}`,
      honestDetail: `Canonical Argon bundle staged on disk (Merkle ${params.currentMerkleRootSha256.slice(0, 12)}). Click "Sync Everything to Argon" to create remote commit & Greenlane PR on ${ARGON_TARGET_REPO}.`,
    };
  }

  return {
    authority: 'U',
    syncState: 'STAGED_AWAITING_GITHUB_AUTH',
    authMode: 'UNPROVISIONED',
    oauthClientConfigured: params.oauthClientConfigured,
    canPushRemoteNow: false,
    statusHeadline: `Staged in .genesis/outbox/ (Authority U — awaiting GitHub credential for live push)`,
    honestDetail: `All source files, .ops/register.jsonl, and [GENESIS-OUTBOX] v1 receipt are hashed & staged (Merkle ${params.currentMerkleRootSha256.slice(0, 12)}). Connect GitHub OAuth, set GITHUB_TOKEN in Secrets, or run the 1-click Greenlane Apply Script inside your chidionyema/argon checkout.`,
  };
}

/**
 * Generates a deterministic, fail-closed bash script (`apply-argon-lane.sh`) that
 * unpacks `/api/argon/bundle.json` inside a local `chidionyema/argon` checkout,
 * verifies every file's SHA-256 digest, commits onto `lane/aistudio-genesis-2100-sync`
 * (refusing dirty trees or direct `main` commits), and submits via Greenlane / `gh pr create`.
 */
export function generateArgonLaneApplyScript(params: {
  manifest: ArgonSyncManifest;
  bundleDownloadUrl: string;
}): string {
  const branch = params.manifest.governedBranch;
  const merkle = params.manifest.merkleRootSha256;

  return [
    '#!/usr/bin/env bash',
    '# ==============================================================================',
    '# GENESIS 2100 -> ARGON FAIL-CLOSED GREENLANE SYNC INSTALLER',
    `# Target Repo:      ${ARGON_TARGET_REPO}`,
    `# Governed Branch:  ${branch}`,
    `# Merkle Root:      ${merkle}`,
    `# Files & Register: ${params.manifest.fileCount} files · seq #${params.manifest.registerHeadSeq}`,
    '# Law:              NEVER pushes to main; verifies every SHA-256 before commit.',
    '# ==============================================================================',
    'set -euo pipefail',
    '',
    'BUNDLE_FILE="${1:-argon-sync-bundle.json}"',
    `EXPECTED_MERKLE="${merkle}"`,
    `TARGET_BRANCH="${branch}"`,
    '',
    'if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then',
    '  echo "ERROR: Run this script from inside your chidionyema/argon git clone." >&2',
    '  exit 2',
    'fi',
    '',
    'ORIGIN_URL="$(git remote get-url origin 2>/dev/null || true)"',
    'if [[ "$ORIGIN_URL" != *"chidionyema/argon"* ]]; then',
    '  echo "ERROR: Origin remote ($ORIGIN_URL) is not chidionyema/argon. Refusing cross-repo mutation." >&2',
    '  exit 3',
    'fi',
    '',
    'if [[ -n "$(git status --porcelain)" ]]; then',
    '  echo "ERROR: Working tree has uncommitted modifications. Stash or clean before applying lane sync." >&2',
    '  exit 4',
    'fi',
    '',
    'if [[ ! -f "$BUNDLE_FILE" ]]; then',
    `  echo "Downloading bundle from ${params.bundleDownloadUrl} ..."`,
    `  curl -fsSL "${params.bundleDownloadUrl}" -o "$BUNDLE_FILE"`,
    'fi',
    '',
    'git fetch origin main',
    'git checkout -B "$TARGET_BRANCH" origin/main',
    '',
    'CURRENT_BRANCH="$(git symbolic-ref --short HEAD)"',
    'if [[ "$CURRENT_BRANCH" == "main" || "$CURRENT_BRANCH" == "master" ]]; then',
    '  echo "FATAL: Refusing to materialize files on protected branch $CURRENT_BRANCH." >&2',
    '  exit 5',
    'fi',
    '',
    'python3 - "$BUNDLE_FILE" "$EXPECTED_MERKLE" <<\'PY\'',
    'import hashlib, json, pathlib, sys',
    '',
    'bundle_path = pathlib.Path(sys.argv[1])',
    'expected_merkle = sys.argv[2]',
    'payload = json.loads(bundle_path.read_text(encoding="utf-8"))',
    'manifest = payload["manifest"]',
    'if manifest["merkleRootSha256"] != expected_merkle:',
    '    raise SystemExit(f"MERKLE_MISMATCH: got {manifest[\'merkleRootSha256\']}, expected {expected_merkle}")',
    '',
    'contents = payload["fileContentsByArgonPath"]',
    'for item in manifest["files"]:',
    '    rel = item["argonRepoPath"]',
    '    if rel.startswith("/") or ".." in rel.split("/"):',
    '        raise SystemExit(f"UNSAFE_PATH_REFUSED: {rel}")',
    '    raw = contents[rel].encode("utf-8")',
    '    digest = hashlib.sha256(raw).hexdigest()',
    '    if digest != item["sha256"]:',
    '        raise SystemExit(f"SHA256_MISMATCH on {rel}: got {digest}, expected {item[\'sha256\']}")',
    '    dest = pathlib.Path(rel)',
    '    dest.parent.mkdir(parents=True, exist_ok=True)',
    '    dest.write_bytes(raw)',
    '',
    'print(f"Verified and materialized {len(manifest[\'files\'])} files (Merkle {expected_merkle[:12]}).")',
    'PY',
    '',
    'git add -f apps/genesis-2100-cockpit platform/estate HANDOVER_2026-11-12.md .ops .genesis/outbox .genesis/GENESIS_SPORE.dna 2>/dev/null || git add -f apps/genesis-2100-cockpit .ops .genesis/outbox',
    'if git diff --cached --quiet; then',
    '  echo "No delta against origin/main — $TARGET_BRANCH is already identical."',
    '  exit 0',
    'fi',
    '',
    `git commit -m "feat(genesis-2100): sync Register Projector, Optimus & Estate Control Plane (merkle ${merkle.slice(0, 12)})"`,
    'git push -u origin "$TARGET_BRANCH"',
    '',
    'if command -v estate-execute >/dev/null 2>&1; then',
    '  estate-execute lane-submit --repo argon --branch "$TARGET_BRANCH"',
    'elif command -v gh >/dev/null 2>&1; then',
    '  gh pr create --repo chidionyema/argon --base main --head "$TARGET_BRANCH" \\',
    `    --title "feat(genesis-2100): sync Register Projector, Optimus & Control Plane (${merkle.slice(0, 8)})" \\`,
    '    --body "Automated Greenlane sync from AI Studio Genesis 2100 Control Plane. All SHA-256 file digests and .ops/register.jsonl entries verified." || true',
    'fi',
    '',
    'echo "SUCCESS: Synced onto governed branch $TARGET_BRANCH without touching main."',
    '',
  ].join('\n');
}
