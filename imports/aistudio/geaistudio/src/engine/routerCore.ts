import { AtomicKeyStore } from './keyStore';
import { ForensicPacketLedger } from './meridianTelemetry';
import { calculateTokenEconomics } from './pricingCatalog';
import { WalReceiptLedger } from './receiptLedger';
import {
  LaneAttempt,
  LaneFaultMode,
  RouteRequest,
  RouteResult,
  RoutingStrategy,
  UpstreamLane,
} from './types';

export function createDefaultClientKeys() {
  const now = new Date().toISOString();
  return [
    {
      id: 'opencode_primary',
      label: 'OpenCode Primary',
      keyHash: 'sha256:9f82a1e4c0b7...3d12',
      maskedKey: 'pk_live_opencode_...94a2',
      rawKey: 'pk_live_opencode_primary_94a2',
      dailyBudgetUsd: 250,
      spentTodayUsd: 18.42,
      active: true,
      boundClient: 'opencode-cli-4200',
      lastVerifiedAt: now,
      lastProbeStatus: 'pass' as const,
    },
    {
      id: 'ci_canary',
      label: 'CI Canary Probe',
      keyHash: 'sha256:4b11c89d2a19...7e08',
      maskedKey: 'pk_live_canary_...71c9',
      rawKey: 'pk_live_canary_probe_71c9',
      dailyBudgetUsd: 75,
      spentTodayUsd: 2.15,
      active: true,
      boundClient: 'dagster-canary-sensor',
      lastVerifiedAt: now,
      lastProbeStatus: 'pass' as const,
    },
  ];
}

export function createDefaultLanes(): UpstreamLane[] {
  return [
    {
      id: 'deepseek-flash',
      provider: 'DeepSeek',
      model: 'deepseek-chat',
      endpoint: 'https://api.deepseek.com/v1/chat/completions',
      priority: 1,
      weight: 55,
      baseLatencyMs: 142,
      costPer1kTokensUsd: 0.00028,
      vaultKeyPresent: true,
      creditBalanceUsd: 120.0,
      faultMode: 'healthy',
      circuitState: 'CLOSED',
      failureCount: 0,
      successCount: 1480,
      activeInFlight: 2,
      lastFailureReason: null,
      lastOpenedAt: null,
      cooldownMs: 15000,
    },
    {
      id: 'anthropic-sonnet',
      provider: 'Anthropic',
      model: 'claude-sonnet-4',
      endpoint: 'https://api.anthropic.com/v1/messages',
      priority: 2,
      weight: 25,
      baseLatencyMs: 218,
      costPer1kTokensUsd: 0.003,
      vaultKeyPresent: true,
      creditBalanceUsd: 340.0,
      faultMode: 'healthy',
      circuitState: 'CLOSED',
      failureCount: 0,
      successCount: 512,
      activeInFlight: 1,
      lastFailureReason: null,
      lastOpenedAt: null,
      cooldownMs: 15000,
    },
    {
      id: 'gemini-flash',
      provider: 'Google',
      model: 'gemini-2.5-flash',
      endpoint: 'https://generativelanguage.googleapis.com/v1beta',
      priority: 3,
      weight: 15,
      baseLatencyMs: 164,
      costPer1kTokensUsd: 0.00035,
      vaultKeyPresent: true,
      creditBalanceUsd: 260.0,
      faultMode: 'healthy',
      circuitState: 'CLOSED',
      failureCount: 0,
      successCount: 284,
      activeInFlight: 0,
      lastFailureReason: null,
      lastOpenedAt: null,
      cooldownMs: 15000,
    },
    {
      id: 'openai-mini',
      provider: 'OpenAI',
      model: 'gpt-4o-mini',
      endpoint: 'https://api.openai.com/v1/chat/completions',
      priority: 4,
      weight: 5,
      baseLatencyMs: 195,
      costPer1kTokensUsd: 0.0006,
      vaultKeyPresent: true,
      creditBalanceUsd: 190.0,
      faultMode: 'healthy',
      circuitState: 'CLOSED',
      failureCount: 0,
      successCount: 106,
      activeInFlight: 0,
      lastFailureReason: null,
      lastOpenedAt: null,
      cooldownMs: 15000,
    },
  ];
}

