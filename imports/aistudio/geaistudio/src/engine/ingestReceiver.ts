/**
 * Fail-Closed Genesis Bundle Ingest Receiver & Estate Session Wake Reconciler.
 * Solves "the other side" when dist-exports/meridian-hermes-today.bundle lands from AI Studio:
 *   1. Re-computes SHA-256 over raw received body bytes and timing-safe compares to X-Bundle-Sha256 (fail-closed 401).
 *   2. Verifies bundle integrity via `git bundle verify` inside isolated staging before touching estate state.
 *   3. Tracks estate worker sessions: wakes an existing IDLE session if available, otherwise spawns a new session.
 */

import { createHash, randomUUID, timingSafeEqual } from 'node:crypto';
import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';

export type WakeDisposition = 'WOKEN_IDLE_SESSION' | 'SPAWNED_NEW_SESSION';

export interface EstateSessionRecord {
  sessionId: string;
  workerId: string;
  agent: string;
  sourceAppUrl: string;
  status: 'IDLE' | 'RUNNING';
  wakeCount: number;
  lastBundleSha256: string | null;
  lastHeadSha: string | null;
  lastTargetRef: string | null;
  lastWokenAtUtc: string | null;
  createdAtUtc: string;
}

export interface WakeEventRecord {
  wakeEventId: string;
  timestampUtc: string;
  disposition: WakeDisposition;
  workerId: string;
  sessionId: string;
  verifiedSha256: string;
  bundleBytes: number;
  targetRef: string;
  targetRemotes: string[];
  bundlePath: string;
}

export interface IngestReceiverState {
  sessionsByWorkerId: Map<string, EstateSessionRecord>;
  wakeEvents: WakeEventRecord[];
  acceptedCount: number;
  rejectedCount: number;
}

export const MAX_WAKE_EVENTS = 100;
export const MAX_GEMINI_SYNC_BUNDLE_BYTES = 16 * 1024 * 1024; // 16 MiB ceiling (#7760 / gemini-sync)

export function createIngestReceiverState(
  seedIdleSessions: EstateSessionRecord[] = []
): IngestReceiverState {
  const sessionsByWorkerId = new Map<string, EstateSessionRecord>();
  for (const s of seedIdleSessions) {
    sessionsByWorkerId.set(s.workerId, { ...s });
  }
  return {
    sessionsByWorkerId,
    wakeEvents: [],
    acceptedCount: 0,
    rejectedCount: 0,
  };
}

export function markSessionIdle(state: IngestReceiverState, workerId: string): boolean {
  const existing = state.sessionsByWorkerId.get(workerId);
  if (!existing) return false;
  existing.status = 'IDLE';
  return true;
}

export interface HandleIngestInput {
  bodyBytes: Buffer;
  claimedSha256?: string;
  authHeader?: string;
  expectedAuthToken?: string;
  sessionId?: string;
  wakePolicy?: string;
  wakeAgent?: string;
  appUrl?: string;
  targetRef?: string;
  targetRemotes?: string[];
  headSha?: string;
  stagingDir: string;
  state: IngestReceiverState;
  onWakeSession?: (
    session: EstateSessionRecord,
    event: WakeEventRecord
  ) => void | Promise<void>;
}

export interface HandleIngestOutput {
  httpStatus: number;
  accepted: boolean;
  error?: string;
  verifiedSha256?: string;
  independentReadbackVerified?: boolean;
  storedBytes?: number;
  wakeDisposition?: WakeDisposition;
  wokenSessionId?: string;
  workerId?: string;
  wakeCount?: number;
  bundlePath?: string;
  targetRemotes?: string[];
}

function timingSafeHexEqual(a: string, b: string): boolean {
  const cleanA = a.trim().toLowerCase();
  const cleanB = b.trim().toLowerCase();
  if (cleanA.length !== 64 || cleanB.length !== 64) return false;
  if (!/^[0-9a-f]{64}$/.test(cleanA) || !/^[0-9a-f]{64}$/.test(cleanB)) return false;
  return timingSafeEqual(Buffer.from(cleanA, 'hex'), Buffer.from(cleanB, 'hex'));
}

function timingSafeUtf8Equal(a: string, b: string): boolean {
  const ba = Buffer.from(a, 'utf8');
  const bb = Buffer.from(b, 'utf8');
  if (ba.length === 0 || ba.length !== bb.length) return false;
  return timingSafeEqual(ba, bb);
}

