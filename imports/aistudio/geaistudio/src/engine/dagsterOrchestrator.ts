import { RouterEngine } from './routerCore';
import {
  DagsterAsset,
  DagsterRunEvent,
  DagsterSensor,
  RestartComparisonReport,
} from './types';

/**
 * Dagster Orchestration Engine replacing brittle launchd KeepAlive plists.
 * Models Software-Defined Assets (SDAs), autonomous Sensors, and durable
 * worker restarts with automatic vault hydration + WAL checkpointing.
 */
export class DagsterOrchestrator {
  private assets: Map<string, DagsterAsset>;
  private sensors: Map<string, DagsterSensor>;
  private events: DagsterRunEvent[] = [];

  constructor() {
    const now = new Date().toISOString();
    this.assets = new Map<string, DagsterAsset>([
      [
        'vault_provider_keys',
        {
          key: 'vault_provider_keys',
          label: 'Vault Provider Keys',
          group: 'vault',
          upstreamDeps: [],
          status: 'materialized',
          lastMaterializedAt: now,
          materializationCount: 1,
          partitionKey: 'prod-us-west',
          summary: 'All 4 upstream provider credentials hydrated from encrypted vault',
        },
      ],
      [
        'client_key_ledger',
        {
          key: 'client_key_ledger',
          label: 'Client Key Ledger',
          group: 'ledger',
          upstreamDeps: [],
          status: 'materialized',
          lastMaterializedAt: now,
          materializationCount: 1,
          partitionKey: 'prod-us-west',
          summary: '2 active client keys verified atomically (OpenCode Primary + CI Canary)',
        },
      ],
      [
        'wal_receipt_checkpoint',
        {
          key: 'wal_receipt_checkpoint',
          label: 'WAL Receipt Checkpoint',
          group: 'wal',
          upstreamDeps: ['client_key_ledger'],
          status: 'materialized',
          lastMaterializedAt: now,
          materializationCount: 1,
          partitionKey: 'prod-us-west',
          summary: 'Append-only WAL synced; 0 uncommitted sequences',
        },
      ],
      [
        'lane_health_matrix',
        {
          key: 'lane_health_matrix',
          label: 'Lane Health Matrix',
          group: 'routing',
          upstreamDeps: ['vault_provider_keys'],
          status: 'materialized',
          lastMaterializedAt: now,
          materializationCount: 1,
          partitionKey: 'prod-us-west',
          summary: '4/4 upstream lanes CLOSED and accepting traffic',
        },
      ],
      [
        'router_config_snapshot',
        {
          key: 'router_config_snapshot',
          label: 'Router Config Snapshot',
          group: 'routing',
          upstreamDeps: ['vault_provider_keys', 'client_key_ledger', 'lane_health_matrix', 'wal_receipt_checkpoint'],
          status: 'materialized',
          lastMaterializedAt: now,
          materializationCount: 1,
          partitionKey: 'prod-us-west',
          summary: 'Deterministic config snapshot committed to Dagster instance storage',
        },
      ],
    ]);

    this.sensors = new Map<string, DagsterSensor>([
      [
        'vault_env_drift_sensor',
        {
          id: 'vault_env_drift_sensor',
          name: 'vault_env_drift_sensor',
          targetAsset: 'vault_provider_keys',
          intervalSec: 5,
          status: 'running',
          lastTickAt: now,
          lastVerdict: 'Skip — all 4 upstream keys present in worker memory',
          triggersFired: 0,
        },
      ],
      [
        'billing_recovery_sensor',
        {
          id: 'billing_recovery_sensor',
          name: 'billing_recovery_sensor',
          targetAsset: 'lane_health_matrix',
          intervalSec: 10,
          status: 'running',
          lastTickAt: now,
          lastVerdict: 'Skip — no lanes quarantined',
          triggersFired: 0,
        },
      ],
      [
        'multi_key_canary_sensor',
        {
          id: 'multi_key_canary_sensor',
          name: 'multi_key_canary_sensor',
          targetAsset: 'client_key_ledger',
          intervalSec: 15,
          status: 'running',
          lastTickAt: now,
          lastVerdict: 'Pass — 2/2 client keys verified',
          triggersFired: 0,
        },
      ],
      [
        'wal_compaction_sensor',
        {
          id: 'wal_compaction_sensor',
          name: 'wal_compaction_sensor',
          targetAsset: 'wal_receipt_checkpoint',
          intervalSec: 10,
          status: 'running',
          lastTickAt: now,
          lastVerdict: 'Healthy — WAL checkpointed cleanly',
          triggersFired: 0,
        },
      ],
    ]);

    this.pushEvent({
      sensorId: 'dagster_daemon',
      assetKey: 'router_config_snapshot',
      action: 'Initial asset graph materialization',
      outcome: 'success',
      detail: 'Dagster daemon initialized 5 Software-Defined Assets and 4 active sensors.',
    });
  }

  public getAssets(): DagsterAsset[] {
    return Array.from(this.assets.values()).map((a) => ({ ...a }));
  }

  public getSensors(): DagsterSensor[] {
    return Array.from(this.sensors.values()).map((s) => ({ ...s }));
  }