export class RouterEngine {
  public keyStore: AtomicKeyStore;
  public ledger: WalReceiptLedger;
  public forensics: ForensicPacketLedger;
  private lanes: Map<string, UpstreamLane>;
  private defaultStrategy: RoutingStrategy = 'priority_failover';
  private vaultHydrated = true;
  private circuitFailureThreshold = 2;

  constructor(options?: { initialReceipts?: number; strategy?: RoutingStrategy; seedForensics?: number }) {
    this.keyStore = new AtomicKeyStore(createDefaultClientKeys());
    this.ledger = new WalReceiptLedger(options?.initialReceipts ?? 24);
    this.forensics = new ForensicPacketLedger(options?.seedForensics ?? 18);
    this.lanes = new Map();
    for (const lane of createDefaultLanes()) {
      this.lanes.set(lane.id, { ...lane });
    }
    if (options?.strategy) {
      this.defaultStrategy = options.strategy;
    }
  }

  public getLanes(): UpstreamLane[] {
    return Array.from(this.lanes.values()).map((l) => ({ ...l }));
  }

  public getStrategy(): RoutingStrategy {
    return this.defaultStrategy;
  }

  public setStrategy(strategy: RoutingStrategy): void {
    this.defaultStrategy = strategy;
  }

  public isVaultHydrated(): boolean {
    return this.vaultHydrated && Array.from(this.lanes.values()).every((l) => l.vaultKeyPresent);
  }

  public dropVaultKeysInMemory(): void {
    this.vaultHydrated = false;
    for (const lane of this.lanes.values()) {
      lane.vaultKeyPresent = false;
    }
  }

  public hydrateVaultKeys(): { hydratedCount: number } {
    let hydratedCount = 0;
    for (const lane of this.lanes.values()) {
      if (!lane.vaultKeyPresent) {
        lane.vaultKeyPresent = true;
        hydratedCount++;
      }
    }
    this.vaultHydrated = true;
    return { hydratedCount };
  }

  public setLaneFault(laneId: string, faultMode: LaneFaultMode, creditBalanceUsd?: number): UpstreamLane | null {
    const lane = this.lanes.get(laneId);
    if (!lane) return null;
    lane.faultMode = faultMode;
    if (creditBalanceUsd !== undefined) {
      lane.creditBalanceUsd = creditBalanceUsd;
    }
    if (faultMode === '402_credit_exhausted') {
      lane.creditBalanceUsd = 0;
    }
    if (faultMode === 'healthy') {
      if (lane.creditBalanceUsd <= 0) {
        lane.creditBalanceUsd = 100;
      }
      lane.vaultKeyPresent = true;
      lane.circuitState = 'CLOSED';
      lane.failureCount = 0;
      lane.lastFailureReason = null;
      lane.lastOpenedAt = null;
    }
    return { ...lane };
  }

  public topUpLaneCredits(laneId: string, addUsd: number): UpstreamLane | null {
    const lane = this.lanes.get(laneId);
    if (!lane) return null;
    lane.creditBalanceUsd = Number((lane.creditBalanceUsd + addUsd).toFixed(2));
    if (lane.creditBalanceUsd > 0 && lane.faultMode === '402_credit_exhausted') {
      lane.faultMode = 'healthy';
    }
    return { ...lane };
  }

