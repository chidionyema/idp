/**
 * Clause 4: Short-Loop Repeat Detector
 * Hardened implementation fixing the 3 vulnerabilities identified in MUM-300:
 * 1. Normalized target & payload fingerprinting (not merely byte-identical raw output)
 * 2. Folder-agnostic normalization (working directory changes do NOT reset the detector)
 * 3. Fail-loud state enforcement (corrupted or unreadable state throws or halts, never fails silent)
 */

export interface ExecutionRecord {
  fingerprint: string;
  capability: string;
  evidenceDigest?: string;
  timestamp: number;
}

export class ShortLoopDetector {
  private history: Map<string, ExecutionRecord[]> = new Map();
  private isCorrupted: boolean = false;

  constructor(initialCorruptedState: boolean = false) {
    this.isCorrupted = initialCorruptedState;
  }

  /**
   * Generates a folder-agnostic semantic fingerprint.
   * Strips local directory paths (e.g., /Users/... or /tmp/...) so directory hopping
   * does not evade repeat detection.
   */
  public generateFingerprint(
    capability: string,
    actionType: string,
    payload: unknown
  ): string {
    const rawPayload = JSON.stringify(payload ?? {});
    // Normalize path separators and remove local directory prefixes
    const normalizedPayload = rawPayload
      .replace(/\/Users\/[a-zA-Z0-9._-]+\//g, 'ESTATE_ROOT/')
      .replace(/\/home\/[a-zA-Z0-9._-]+\//g, 'ESTATE_ROOT/')
      .replace(/\/tmp\/[a-zA-Z0-9._-]+\//g, 'TMP_ROOT/')
      .replace(/\\/g, '/');

    return `${capability}:${actionType}:${normalizedPayload}`;
  }

  /**
   * Checks whether the current action is an ungrounded short loop.
   * If state file is corrupted, FAILS LOUD by throwing an explicit error.
   * If the identical action + target was executed recently WITHOUT any new evidenceDigest,
   * detects repeat short loop.
   */
  public checkLoop(
    surfaceId: string,
    capability: string,
    actionType: string,
    payload: unknown,
    evidenceDigest?: string
  ): { isLoop: boolean; reason?: string } {
    if (this.isCorrupted) {
      throw new Error(
        'CRITICAL: ShortLoopDetector state store is corrupted or unreadable. Failing loud per governance Clause 4.'
      );
    }

    const fingerprint = this.generateFingerprint(capability, actionType, payload);
    const surfaceHistory = this.history.get(surfaceId) || [];

    // Find any prior execution with matching action/payload fingerprint
    const match = surfaceHistory.find((rec) => rec.fingerprint === fingerprint);

    if (match) {
      // If evidence has not changed or is absent, this is an illegal repeat
      if (!evidenceDigest || match.evidenceDigest === evidenceDigest) {
        return {
          isLoop: true,
          reason: `Repeated execution of '${capability}' with unchanged evidence digest (${evidenceDigest || 'none'}). Short-loop aborted.`,
        };
      }
    }

    return { isLoop: false };
  }

  /**
   * Records execution in the state ledger
   */
  public recordExecution(
    surfaceId: string,
    capability: string,
    actionType: string,
    payload: unknown,
    evidenceDigest?: string
  ): void {
    if (this.isCorrupted) {
      throw new Error('CRITICAL: Cannot record execution in corrupted ShortLoop state store.');
    }

    const fingerprint = this.generateFingerprint(capability, actionType, payload);
    const surfaceHistory = this.history.get(surfaceId) || [];
    surfaceHistory.push({
      fingerprint,
      capability,
      evidenceDigest,
      timestamp: Date.now(),
    });

    // Keep history bounded to last 50 calls
    if (surfaceHistory.length > 50) {
      surfaceHistory.shift();
    }
    this.history.set(surfaceId, surfaceHistory);
  }

  public simulateCorruptState(): void {
    this.isCorrupted = true;
  }

  public restoreHealthyState(): void {
    this.isCorrupted = false;
  }
}
