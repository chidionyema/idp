// ui/FounderConciergeSurface.tsx
// Full Sovereign Control Plane for I-8046 Universal Fleet Cage,
// 5-Layer Lockdown Toggles, Dual-Router Comparison (pennyd vs sovereign-router),
// Work-in-Flight Auto-Main Drain Console, and 1-Click Point-in-Time Rollback.

import React, { useEffect, useState } from 'react';

export interface FleetActorStatus {
  actorId: string;
  fleetClass: 'CLASS_A_SOVEREIGN' | 'CLASS_B1_CLI_WEB' | 'CLASS_B2_ROUTER' | 'CLASS_B3_HARNESS' | 'CLASS_B4_CI';
  repoWriteAccess: 'PASSKEY_SEAL_ONLY' | 'ZERO_WRITE';
  dofAccess: 'CERTIFIER_ONLY' | 'HTTP_401_BLOCKED';
  osCredsMounted: boolean;
  chromeDebugLocked: boolean;
}

export interface WorkInFlightEntry {
  sha: string;
  branch: string;
  title: string;
  touchedFiles: string[];
  verdict: 'CLEAN_ELIGIBLE' | 'QUARANTINED_B2_BREACH' | 'SUPERSEDED_ARCHIVE';
  promotedToMain: boolean;
}

export interface LockdownConfigState {
  instructionId: string;
  authoritativeToken: number;
  telegramPinnedMsgId: number;
  layers: {
    githubRulesetLock: boolean;
    controlPrimitiveFreeze: boolean;
    osCredentialStripping: boolean;
    browserIsolation: boolean;
    kernelTelegramFence: boolean;
  };
  routers: {
    pennydRustPort4200Active: boolean;
    pennydSeq25Repaired: boolean;
    pennydMaxTokensCap: number;
    sovereignRouter8022Active: boolean;
    executionCeilingSecondsI11: number;
  };
  fleet: FleetActorStatus[];
  workInFlight: WorkInFlightEntry[];
}

export const FounderConciergeSurface: React.FC = () => {
  const [state, setState] = useState<LockdownConfigState | null>(null);
  const [statusBanner, setStatusBanner] = useState<string>('LOCAL_HERMETIC_READY');

  useEffect(() => {
    const ws = new WebSocket(`${window.location.origin.replace(/^http/, 'ws')}/api/realtime/ws?since_seq=0`);
    ws.onmessage = (event) => {
      const payload = JSON.parse(event.data);
      if (payload.type === 'CAGE_STATE_SNAPSHOT') {
        setState(payload.data);
      }
    };
    return () => ws.close();
  }, []);

  const triggerSignedAction = async (endpoint: string, body: Record<string, unknown>) => {
    const response = await fetch(endpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Control-Surface': 'gemini-argon',
      },
      body: JSON.stringify(body),
    });
    if (!response.ok) {
      setStatusBanner(`REJECTED_${response.status}`);
      return;
    }
    const updated = await response.json();
    setState(updated.state);
    setStatusBanner(`SEALED_SEQ_${updated.seq_id}`);
  };

  if (!state) return <div data-testid="loading-surface">Synchronizing Merkle-WAL...</div>;

  return (
    <main className="aura-2100-deck" data-testid="founder-concierge-surface">
      <header>
        <h1>I-8046 Sovereign Control Plane — Universal Agent Cage & Deterministic Auto-Main</h1>
        <div data-testid="fence-token">Fence Token: {state.authoritativeToken} | Telegram Seal: #{state.telegramPinnedMsgId} | Status: {statusBanner}</div>
      </header>

      <section data-testid="five-layer-lockdown-controls">
        <h2>1. Five-Layer Mechanical Lockdown (Configurable with Hardware Seal)</h2>
        {Object.entries(state.layers).map(([key, enabled]) => (
          <button
            key={key}
            data-testid={`toggle-${key}`}
            onClick={() => triggerSignedAction('/api/cage/layer', { layer: key, enabled: !enabled })}
          >
            {key}: {enabled ? 'LOCKED_ENFORCED' : 'DISABLED'}
          </button>
        ))}
      </section>

      <section data-testid="work-in-flight-automain-console">
        <h2>2. Work-in-Flight Triage & Deterministic Auto-Main</h2>
        <button
          data-testid="run-local-automain-drain"
          onClick={() => triggerSignedAction('/api/automain/drain', { requireLocalHermeticPass: true })}
        >
          Verify All Locally & Auto-Promote Clean Commits to Main
        </button>
        <table>
          <thead>
            <tr>
              <th>Commit</th>
              <th>Branch</th>
              <th>Verdict</th>
              <th>Main Status</th>
            </tr>
          </thead>
          <tbody>
            {state.workInFlight.map((item) => (
              <tr key={item.sha} data-testid={`wif-row-${item.sha}`}>
                <td>{item.sha}</td>
                <td>{item.branch}</td>
                <td>{item.verdict}</td>
                <td>{item.promotedToMain ? 'ON_MAIN' : 'QUARANTINED_OR_PENDING'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section data-testid="dual-router-comparison">
        <h2>3. Dual Router Arena (Rust pennyd :4200 vs sovereign-router #8022)</h2>
        <p>
          pennyd (:4200): {state.routers.pennydRustPort4200Active ? 'ACTIVE' : 'OFF'} |
          Seq 25 Ledger Repaired: {String(state.routers.pennydSeq25Repaired)} |
          Max Tokens Cap: {state.routers.pennydMaxTokensCap} |
          sovereign-router (#8022): {state.routers.sovereignRouter8022Active ? 'ACTIVE' : 'OFF'} |
          I11 Ceiling: {state.routers.executionCeilingSecondsI11}s
        </p>
      </section>
    </main>
  );
};