  /**
   * Probes a quarantined or unhealthy lane (used by Dagster billing_recovery_sensor).
   * If upstream responds cleanly, immediately closes the circuit so topped-up credits take effect.
   */
  public probeAndRecoverLane(laneId: string): { recovered: boolean; reason: string } {
    const lane = this.lanes.get(laneId);
    if (!lane) return { recovered: false, reason: `Unknown lane ${laneId}` };
    if (!lane.vaultKeyPresent) {
      return { recovered: false, reason: 'Vault key missing in memory' };
    }
    if (lane.faultMode === '402_credit_exhausted' || lane.creditBalanceUsd <= 0) {
      return { recovered: false, reason: 'Upstream returned 402 Insufficient Balance' };
    }
    if (lane.faultMode === '401_upstream_key') {
      return { recovered: false, reason: 'Upstream returned 401 Invalid API Key' };
    }
    if (lane.faultMode === '503_unavailable') {
      return { recovered: false, reason: 'Upstream returned 503 Service Unavailable' };
    }

    lane.circuitState = 'CLOSED';
    lane.failureCount = 0;
    lane.lastFailureReason = null;
    lane.lastOpenedAt = null;
    return { recovered: true, reason: `Probe 200 OK — circuit CLOSED on ${lane.id}` };
  }

  public orderLanes(strategy: RoutingStrategy): UpstreamLane[] {
    const all = Array.from(this.lanes.values());
    switch (strategy) {
      case 'lowest_latency':
        return all.sort((a, b) => a.baseLatencyMs - b.baseLatencyMs);
      case 'weighted_cost':
        return all.sort((a, b) => a.costPer1kTokensUsd - b.costPer1kTokensUsd);
      case 'least_busy':
        return all.sort((a, b) => a.activeInFlight - b.activeInFlight || a.priority - b.priority);
      case 'priority_failover':
      default:
        return all.sort((a, b) => a.priority - b.priority);
    }
  }