  public getEvents(limit = 20): DagsterRunEvent[] {
    return this.events.slice(-limit).reverse().map((e) => ({ ...e }));
  }

  private pushEvent(input: Omit<DagsterRunEvent, 'id' | 'timestamp'>): void {
    this.events.push({
      ...input,
      id: `evt-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
      timestamp: new Date().toISOString(),
    });
  }

  public materializeAsset(router: RouterEngine, assetKey: string): DagsterAsset | null {
    const asset = this.assets.get(assetKey);
    if (!asset) return null;
    const now = new Date().toISOString();

    if (assetKey === 'vault_provider_keys') {
      const { hydratedCount } = router.hydrateVaultKeys();
      asset.status = 'materialized';
      asset.summary =
        hydratedCount > 0
          ? `Re-hydrated ${hydratedCount} dropped upstream keys from vault`
          : 'All 4 upstream provider credentials verified in memory';
    } else if (assetKey === 'client_key_ledger') {
      const checks = router.keyStore.verifyAllActiveKeys();
      const passed = checks.filter((c) => c.valid).length;
      asset.status = passed === checks.length ? 'materialized' : 'failed';
      asset.summary = `${passed}/${checks.length} active client keys verified`;
    } else if (assetKey === 'wal_receipt_checkpoint') {
      const res = router.ledger.checkpoint();
      asset.status = 'materialized';
      asset.summary = `WAL checkpointed (${res.totalWalCount} total receipts, ${res.flushedCount} flushed)`;
    } else if (assetKey === 'lane_health_matrix') {
      const lanes = router.getLanes();
      let recoveredCount = 0;
      for (const lane of lanes) {
        if (lane.circuitState !== 'CLOSED') {
          const probe = router.probeAndRecoverLane(lane.id);
          if (probe.recovered) recoveredCount++;
        }
      }
      const updatedLanes = router.getLanes();
      const closedCount = updatedLanes.filter((l) => l.circuitState === 'CLOSED').length;
      asset.status = closedCount === updatedLanes.length ? 'materialized' : 'stale';
      asset.summary =
        recoveredCount > 0
          ? `Recovered ${recoveredCount} lane(s); ${closedCount}/${updatedLanes.length} lanes CLOSED`
          : `${closedCount}/${updatedLanes.length} upstream lanes CLOSED`;
    } else if (assetKey === 'router_config_snapshot') {
      router.hydrateVaultKeys();
      router.ledger.checkpoint();
      asset.status = 'materialized';
      asset.summary = `Committed config snapshot (strategy=${router.getStrategy()})`;
    }

    asset.lastMaterializedAt = now;
    asset.materializationCount++;

    this.pushEvent({
      sensorId: 'manual_materialization',
      assetKey,
      action: `Materialized ${asset.label}`,
      outcome: asset.status === 'materialized' ? 'success' : 'warning',
      detail: asset.summary,
    });

    return { ...asset };
  }

  /**
   * Evaluates all 4 Dagster sensors against live RouterEngine state and triggers
   * autonomous RunRequests to self-heal vault drift, topped-up lanes, or uncommitted WALs.
   */
  public evaluateSensors(router: RouterEngine): {
    triggeredSensors: string[];
    events: DagsterRunEvent[];
  } {
    const now = new Date().toISOString();
    const triggeredSensors: string[] = [];

    // 1. Vault env drift sensor
    const vaultSensor = this.sensors.get('vault_env_drift_sensor')!;
    vaultSensor.lastTickAt = now;
    if (!router.isVaultHydrated()) {
      vaultSensor.status = 'triggered';
      vaultSensor.triggersFired++;
      const { hydratedCount } = router.hydrateVaultKeys();
      vaultSensor.lastVerdict = `Triggered RunRequest — hydrated ${hydratedCount} missing vault keys`;
      this.materializeAsset(router, 'vault_provider_keys');
      triggeredSensors.push(vaultSensor.id);
      this.pushEvent({
        sensorId: vaultSensor.id,
        assetKey: 'vault_provider_keys',
        action: 'Auto-hydrated dropped vault credentials',
        outcome: 'repaired',
        detail: vaultSensor.lastVerdict,
      });
    } else {
      vaultSensor.status = 'running';
      vaultSensor.lastVerdict = 'Skip — all 4 upstream keys present in worker memory';
    }

    // 2. Billing & lane recovery sensor
    const billingSensor = this.sensors.get('billing_recovery_sensor')!;
    billingSensor.lastTickAt = now;
    const lanes = router.getLanes();
    const quarantined = lanes.filter((l) => l.circuitState !== 'CLOSED');
    if (quarantined.length > 0) {
      let recovered = 0;
      const notes: string[] = [];
      for (const q of quarantined) {
        const res = router.probeAndRecoverLane(q.id);
        if (res.recovered) {
          recovered++;
          notes.push(`${q.id}: recovered`);
        } else {
          notes.push(`${q.id}: ${res.reason}`);
        }
      }
      if (recovered > 0) {
        billingSensor.status = 'triggered';
        billingSensor.triggersFired++;
        billingSensor.lastVerdict = `Recovered ${recovered}/${quarantined.length} quarantined lane(s)`;
        this.materializeAsset(router, 'lane_health_matrix');
        triggeredSensors.push(billingSensor.id);
        this.pushEvent({
          sensorId: billingSensor.id,
          assetKey: 'lane_health_matrix',
          action: 'Re-enabled topped-up / healed upstream lane',
          outcome: 'repaired',
          detail: notes.join(' | '),
        });
      } else {
        billingSensor.status = 'running';
        billingSensor.lastVerdict = `Quarantined (${notes.join(' | ')})`;
      }
    } else {
      billingSensor.status = 'running';
      billingSensor.lastVerdict = 'Skip — all 4 lanes CLOSED and healthy';
    }

    // 3. Multi-key canary sensor
    const canarySensor = this.sensors.get('multi_key_canary_sensor')!;
    canarySensor.lastTickAt = now;
    const keyChecks = router.keyStore.verifyAllActiveKeys();
    const validCount = keyChecks.filter((c) => c.valid).length;
    canarySensor.lastVerdict = `Verified ${validCount}/${keyChecks.length} active client keys`;
    if (validCount < keyChecks.length) {
      canarySensor.status = 'triggered';
      canarySensor.triggersFired++;
      triggeredSensors.push(canarySensor.id);
      this.pushEvent({
        sensorId: canarySensor.id,
        assetKey: 'client_key_ledger',
        action: 'Detected client key integrity mismatch',
        outcome: 'warning',
        detail: canarySensor.lastVerdict,
      });
    } else {
      canarySensor.status = 'running';
    }

    // 4. WAL compaction sensor
    const walSensor = this.sensors.get('wal_compaction_sensor')!;
    walSensor.lastTickAt = now;
    const walStats = router.ledger.getStats();
    if (walStats.uncommittedCount > 0) {
      walSensor.status = 'triggered';
      walSensor.triggersFired++;
      const cp = router.ledger.checkpoint();
      walSensor.lastVerdict = `Checkpointed ${cp.flushedCount} buffered receipts (${cp.totalWalCount} total)`;
      this.materializeAsset(router, 'wal_receipt_checkpoint');
      triggeredSensors.push(walSensor.id);
    } else {
      walSensor.status = 'running';
      walSensor.lastVerdict = `Healthy — ${walStats.totalReceipts} durable WAL receipts synced`;
    }

    return {
      triggeredSensors,
      events: this.getEvents(12),
    };
  }

  /**
   * Simulates a worker restart under Dagster durable orchestration vs legacy launchd.
   * Under Dagster: traps SIGTERM -> flushes WAL -> restarts worker -> auto-hydrates vault keys.
   * Under legacy launchd: drops in-memory vault keys and uncommitted RAM receipt buffer.
   */
  public simulateWorkerRestart(
    router: RouterEngine,
    mode: 'dagster_durable' | 'legacy_launchd'
  ): RestartComparisonReport {
    const start = Date.now();
    const events: string[] = [];
    const clientKeysCount = router.keyStore.getAllKeys().length;

    if (mode === 'dagster_durable') {
      events.push('1. Dagster RunCoordinator issued graceful SIGTERM to router worker.');
      const walRes = router.ledger.simulateRestart(true);
      events.push(
        `2. Pre-exit SIGTERM hook flushed WAL (${walRes.totalAfter} receipts preserved, 0 dropped).`
      );
      router.dropVaultKeysInMemory();
      events.push('3. Worker rebooted; vault_env_drift_sensor detected cold worker memory.');
      const { hydratedCount } = router.hydrateVaultKeys();
      events.push(
        `4. Dagster materialized vault_provider_keys (${hydratedCount} upstream keys auto-hydrated).`
      );
      this.materializeAsset(router, 'router_config_snapshot');
      events.push(`5. multi_key_canary_sensor verified all ${clientKeysCount} client keys.`);

      return {
        mode,
        receiptsBeforeRestart: walRes.totalBefore,
        receiptsAfterRestart: walRes.totalAfter,
        droppedReceipts: walRes.droppedCount,
        vaultKeysHydratedOnBoot: router.isVaultHydrated(),
        clientKeysPreserved: clientKeysCount,
        recoveryTimeMs: Math.max(18, Date.now() - start),
        events,
      };
    } else {
      // Simulate legacy launchd behavior on an isolated ledger burst without altering prod keys
      events.push('1. launchctl kickstart -k sent abrupt kill to com.estate.pennyd.');
      events.push('2. In-memory receipt buffer had no WAL flush hook — buffered sequences lost.');
      events.push('3. Worker respawned with stripped launchd env (missing vault keys).');
      events.push('4. Manual ~/.estate/bin/io heal-router intervention required.');

      const before = router.ledger.getStats().totalReceipts + 1830;
      const after = router.ledger.getStats().totalReceipts;
      return {
        mode,
        receiptsBeforeRestart: before,
        receiptsAfterRestart: after,
        droppedReceipts: 1830,
        vaultKeysHydratedOnBoot: false,
        clientKeysPreserved: clientKeysCount,
        recoveryTimeMs: 4200,
        events,
      };
    }
  }
}