export async function handleIngestBundleRequest(
  input: HandleIngestInput
): Promise<HandleIngestOutput> {
  const { bodyBytes, stagingDir, state } = input;
  if (input.expectedAuthToken !== undefined) {
    const expected = input.expectedAuthToken.trim();
    const authRaw = (input.authHeader ?? '').trim();
    const bearer = authRaw.startsWith('Bearer ') ? authRaw.slice(7).trim() : authRaw;
    if (!expected || !timingSafeUtf8Equal(bearer, expected)) {
      state.rejectedCount++;
      return { httpStatus: 401, accepted: false, error: 'unauthorized_receiver_token_fail_closed' };
    }
  }

  if (!Buffer.isBuffer(bodyBytes) || bodyBytes.byteLength === 0) {
    state.rejectedCount++;
    return { httpStatus: 400, accepted: false, error: 'empty_bundle_payload' };
  }
  if (bodyBytes.byteLength > MAX_GEMINI_SYNC_BUNDLE_BYTES) {
    state.rejectedCount++;
    return {
      httpStatus: 413,
      accepted: false,
      error: 'bundle_exceeds_16mib_gemini_sync_limit',
    };
  }

  const claimed = (input.claimedSha256 ?? '').trim();
  if (!claimed) {
    state.rejectedCount++;
    return { httpStatus: 401, accepted: false, error: 'missing_x_bundle_sha256_fail_closed' };
  }

  const computedSha256 = createHash('sha256').update(bodyBytes).digest('hex');
  if (!timingSafeHexEqual(computedSha256, claimed)) {
    state.rejectedCount++;
    return {
      httpStatus: 401,
      accepted: false,
      error: 'sha256_mismatch_fail_closed',
    };
  }

  fs.mkdirSync(stagingDir, { recursive: true });
  const stagedBundlePath = path.join(stagingDir, `bundle-${computedSha256.slice(0, 12)}.bundle`);
  fs.writeFileSync(stagedBundlePath, bodyBytes);

  // Mandatory independent byte readback from durable filesystem staging before trusting write
  const readbackBytes = fs.readFileSync(stagedBundlePath);
  const readbackSha = createHash('sha256').update(readbackBytes).digest('hex');
  if (
    readbackBytes.byteLength !== bodyBytes.byteLength ||
    !timingSafeHexEqual(readbackSha, computedSha256)
  ) {
    try {
      fs.unlinkSync(stagedBundlePath);
    } catch {
      // Ignore cleanup failure
    }
    state.rejectedCount++;
    return {
      httpStatus: 500,
      accepted: false,
      error: 'corrupted_storage_readback_mismatch',
    };
  }

  // Verify bundle cryptographic DAG structure via git bundle verify
  // Run inside an isolated temporary bare repo check if outside a repo, or git bundle verify directly
  try {
    const verifyRepo = path.join(stagingDir, '.verify-repo');
    if (!fs.existsSync(path.join(verifyRepo, 'HEAD'))) {
      fs.mkdirSync(verifyRepo, { recursive: true });
      execFileSync('git', ['-c', `safe.directory=${verifyRepo}`, 'init', '--bare'], {
        cwd: verifyRepo,
        stdio: 'ignore',
      });
    }
    execFileSync(
      'git',
      ['-c', `safe.directory=${verifyRepo}`, 'bundle', 'verify', stagedBundlePath],
      {
        cwd: verifyRepo,
        stdio: ['ignore', 'pipe', 'pipe'],
      }
    );
  } catch (err) {
    state.rejectedCount++;
    return {
      httpStatus: 400,
      accepted: false,
      error: `invalid_git_bundle: ${err instanceof Error ? err.message : 'verify failed'}`,
    };
  }

  const nowUtc = new Date().toISOString();
  const sessionId = (input.sessionId ?? 'aistudio-default').trim();
  const agent = (input.wakeAgent ?? 'pennyd-sync-reconciler').trim();
  const targetRef = (input.targetRef ?? 'refs/heads/aistudio/meridian-hermes-live').trim();
  const targetRemotes = input.targetRemotes ?? ['chidionyema/argon-sync', 'chidionyema/gemini-sync'];
  const sourceAppUrl = (input.appUrl ?? 'aistudio-container').trim();

  // 1. Prefer an IDLE session already matching sessionId; 2. otherwise any IDLE worker for same agent
  let selectedSession: EstateSessionRecord | undefined;
  for (const s of state.sessionsByWorkerId.values()) {
    if (s.status === 'IDLE' && s.sessionId === sessionId) {
      selectedSession = s;
      break;
    }
  }
  if (!selectedSession) {
    for (const s of state.sessionsByWorkerId.values()) {
      if (s.status === 'IDLE' && s.agent === agent) {
        selectedSession = s;
        break;
      }
    }
  }

  let disposition: WakeDisposition;
  if (selectedSession) {
    disposition = 'WOKEN_IDLE_SESSION';
    selectedSession.status = 'RUNNING';
    selectedSession.sessionId = sessionId;
    selectedSession.sourceAppUrl = sourceAppUrl;
    selectedSession.wakeCount += 1;
    selectedSession.lastBundleSha256 = computedSha256;
    selectedSession.lastHeadSha = input.headSha ?? null;
    selectedSession.lastTargetRef = targetRef;
    selectedSession.lastWokenAtUtc = nowUtc;
  } else {
    disposition = 'SPAWNED_NEW_SESSION';
    const workerId = `worker-${randomUUID().slice(0, 8)}`;
    selectedSession = {
      sessionId,
      workerId,
      agent,
      sourceAppUrl,
      status: 'RUNNING',
      wakeCount: 1,
      lastBundleSha256: computedSha256,
      lastHeadSha: input.headSha ?? null,
      lastTargetRef: targetRef,
      lastWokenAtUtc: nowUtc,
      createdAtUtc: nowUtc,
    };
    state.sessionsByWorkerId.set(workerId, selectedSession);
  }

  const event: WakeEventRecord = {
    wakeEventId: `wake-${randomUUID().slice(0, 8)}`,
    timestampUtc: nowUtc,
    disposition,
    workerId: selectedSession.workerId,
    sessionId: selectedSession.sessionId,
    verifiedSha256: computedSha256,
    bundleBytes: bodyBytes.byteLength,
    targetRef,
    targetRemotes,
    bundlePath: stagedBundlePath,
  };

  state.wakeEvents.unshift(event);
  if (state.wakeEvents.length > MAX_WAKE_EVENTS) {
    state.wakeEvents.length = MAX_WAKE_EVENTS;
  }
  state.acceptedCount += 1;

  if (input.onWakeSession) {
    await input.onWakeSession(selectedSession, event);
  }

  return {
    httpStatus: 202,
    accepted: true,
    verifiedSha256: computedSha256,
    independentReadbackVerified: true,
    storedBytes: readbackBytes.byteLength,
    wakeDisposition: disposition,
    wokenSessionId: selectedSession.sessionId,
    workerId: selectedSession.workerId,
    wakeCount: selectedSession.wakeCount,
    bundlePath: stagedBundlePath,
    targetRemotes,
  };
}
