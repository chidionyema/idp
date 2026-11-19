import { CapSaveResult, ClientKeyRecord } from './types';

/**
 * Structural key ledger managing atomic cap-save updates without clobbering
 * sibling keys. Mirrors TOML serialization + temp-file invariant checks +
 * multi-key verification before committing.
 */
export class AtomicKeyStore {
  private keys: Map<string, ClientKeyRecord>;
  private rawTomlSnapshot: string;

  constructor(initialKeys: ClientKeyRecord[]) {
    this.keys = new Map();
    for (const k of initialKeys) {
      this.keys.set(k.id, { ...k });
    }
    this.rawTomlSnapshot = this.serializeToToml(Array.from(this.keys.values()));
  }

  public getAllKeys(): ClientKeyRecord[] {
    return Array.from(this.keys.values()).map((k) => ({ ...k }));
  }

  public findByRawKey(rawKey: string): ClientKeyRecord | undefined {
    for (const record of this.keys.values()) {
      if (record.rawKey === rawKey && record.active) {
        return { ...record };
      }
    }
    return undefined;
  }

  public getTomlSnapshot(): string {
    return this.rawTomlSnapshot;
  }

  public recordSpend(keyId: string, amountUsd: number): void {
    const existing = this.keys.get(keyId);
    if (!existing) return;
    existing.spentTodayUsd = Number((existing.spentTodayUsd + amountUsd).toFixed(6));
  }

  /**
   * Atomically updates a single client key's daily budget ceiling in-place,
   * preserving every other key block, validating `nextKeys.length >= prevKeys.length`,
   * and running a pre-commit probe on ALL active keys (eliminating single-key canary blindness).
   */
  public atomicCapSave(
    targetKeyId: string,
    newDailyBudgetUsd: number,
    options?: { simulateLegacyClobberBug?: boolean }
  ): CapSaveResult {
    if (!Number.isFinite(newDailyBudgetUsd) || newDailyBudgetUsd <= 0 || newDailyBudgetUsd > 100000) {
      return {
        ok: false,
        updatedKeyId: targetKeyId,
        previousBudgetUsd: this.keys.get(targetKeyId)?.dailyBudgetUsd ?? 0,
        newBudgetUsd: newDailyBudgetUsd,
        preservedKeyCount: this.keys.size,
        verifiedKeys: [],
        error: 'Invalid daily budget ceiling: must be > $0 and <= $100,000.',
      };
    }

    const prevKeys = this.getAllKeys();
    const target = prevKeys.find((k) => k.id === targetKeyId);
    if (!target) {
      return {
        ok: false,
        updatedKeyId: targetKeyId,
        previousBudgetUsd: 0,
        newBudgetUsd: newDailyBudgetUsd,
        preservedKeyCount: prevKeys.length,
        verifiedKeys: [],
        error: `Client key '${targetKeyId}' not found in ledger.`,
      };
    }

    const previousBudgetUsd = target.dailyBudgetUsd;
    const nowIso = new Date().toISOString();

    // Stage candidate state
    let candidateKeys: ClientKeyRecord[];
    if (options?.simulateLegacyClobberBug) {
      // Simulates the legacy bug where cap-save overwrote keys.toml with only 1 key
      candidateKeys = [{ ...target, dailyBudgetUsd: newDailyBudgetUsd, lastVerifiedAt: nowIso }];
    } else {
      candidateKeys = prevKeys.map((k) =>
        k.id === targetKeyId
          ? { ...k, dailyBudgetUsd: newDailyBudgetUsd, lastVerifiedAt: nowIso }
          : { ...k }
      );
    }

    // Pre-commit structural invariant check: never allow key count shrinkage
    if (candidateKeys.length < prevKeys.length) {
      return {
        ok: false,
        updatedKeyId: targetKeyId,
        previousBudgetUsd,
        newBudgetUsd: newDailyBudgetUsd,
        preservedKeyCount: prevKeys.length,
        verifiedKeys: prevKeys.map((k) => ({
          id: k.id,
          label: k.label,
          valid: true,
        })),
        rolledBack: true,
        error: `Atomic invariant rejected commit: candidate key count (${candidateKeys.length}) < previous count (${prevKeys.length}). Rolled back.`,
      };
    }

    // Serialize to candidate TOML and re-parse to verify round-trip fidelity
    const candidateToml = this.serializeToToml(candidateKeys);
    const parsedBack = this.parseTomlKeyIds(candidateToml);
    const verifiedKeys = prevKeys.map((k) => ({
      id: k.id,
      label: k.label,
      valid: parsedBack.includes(k.id) && candidateKeys.some((c) => c.id === k.id && c.active && c.rawKey.length > 0),
    }));

    const allValid = verifiedKeys.every((v) => v.valid);
    if (!allValid) {
      return {
        ok: false,
        updatedKeyId: targetKeyId,
        previousBudgetUsd,
        newBudgetUsd: newDailyBudgetUsd,
        preservedKeyCount: prevKeys.length,
        verifiedKeys,
        rolledBack: true,
        error: 'Multi-key pre-commit probe failed for one or more client keys. Rolled back.',
      };
    }

    // Atomic swap
    const nextMap = new Map<string, ClientKeyRecord>();
    for (const k of candidateKeys) {
      k.lastProbeStatus = 'pass';
      nextMap.set(k.id, k);
    }
    this.keys = nextMap;
    this.rawTomlSnapshot = candidateToml;

    return {
      ok: true,
      updatedKeyId: targetKeyId,
      previousBudgetUsd,
      newBudgetUsd: newDailyBudgetUsd,
      preservedKeyCount: this.keys.size,
      verifiedKeys,
    };
  }

  public verifyAllActiveKeys(): Array<{ id: string; label: string; valid: boolean }> {
    const parsedIds = this.parseTomlKeyIds(this.rawTomlSnapshot);
    return this.getAllKeys().map((k) => ({
      id: k.id,
      label: k.label,
      valid: k.active && parsedIds.includes(k.id) && k.rawKey.startsWith('pk_'),
    }));
  }

  private serializeToToml(records: ClientKeyRecord[]): string {
    return records
      .map(
        (k) =>
          `[clients.${k.id}]\nlabel = "${k.label}"\nbound_client = "${k.boundClient}"\nkey_hash = "${k.keyHash}"\ndaily_budget_usd = ${k.dailyBudgetUsd}\nactive = ${k.active}`
      )
      .join('\n\n');
  }

  private parseTomlKeyIds(toml: string): string[] {
    const ids: string[] = [];
    const regex = /^\[clients\.([a-zA-Z0-9_-]+)\]/gm;
    let match: RegExpExecArray | null;
    while ((match = regex.exec(toml)) !== null) {
      ids.push(match[1]);
    }
    return ids;
  }
}