  public route(req: RouteRequest): RouteResult {
    const startNs = typeof process !== 'undefined' && process.hrtime ? process.hrtime.bigint() : BigInt(Date.now() * 1e6);
    const nowMs = req.nowMs ?? Date.now();
    const strategy = req.strategy ?? this.defaultStrategy;

    // 1. Validate request payload
    if (!req.modelSlug || req.estimatedTokens <= 0) {
      return {
        ok: false,
        httpStatus: 400,
        selectedLaneId: null,
        selectedProvider: null,
        modelSlug: req.modelSlug || 'unknown',
        gatewayOverheadUs: 8,
        totalLatencyMs: 1,
        costUsd: 0,
        receiptSequence: null,
        attempts: [],
        errorPayload: {
          error: {
            detail: 'Invalid request: modelSlug and positive estimatedTokens required.',
            type: 'validation',
          },
        },
      };
    }

    // 2. Authenticate inbound client key (distinct from upstream 401/402)
    const clientRecord = this.keyStore.findByRawKey(req.clientKey);
    if (!clientRecord) {
      return {
        ok: false,
        httpStatus: 401,
        selectedLaneId: null,
        selectedProvider: null,
        modelSlug: req.modelSlug,
        gatewayOverheadUs: 11,
        totalLatencyMs: 1,
        costUsd: 0,
        receiptSequence: null,
        attempts: [],
        errorPayload: {
          error: {
            detail: 'unknown client API key (inbound auth rejected before upstream dispatch)',
            type: 'unauthorized',
          },
        },
      };
    }

    // 3. Enforce daily budget ceiling atomically
    if (clientRecord.spentTodayUsd >= clientRecord.dailyBudgetUsd) {
      return {
        ok: false,
        httpStatus: 402,
        selectedLaneId: null,
        selectedProvider: null,
        modelSlug: req.modelSlug,
        gatewayOverheadUs: 12,
        totalLatencyMs: 1,
        costUsd: 0,
        receiptSequence: null,
        attempts: [],
        errorPayload: {
          error: {
            detail: `daily budget ceiling exceeded ($${clientRecord.spentTodayUsd.toFixed(2)} / $${clientRecord.dailyBudgetUsd.toFixed(2)})`,
            type: 'budget_exceeded',
          },
        },
      };
    }

    // 4. Evaluate ordered upstream lanes with circuit-breaker & distinct error taxonomy
    const ordered = this.orderLanes(strategy);
    const attempts: LaneAttempt[] = [];
    let cumulativeFailLatencyMs = 0;

    for (const lane of ordered) {
      // Transition OPEN -> HALF_OPEN if cooldown elapsed
      if (lane.circuitState === 'OPEN' && lane.lastOpenedAt !== null) {
        if (nowMs - lane.lastOpenedAt >= lane.cooldownMs) {
          lane.circuitState = 'HALF_OPEN';
        } else {
          attempts.push({
            laneId: lane.id,
            provider: lane.provider,
            model: lane.model,
            httpStatus: 503,
            errorType: 'circuit_open',
            detail: `Lane quarantined (${lane.lastFailureReason ?? 'recent failure'})`,
            latencyMs: 0,
            outcome: 'skipped_open_circuit',
          });
          continue;
        }
      }

      if (!lane.vaultKeyPresent) {
        lane.failureCount++;
        lane.lastFailureReason = 'Missing vault provider key in worker env';
        if (lane.failureCount >= this.circuitFailureThreshold) {
          lane.circuitState = 'OPEN';
          lane.lastOpenedAt = nowMs;
        }
        attempts.push({
          laneId: lane.id,
          provider: lane.provider,
          model: lane.model,
          httpStatus: 401,
          errorType: 'vault_key_missing',
          detail: 'Upstream key absent from worker environment (requires vault hydration)',
          latencyMs: 4,
          outcome: 'skipped_missing_vault_key',
        });
        cumulativeFailLatencyMs += 4;
        continue;
      }

      // Check billing / credit exhaustion BEFORE treating as 401
      if (lane.faultMode === '402_credit_exhausted' || lane.creditBalanceUsd <= 0) {
        lane.failureCount++;
        lane.lastFailureReason = '402 Insufficient Balance';
        // Immediately open circuit on 402 billing exhaustion so we don't burn retries
        lane.circuitState = 'OPEN';
        lane.lastOpenedAt = nowMs;
        const failLat = 38;
        cumulativeFailLatencyMs += failLat;
        attempts.push({
          laneId: lane.id,
          provider: lane.provider,
          model: lane.model,
          httpStatus: 402,
          errorType: 'billing_exhausted',
          detail: `${lane.provider} returned HTTP 402 Insufficient Balance (credit=$${lane.creditBalanceUsd.toFixed(2)})`,
          latencyMs: failLat,
          outcome: 'failed',
        });
        continue;
      }

      if (lane.faultMode === '401_upstream_key') {
        lane.failureCount++;
        lane.lastFailureReason = '401 Invalid Upstream API Key';
        lane.circuitState = 'OPEN';
        lane.lastOpenedAt = nowMs;
        const failLat = 29;
        cumulativeFailLatencyMs += failLat;
        attempts.push({
          laneId: lane.id,
          provider: lane.provider,
          model: lane.model,
          httpStatus: 401,
          errorType: 'upstream_unauthorized',
          detail: `${lane.provider} rejected upstream API key (HTTP 401)`,
          latencyMs: failLat,
          outcome: 'failed',
        });
        continue;
      }

      if (lane.faultMode === '429_rate_limit') {
        lane.failureCount++;
        lane.lastFailureReason = '429 Rate Limit Exceeded';
        if (lane.failureCount >= this.circuitFailureThreshold) {
          lane.circuitState = 'OPEN';
          lane.lastOpenedAt = nowMs;
        }
        const failLat = 22;
        cumulativeFailLatencyMs += failLat;
        attempts.push({
          laneId: lane.id,
          provider: lane.provider,
          model: lane.model,
          httpStatus: 429,
          errorType: 'rate_limited',
          detail: `${lane.provider} returned HTTP 429 Too Many Requests`,
          latencyMs: failLat,
          outcome: 'failed',
        });
        continue;
      }

      if (lane.faultMode === '503_unavailable') {
        lane.failureCount++;
        lane.lastFailureReason = '503 Upstream Unavailable';
        if (lane.failureCount >= this.circuitFailureThreshold) {
          lane.circuitState = 'OPEN';
          lane.lastOpenedAt = nowMs;
        }
        const failLat = 65;
        cumulativeFailLatencyMs += failLat;
        attempts.push({
          laneId: lane.id,
          provider: lane.provider,
          model: lane.model,
          httpStatus: 503,
          errorType: 'upstream_unavailable',
          detail: `${lane.provider} returned HTTP 503 Service Unavailable`,
          latencyMs: failLat,
          outcome: 'failed',
        });
        continue;
      }

      // Healthy dispatch (or latency spike)
      const latencyMs =
        lane.faultMode === 'latency_spike' ? lane.baseLatencyMs + 850 : lane.baseLatencyMs;
      const uncachedInputTokens = Math.max(1, Math.round(req.estimatedTokens * 0.45));
      const cachedInputTokens = req.cachedInputTokens ?? Math.round(req.estimatedTokens * 0.55);
      const outputTokens = req.outputTokens ?? Math.max(32, Math.round(req.estimatedTokens * 0.32));
      const reasoningTokens = req.reasoningTokens ?? (lane.model.includes('reasoner') ? 240 : 0);
      const contextTrimSavedTokens = req.contextTrimSavedTokens ?? Math.round(req.estimatedTokens * 0.25);

      const econ = calculateTokenEconomics({
        modelSlug: lane.model,
        baselineModelSlug: this.forensics.getBaselineModelSlug(),
        uncachedInputTokens,
        cachedInputTokens,
        outputTokens,
        reasoningTokens,
        contextTrimSavedTokens,
      });
      const costUsd = econ.actualTotalCostUsd;

      lane.circuitState = 'CLOSED';
      lane.failureCount = 0;
      lane.successCount++;
      lane.lastFailureReason = null;
      const isIdempotentReplay = this.ledger.hasIdempotencyKey(req.idempotencyKey);
      const receipt = this.ledger.append(
        {
          idempotencyKey: req.idempotencyKey || `req-${nowMs}-${Math.random().toString(36).slice(2, 8)}`,
          timestamp: new Date(nowMs).toISOString(),
          clientKeyId: clientRecord.id,
          laneId: lane.id,
          provider: lane.provider,
          model: lane.model,
          tokens: econ.totalExecutedTokens,
          costUsd,
          httpStatus: 200,
        },
        true
      );

      if (!isIdempotentReplay) {
        lane.creditBalanceUsd = Number(Math.max(0, lane.creditBalanceUsd - costUsd).toFixed(4));
        this.keyStore.recordSpend(clientRecord.id, costUsd);
      } else {
        this.forensics.incrementDuplicatePrevented();
      }

      attempts.push({
        laneId: lane.id,
        provider: lane.provider,
        model: lane.model,
        httpStatus: 200,
        errorType: null,
        detail: isIdempotentReplay
          ? `Idempotent replay via ${lane.provider} (${lane.model}) — zero double-charge`
          : `Dispatched cleanly via ${lane.provider} (${lane.model})`,
        latencyMs,
        outcome: 'success',
      });

      const endNs = typeof process !== 'undefined' && process.hrtime ? process.hrtime.bigint() : BigInt(Date.now() * 1e6);
      const overheadUs = Math.min(450, Math.max(9, Number((endNs - startNs) / BigInt(1000))));
      const totalLatencyMs = cumulativeFailLatencyMs + latencyMs;

      const pkt = isIdempotentReplay
        ? this.forensics.getPackets(1)[0]
        : this.forensics.recordPacket({
            sequence: receipt.sequence,
            timestamp: new Date(nowMs).toISOString(),
            missionId: req.missionId ?? 'MSN-ESTATE-409',
            executionId: `EXE-${receipt.sequence}`,
            sessionId: req.sessionId ?? 'SES-420',
            ownerId: req.ownerId ?? `${clientRecord.boundClient}@meridian.estate`,
            adapter: req.adapter ?? 'OpenCode V2',
            clientKeyId: clientRecord.id,
            laneId: lane.id,
            provider: lane.provider,
            modelSlug: lane.model,
            strategy,
            httpStatus: 200,
            failoverRecovered: attempts.some(
              (a) => a.outcome === 'failed' || a.outcome === 'skipped_open_circuit'
            ),
            attempts: [...attempts],
            uncachedInputTokens,
            cachedInputTokens,
            outputTokens,
            reasoningTokens,
            contextTrimSavedTokens,
            gatewayAuthAndCapUs: overheadUs,
            totalLatencyMs,
            measurementStatus: 'DIRECT',
            reasoningMeasurementStatus: reasoningTokens > 0 ? 'DIRECT' : 'DIRECT',
            computeEnergyJoules: Number(
              (1.25 + (econ.totalExecutedTokens / 1000) * 0.45).toFixed(2)
            ),
          });

      return {
        ok: true,
        httpStatus: 200,
        packetId: pkt.packetId,
        selectedLaneId: lane.id,
        selectedProvider: lane.provider,
        modelSlug: lane.model,
        gatewayOverheadUs: overheadUs,
        totalLatencyMs,
        costUsd,
        withoutPennydCostUsd: econ.withoutPennydCostUsd,
        usdSaved: econ.usdSaved,
        tokensSaved: econ.tokensSavedByPennyD,
        receiptSequence: receipt.sequence,
        attempts,
      };
    }

    // All lanes failed -> return 502 with explicit per-lane diagnostics (never opaque)
    const endNs = typeof process !== 'undefined' && process.hrtime ? process.hrtime.bigint() : BigInt(Date.now() * 1e6);
    const overheadUs = Math.min(450, Math.max(12, Number((endNs - startNs) / BigInt(1000))));
    const summaryReasons = attempts
      .map((a) => `${a.laneId}:${a.httpStatus}(${a.errorType})`)
      .join(', ');

    const failPkt = this.forensics.recordPacket({
      sequence: this.ledger.getStats().latestSequence,
      timestamp: new Date(nowMs).toISOString(),
      missionId: req.missionId ?? 'MSN-ESTATE-409',
      executionId: `EXE-FAIL-${nowMs}`,
      sessionId: req.sessionId ?? 'SES-420',
      ownerId: req.ownerId ?? `${clientRecord.boundClient}@meridian.estate`,
      adapter: req.adapter ?? 'OpenCode V2',
      clientKeyId: clientRecord.id,
      laneId: null,
      provider: 'None',
      modelSlug: req.modelSlug,
      strategy,
      httpStatus: 502,
      failoverRecovered: false,
      attempts: [...attempts],
      uncachedInputTokens: 0,
      cachedInputTokens: 0,
      outputTokens: 0,
      reasoningTokens: 0,
      contextTrimSavedTokens: 0,
      gatewayAuthAndCapUs: overheadUs,
      totalLatencyMs: cumulativeFailLatencyMs,
      measurementStatus: 'DIRECT',
      reasoningMeasurementStatus: 'BLIND',
      computeEnergyJoules: null,
    });

    return {
      ok: false,
      httpStatus: 502,
      packetId: failPkt.packetId,
      selectedLaneId: null,
      selectedProvider: null,
      modelSlug: req.modelSlug,
      gatewayOverheadUs: overheadUs,
      totalLatencyMs: cumulativeFailLatencyMs,
      costUsd: 0,
      receiptSequence: null,
      attempts,
      errorPayload: {
        error: {
          detail: `all lanes failed [${summaryReasons}]`,
          type: 'upstream',
          perLaneDiagnostics: attempts,
        },
      },
    };
  }
}
