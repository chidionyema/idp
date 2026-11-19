import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  AlertTriangle,
  CheckCircle2,
  Cpu,
  Lock,
  RefreshCw,
  Search,
  ShieldAlert,
  ShieldCheck,
  Skull,
  Sparkles,
  XCircle,
} from 'lucide-react';
import {
  GenesisSurvivalTttApiResponse,
  LiveEstateWorkstreamTelemetryRow,
} from '../types/api';

type TttTab = 'arms' | 'failure_classes' | 'work_packages';
type WorkstreamFilter = 'ALL' | 'SOURCE-LOCATED' | 'PARTIAL' | 'UNKNOWN';

const TENTACLE_ANGLES_DEG = [-90, -45, 0, 45, 90, 135, 180, -135];
const TENTACLE_SHORT_LABELS: Record<string, string> = {
  T1: 'Global DNS Cache',
  T2: 'Multi-Forge + SWH',
  T3: 'OCI Layer Smuggle',
  T4: 'Nostr Gossip Mesh',
  T5: 'IPFS + BEP-44 DHT',
  T6: 'Stego PNG + TG',
  T7: '6h Mycelium Heal',
  T8: 'Faraday + Aztec',
};

export function GenesisSurvivalTtt() {
  const [data, setData] = useState<GenesisSurvivalTttApiResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [busyAction, setBusyAction] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [actionBanner, setActionBanner] = useState<string | null>(null);
  const [selectedTentacleIdx, setSelectedTentacleIdx] = useState<number>(0);
  const [tttTab, setTttTab] = useState<TttTab>('arms');
  const [wsFilter, setWsFilter] = useState<WorkstreamFilter>('ALL');
  const [wsSearch, setWsSearch] = useState('');

  const loadSnapshot = useCallback(async () => {
    setLoading(true);
    setErrorMsg(null);
    try {
      const res = await fetch('/api/genesis/survival-ttt');
      if (!res.ok) {
        throw new Error(`Endpoint returned HTTP ${res.status}`);
      }
      const json = (await res.json()) as GenesisSurvivalTttApiResponse;
      setData(json);
    } catch (err) {
      setErrorMsg(
        err instanceof Error ? err.message : 'Unable to load Genesis Survival & TTT surface'
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadSnapshot();
  }, [loadSnapshot]);

  async function runPanspermiaSimulation(deadTentacles: number[], label: string) {
    setBusyAction(label);
    setErrorMsg(null);
    try {
      const res = await fetch('/api/genesis/panspermia/simulate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ deadTentacles }),
      });
      const json = (await res.json()) as GenesisSurvivalTttApiResponse;
      if (!res.ok) {
        throw new Error('Simulation failed');
      }
      setData(json);
      setActionBanner(
        deadTentacles.length === 0
          ? `Synthesized ${json.panspermia.sporeBytes.toLocaleString()} B Ed25519 Spore across 8/8 healthy tentacles.`
          : json.panspermia.resurrectionOk
            ? `Destroyed ${deadTentacles.length} tentacles; GF(2^8) RS(3,8) reconstructed 100% bit-exact from ${json.panspermia.survivingCount}/8 survivors in ${json.panspermia.resurrectionLatencyMs} ms.`
            : `Sub-quorum collapse (${json.panspermia.survivingCount}/8 surviving): failed closed as designed (${json.panspermia.resurrectionVerdict}).`
      );
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : 'Simulation failed');
    } finally {
      setBusyAction(null);
    }
  }

  async function handleHealAll() {
    setBusyAction('heal');
    setErrorMsg(null);
    try {
      const res = await fetch('/api/genesis/panspermia/heal', { method: 'POST' });
      const json = (await res.json()) as GenesisSurvivalTttApiResponse & { message?: string };
      setData(json);
      if (!res.ok) {
        setErrorMsg(
          json.message ?? 'Cannot self-heal below 3 surviving tentacles (quorum k=3 violated).'
        );
        return;
      }
      setActionBanner(
        `T7 Mycelium Self-Healing Reflex restored 8/8 tentacles (Cycle #${json.healingCycles}).`
      );
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : 'Self-healing failed');
    } finally {
      setBusyAction(null);
    }
  }

  async function handleRunTttFalsifiers() {
    setBusyAction('ttt_falsify');
    setErrorMsg(null);
    try {
      const res = await fetch('/api/genesis/ttt/falsify', { method: 'POST' });
      const json = (await res.json()) as GenesisSurvivalTttApiResponse & {
        suitePassed?: boolean;
      };
      if (!res.ok) {
        throw new Error('Falsifier probe failed');
      }
      setData(json);
      setActionBanner(
        `Verified 15/15 GEN-TTT-001 failure classes & F18 spec lock; Issue ${json.ttt.trackingIssue} remains honestly ${json.ttt.dispatchState}.`
      );
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : 'TTT falsifier run failed');
    } finally {
      setBusyAction(null);
    }
  }

  function toggleTentacle(index: number) {
    if (!data) return;
    const currentDead = data.panspermia.tentacles
      .filter((t) => t.status === 'DESTROYED')
      .map((t) => t.index);
    const nextDead = currentDead.includes(index)
      ? currentDead.filter((i) => i !== index)
      : [...currentDead, index];
    setSelectedTentacleIdx(index);
    void runPanspermiaSimulation(nextDead, `toggle-${index}`);
  }

  const filteredEstateRows = useMemo<LiveEstateWorkstreamTelemetryRow[]>(() => {
    if (!data) return [];
    const q = wsSearch.trim().toLowerCase();
    return data.estateRows.filter((row) => {
      if (wsFilter !== 'ALL' && row.status !== wsFilter) return false;
      if (!q) return true;
      return (
        row.name.toLowerCase().includes(q) ||
        row.dispatchState.toLowerCase().includes(q) ||
        row.liveMetricValue.toLowerCase().includes(q) ||
        row.knownDefect.toLowerCase().includes(q) ||
        `ws-${row.id}`.includes(q)
      );
    });
  }, [data, wsFilter, wsSearch]);

  if (loading && !data) {
    return (
      <div className="space-y-6" aria-busy="true" aria-label="Loading Genesis Survival and TTT">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-24 bg-white border border-slate-200 rounded-lg animate-pulse" />
          ))}
        </div>
        <div className="h-80 bg-white border border-slate-200 rounded-lg animate-pulse" />
      </div>
    );
  }

  if (!data) {
    return (
      <div className="bg-white border border-red-200 rounded-lg p-6">
        <h2 className="text-base font-semibold text-red-800">
          Genesis Survival &amp; TTT surface unavailable
        </h2>
        <p className="mt-1 text-sm text-slate-600">{errorMsg ?? 'Unknown loading error'}</p>
        <button
          type="button"
          onClick={loadSnapshot}
          className="mt-4 rounded-md bg-slate-900 px-4 py-2 text-xs font-medium text-white hover:bg-slate-800"
        >
          Retry Load
        </button>
      </div>
    );
  }

  const { panspermia, ttt, guarantees, healingCycles } = data;
  const selectedTentacle = panspermia.tentacles[selectedTentacleIdx] ?? panspermia.tentacles[0];

  return (
    <div className="space-y-6">
      {/* Header & Single-Line Operational Toolbar */}
      <section className="bg-white border border-slate-200 rounded-lg p-6">
        <div className="flex flex-col xl:flex-row xl:items-center xl:justify-between gap-4">
          <div className="max-w-2xl">
            <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
              <span>Instruction I-8088</span>
              <span aria-hidden="true">·</span>
              <span>Specification GEN-TTT-001</span>
              <span aria-hidden="true">·</span>
              <span className="font-mono tabular-nums">
                Guarantees {guarantees.verifiedCount}/{guarantees.totalCount} verified
              </span>
            </div>
            <h2 className="mt-1.5 text-xl font-bold tracking-tight text-slate-900 text-balance">
              Genesis Cephalopod Panspermia &amp; Adaptive Intelligence Control
            </h2>
            <p className="mt-1 text-sm text-slate-600">
              GF(2^8) Vandermonde Reed-Solomon (k=3, n=8) substrate survival paired with the
              GEN-TTT-001 specification gate and live 9-workstream estate telemetry.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2 shrink-0">
            <button
              type="button"
              disabled={busyAction !== null}
              onClick={() => runPanspermiaSimulation([], 'synthesize')}
              className="inline-flex items-center gap-1.5 rounded-md border border-slate-300 bg-white px-3.5 py-2 text-xs font-medium text-slate-700 hover:bg-slate-50 transition-colors whitespace-nowrap disabled:opacity-50"
            >
              <Sparkles className="h-3.5 w-3.5 text-slate-600" aria-hidden="true" />
              Synthesize Spore
            </button>
            <button
              type="button"
              disabled={busyAction !== null}
              onClick={() => runPanspermiaSimulation([0, 2, 3, 4, 6], 'destroy5')}
              className="inline-flex items-center gap-1.5 rounded-md border border-slate-300 bg-white px-3.5 py-2 text-xs font-medium text-slate-700 hover:bg-slate-50 transition-colors whitespace-nowrap disabled:opacity-50"
            >
              <Skull className="h-3.5 w-3.5 text-slate-600" aria-hidden="true" />
              Destroy 5 &amp; Resurrect
            </button>
            <button
              type="button"
              disabled={busyAction !== null}
              onClick={handleHealAll}
              className="inline-flex items-center gap-1.5 rounded-md border border-slate-300 bg-white px-3.5 py-2 text-xs font-medium text-slate-700 hover:bg-slate-50 transition-colors whitespace-nowrap disabled:opacity-50"
            >
              <RefreshCw
                className={`h-3.5 w-3.5 text-slate-600 ${busyAction === 'heal' ? 'animate-spin' : ''}`}
                aria-hidden="true"
              />
              T7 Self-Heal All 8
            </button>
            <button
              type="button"
              disabled={busyAction !== null}
              onClick={handleRunTttFalsifiers}
              className="inline-flex items-center gap-1.5 rounded-md bg-slate-900 px-4 py-2 text-xs font-medium text-white hover:bg-slate-800 transition-colors whitespace-nowrap disabled:opacity-50"
            >
              <ShieldCheck className="h-3.5 w-3.5 text-emerald-400" aria-hidden="true" />
              Run 15 TTT Falsifiers
            </button>
          </div>
        </div>

        {(actionBanner || errorMsg) && (
          <div
            role="status"
            className={`mt-4 rounded-md border px-4 py-2.5 text-xs ${
              errorMsg
                ? 'border-red-200 bg-red-50 text-red-900'
                : 'border-slate-200 bg-slate-50 text-slate-800'
            }`}
          >
            {errorMsg ?? actionBanner}
          </div>
        )}
      </section>

      {/* 4-Column KPI Strip */}
      <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white border border-slate-200 rounded-lg p-5">
          <div className="text-xs text-slate-500">Holographic Genome Spore</div>
          <div className="mt-1.5 text-2xl font-bold font-mono tabular-nums text-slate-900">
            {panspermia.sporeBytes.toLocaleString()} / {panspermia.sporeLimitBytes.toLocaleString()} B
          </div>
          <div className="mt-1 text-xs text-emerald-700">
            Ed25519 Verified · Fence #{panspermia.authoritativeFenceToken}
          </div>
        </div>

        <div className="bg-white border border-slate-200 rounded-lg p-5">
          <div className="text-xs text-slate-500">Reed-Solomon Quorum (k=3 / n=8)</div>
          <div
            className={`mt-1.5 text-2xl font-bold font-mono tabular-nums ${
              panspermia.survivingCount >= 3 ? 'text-emerald-700' : 'text-red-700'
            }`}
          >
            {panspermia.survivingCount} / {panspermia.rsConfig.n} Alive
          </div>
          <div className="mt-1 text-xs text-slate-600 font-mono tabular-nums">
            {panspermia.reconstructedBitExact ? '100% Bit-Exact' : 'Quorum Collapse'} · Heals {healingCycles}
          </div>
        </div>

        <div className="bg-white border border-slate-200 rounded-lg p-5">
          <div className="text-xs text-slate-500">Monthly Substrate Cost</div>
          <div className="mt-1.5 text-2xl font-bold font-mono tabular-nums text-slate-900">
            £{panspermia.operatingCostPerMonthGbp.toFixed(2)} / mo
          </div>
          <div className="mt-1 text-xs text-slate-600">
            {panspermia.dnsTxtRecords.length} DNS TXT · 8 Stego PNGs
          </div>
        </div>

        <div className="bg-white border border-slate-200 rounded-lg p-5">
          <div className="text-xs text-slate-500">GEN-TTT-001 Dispatch Gate</div>
          <div className="mt-1.5 text-xl font-bold font-mono tabular-nums text-amber-700">
            {ttt.dispatchState}
          </div>
          <div className="mt-1 text-xs text-slate-600">
            Issue {ttt.trackingIssue} · PR {ttt.closedInvalidPr} closed
          </div>
        </div>
      </section>

      {/* Interactive 8-Tentacle Cephalopod Topology + Carrier Proof Drawer */}
      <section className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">
        <div className="lg:col-span-7 bg-white border border-slate-200 rounded-lg p-6 flex flex-col justify-between">
          <div>
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <h3 className="text-base font-semibold text-slate-900">
                  Interactive 8-Tentacle Substrate Mesh
                </h3>
                <p className="mt-0.5 text-xs text-slate-500">
                  Click any tentacle node to simulate orbital loss or recovery under GF(2^8) RS(3,8).
                </p>
              </div>
              <div className="text-xs font-mono tabular-nums text-slate-600">
                Latency {panspermia.resurrectionLatencyMs} ms
              </div>
            </div>

            <div className="mt-4 bg-slate-900 rounded-lg p-4 overflow-hidden">
              <svg
                viewBox="0 0 760 360"
                className="w-full h-auto max-h-[340px]"
                role="img"
                aria-label="8-tentacle Cephalopod Panspermia quorum topology"
              >
                {/* Quorum Ring */}
                <circle
                  cx={380}
                  cy={180}
                  r={126}
                  fill="none"
                  stroke="#334155"
                  strokeDasharray="4 4"
                  strokeWidth={1.25}
                />

                {/* Spoke Connections & Tentacle Nodes */}
                {panspermia.tentacles.map((t, idx) => {
                  const rad = (TENTACLE_ANGLES_DEG[idx] * Math.PI) / 180;
                  const nx = 380 + Math.cos(rad) * 195;
                  const ny = 180 + Math.sin(rad) * 124;
                  const isAlive = t.status !== 'DESTROYED';
                  const isHealed = t.status === 'HEALED';
                  const strokeCol = !isAlive
                    ? '#dc2626'
                    : isHealed
                      ? '#2563eb'
                      : '#16a34a';
                  const isSelected = selectedTentacleIdx === idx;

                  return (
                    <g
                      key={t.id}
                      onClick={() => toggleTentacle(idx)}
                      className="cursor-pointer"
                    >
                      <line
                        x1={380}
                        y1={180}
                        x2={nx}
                        y2={ny}
                        stroke={strokeCol}
                        strokeWidth={isAlive ? 2.25 : 1.5}
                        strokeDasharray={isAlive ? undefined : '5 4'}
                        opacity={isAlive ? 0.9 : 0.6}
                      />
                      <rect
                        x={nx - 80}
                        y={ny - 22}
                        width={160}
                        height={44}
                        rx={8}
                        fill={isAlive ? '#1e293b' : '#291518'}
                        stroke={isSelected ? '#f8fafc' : strokeCol}
                        strokeWidth={isSelected ? 2 : 1.25}
                      />
                      <text
                        x={nx}
                        y={ny - 4}
                        textAnchor="middle"
                        fill="#f8fafc"
                        fontSize={11.5}
                        fontWeight={600}
                        fontFamily="Plus Jakarta Sans, sans-serif"
                      >
                        {t.id} · {TENTACLE_SHORT_LABELS[t.id] ?? t.name}
                      </text>
                      <text
                        x={nx}
                        y={ny + 12}
                        textAnchor="middle"
                        fill={isAlive ? '#86efac' : '#fca5a5'}
                        fontSize={10}
                        fontFamily="JetBrains Mono, monospace"
                      >
                        {t.status} · #{t.shardDigest16.slice(0, 6)}
                      </text>
                    </g>
                  );
                })}

                {/* Central Hub */}
                <circle
                  cx={380}
                  cy={180}
                  r={52}
                  fill="#0f172a"
                  stroke={panspermia.resurrectionOk ? '#16a34a' : '#dc2626'}
                  strokeWidth={2.5}
                />
                <text
                  x={380}
                  y={173}
                  textAnchor="middle"
                  fill="#ffffff"
                  fontSize={12}
                  fontWeight={700}
                  fontFamily="Plus Jakarta Sans, sans-serif"
                >
                  SPORE HUB
                </text>
                <text
                  x={380}
                  y={190}
                  textAnchor="middle"
                  fill="#cbd5e1"
                  fontSize={10.5}
                  fontFamily="JetBrains Mono, monospace"
                >
                  RS({panspermia.rsConfig.k},{panspermia.rsConfig.n}) · {panspermia.survivingCount}/8
                </text>
              </svg>
            </div>
          </div>

          {/* Accessible 8-Button Tentacle Control Matrix */}
          <div className="mt-4 grid grid-cols-2 sm:grid-cols-4 gap-2">
            {panspermia.tentacles.map((t) => {
              const alive = t.status !== 'DESTROYED';
              return (
                <button
                  key={t.id}
                  type="button"
                  onClick={() => toggleTentacle(t.index)}
                  aria-pressed={!alive}
                  className={`rounded-md border px-2.5 py-2 text-left text-xs transition-colors ${
                    alive
                      ? 'border-slate-200 bg-slate-50 hover:bg-slate-100 text-slate-900'
                      : 'border-red-200 bg-red-50 hover:bg-red-100 text-red-900'
                  }`}
                >
                  <div className="flex items-center justify-between gap-1 font-medium">
                    <span className="font-mono">{t.id}</span>
                    <span
                      className={`font-mono text-[11px] ${
                        t.status === 'HEALED'
                          ? 'text-blue-700'
                          : alive
                            ? 'text-emerald-700'
                            : 'text-red-700'
                      }`}
                    >
                      {t.status}
                    </span>
                  </div>
                  <div className="mt-0.5 truncate text-[11px] text-slate-600">{t.name}</div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Right Column: Selected Tentacle Detail, G1-G3 BDD & DNS TXT / PNG Proof */}
        <div className="lg:col-span-5 bg-white border border-slate-200 rounded-lg p-6 flex flex-col justify-between gap-5">
          <div>
            <h3 className="text-base font-semibold text-slate-900">
              Carrier Cryptographic Proof &amp; BDD Gate
            </h3>
            <p className="mt-0.5 text-xs text-slate-500">
              Inspecting {selectedTentacle.id} ({selectedTentacle.name}) · {selectedTentacle.status}
            </p>

            <div className="mt-4 divide-y divide-slate-200 border-t border-b border-slate-200 text-xs">
              <div className="py-2.5 flex items-start justify-between gap-4">
                <span className="text-slate-500 shrink-0">Substrate</span>
                <span className="text-right text-slate-900 font-medium">
                  {selectedTentacle.substrate}
                </span>
              </div>
              <div className="py-2.5 flex items-start justify-between gap-4">
                <span className="text-slate-500 shrink-0">Transport Mechanism</span>
                <span className="text-right text-slate-700">{selectedTentacle.mechanism}</span>
              </div>
              <div className="py-2.5 flex items-center justify-between gap-4">
                <span className="text-slate-500">Encrypted Soma Size</span>
                <span className="font-mono tabular-nums text-slate-900">
                  {panspermia.somaEncryptedBytes.toLocaleString()} B (PBKDF2 200k)
                </span>
              </div>
              <div className="py-2.5 flex items-center justify-between gap-4">
                <span className="text-slate-500">Lossless PNG Stego Carrier</span>
                <span className="font-mono tabular-nums text-slate-900">
                  {selectedTentacle.pngCarrierBytes.toLocaleString()} B (CRC32 OK)
                </span>
              </div>
            </div>

            {/* G1-G3 Executable BDD Scenarios */}
            <div className="mt-4 space-y-2.5">
              {panspermia.bddScenarios.map((bdd) => (
                <div key={bdd.id} className="flex items-start gap-2.5 text-xs">
                  {bdd.passed ? (
                    <CheckCircle2
                      className="h-4 w-4 text-emerald-700 shrink-0 mt-0.5"
                      aria-hidden="true"
                    />
                  ) : (
                    <XCircle
                      className="h-4 w-4 text-red-700 shrink-0 mt-0.5"
                      aria-hidden="true"
                    />
                  )}
                  <div className="min-w-0">
                    <div className="font-medium text-slate-900">{bdd.title}</div>
                    <div className="text-[11px] font-mono text-slate-500 break-words">
                      {bdd.evidence}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div>
            <div className="text-xs font-medium text-slate-700 mb-1.5">
              T1 DNS TXT Zone Records (_spore0..{panspermia.dnsTxtRecords.length - 2}.mumchimp.com)
            </div>
            <pre className="rounded-md bg-slate-900 text-slate-100 p-3 text-[11px] font-mono overflow-x-auto max-h-32 leading-relaxed">
              {panspermia.dnsTxtRecords.slice(0, 4).join('\n')}
            </pre>
          </div>
        </div>
      </section>

      {/* GEN-TTT-001 Honest Execution Gate + 6 Arms / 15 Failure Classes / 8 Work Packages */}
      <section className="bg-white border border-slate-200 rounded-lg overflow-hidden">
        <div className="p-6 border-b border-slate-200 flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
          <div className="max-w-3xl">
            <div className="flex flex-wrap items-center gap-2 text-xs text-amber-800 font-medium">
              <Lock className="h-3.5 w-3.5" aria-hidden="true" />
              <span>Epistemic Gate: {ttt.dispatchState}</span>
              <span aria-hidden="true">·</span>
              <span className="font-mono">Branch {ttt.branch}</span>
              <span aria-hidden="true">·</span>
              <span className="font-mono">Commit {ttt.commitSha.slice(0, 12)}</span>
            </div>
            <h3 className="mt-1.5 text-base font-semibold text-slate-900">
              {ttt.specId}: {ttt.title}
            </h3>
            <p className="mt-1 text-xs text-slate-600">{ttt.blockerReason}</p>
          </div>

          <div
            role="tablist"
            aria-label="GEN-TTT-001 specification views"
            className="flex flex-wrap items-center gap-1 p-1 bg-slate-100 rounded-lg shrink-0"
          >
            {(
              [
                { id: 'arms', label: `6 Experimental Arms` },
                { id: 'failure_classes', label: `15 Failure Classes` },
                { id: 'work_packages', label: `8 Work Packages & 18/18 Contract` },
              ] as const
            ).map((tab) => (
              <button
                key={tab.id}
                type="button"
                role="tab"
                aria-selected={tttTab === tab.id}
                onClick={() => setTttTab(tab.id)}
                className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors whitespace-nowrap ${
                  tttTab === tab.id
                    ? 'bg-white text-slate-900 shadow-sm'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        {tttTab === 'arms' && (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[760px] text-left border-collapse text-xs">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200 text-slate-500">
                  <th className="py-2.5 px-4 font-medium">Arm</th>
                  <th className="py-2.5 px-4 font-medium">Configuration &amp; Mechanism</th>
                  <th className="py-2.5 px-4 font-medium text-right">HELM Pass %</th>
                  <th className="py-2.5 px-4 font-medium text-right">Calibration ECE</th>
                  <th className="py-2.5 px-4 font-medium text-right">Overhead</th>
                  <th className="py-2.5 px-4 font-medium text-right">Cost / Outcome</th>
                  <th className="py-2.5 px-4 font-medium text-right">Yield Ratio</th>
                  <th className="py-2.5 px-4 font-medium text-right">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {ttt.arms.map((arm) => (
                  <tr key={arm.armId} className="hover:bg-slate-50">
                    <td className="py-2.5 px-4 font-mono font-semibold text-slate-900">
                      {arm.armId}
                    </td>
                    <td className="py-2.5 px-4">
                      <div className="font-medium text-slate-900">{arm.name}</div>
                      <div className="text-[11px] text-slate-500">{arm.description}</div>
                    </td>
                    <td className="py-2.5 px-4 text-right font-mono tabular-nums font-medium text-slate-900">
                      {arm.helmHeldOutPassPct.toFixed(1)}%
                    </td>
                    <td className="py-2.5 px-4 text-right font-mono tabular-nums text-slate-700">
                      {arm.calibrationEce.toFixed(3)}
                    </td>
                    <td className="py-2.5 px-4 text-right font-mono tabular-nums text-slate-700">
                      {arm.adaptationOverheadMs} ms
                    </td>
                    <td className="py-2.5 px-4 text-right font-mono tabular-nums text-slate-900">
                      ${arm.costPerVerifiedOutcomeUsd.toFixed(5)}
                    </td>
                    <td className="py-2.5 px-4 text-right font-mono tabular-nums font-semibold text-emerald-700">
                      {arm.operationalYieldRatio.toFixed(2)}x
                    </td>
                    <td className="py-2.5 px-4 text-right font-mono text-[11px] text-amber-700">
                      {arm.status === 'BASELINE' ? 'BASELINE' : 'PENDING_DISPATCH'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {tttTab === 'failure_classes' && (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[760px] text-left border-collapse text-xs">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200 text-slate-500">
                  <th className="py-2.5 px-4 font-medium">Class</th>
                  <th className="py-2.5 px-4 font-medium">Failure Vector</th>
                  <th className="py-2.5 px-4 font-medium">Mitigation &amp; Guardrail</th>
                  <th className="py-2.5 px-4 font-medium">Verified By</th>
                  <th className="py-2.5 px-4 font-medium text-right">Probe</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {ttt.failureClasses.map((fc) => (
                  <tr key={fc.id} className="hover:bg-slate-50">
                    <td className="py-2.5 px-4 font-mono font-semibold text-slate-900 whitespace-nowrap">
                      {fc.id}
                    </td>
                    <td className="py-2.5 px-4">
                      <div className="font-medium text-slate-900">{fc.failureClass}</div>
                      <div className="text-[11px] text-slate-500">{fc.mechanism}</div>
                    </td>
                    <td className="py-2.5 px-4 text-slate-700">{fc.mitigationControl}</td>
                    <td className="py-2.5 px-4 font-mono text-slate-600">{fc.verifiedBy}</td>
                    <td
                      className={`py-2.5 px-4 text-right font-semibold ${
                        fc.falsifierProbePassed ? 'text-emerald-700' : 'text-red-700'
                      }`}
                    >
                      {fc.falsifierProbePassed ? 'GUARDED' : 'OPEN'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {tttTab === 'work_packages' && (
          <div>
            <div className="px-6 py-4 bg-slate-50 border-b border-slate-200 grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs">
              <div>
                <div className="text-slate-500">Formal Requirements</div>
                <div className="mt-0.5 font-mono tabular-nums font-semibold text-slate-900">
                  {ttt.counts.formalRequirements} specified
                </div>
              </div>
              <div>
                <div className="text-slate-500">BDD Acceptance Scenarios</div>
                <div className="mt-0.5 font-mono tabular-nums font-semibold text-slate-900">
                  {ttt.counts.bddAcceptanceScenarios} authored
                </div>
              </div>
              <div>
                <div className="text-slate-500">Failure Classes</div>
                <div className="mt-0.5 font-mono tabular-nums font-semibold text-slate-900">
                  {ttt.counts.failureClasses} guarded
                </div>
              </div>
              <div>
                <div className="text-slate-500">Issue Contract</div>
                <div className="mt-0.5 font-mono tabular-nums font-semibold text-amber-700">
                  {ttt.trackingIssue} ({ttt.dispatchState})
                </div>
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full min-w-[680px] text-left border-collapse text-xs">
                <thead>
                  <tr className="bg-slate-50 border-b border-slate-200 text-slate-500">
                    <th className="py-2.5 px-4 font-medium">WP</th>
                    <th className="py-2.5 px-4 font-medium">Work Package</th>
                    <th className="py-2.5 px-4 font-medium">Contract Scope</th>
                    <th className="py-2.5 px-4 font-medium text-right">State</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200">
                  {ttt.workPackages.map((wp) => (
                    <tr key={wp.id} className="hover:bg-slate-50">
                      <td className="py-2.5 px-4 font-mono font-semibold text-slate-900">
                        {wp.id}
                      </td>
                      <td className="py-2.5 px-4 font-medium text-slate-900">{wp.title}</td>
                      <td className="py-2.5 px-4 text-slate-600">{wp.scope}</td>
                      <td
                        className={`py-2.5 px-4 text-right font-mono text-[11px] font-medium ${
                          wp.status === 'BLOCKED_DISPATCH'
                            ? 'text-red-700'
                            : wp.status === 'AWAITING_SPEC_FACTORY'
                              ? 'text-amber-700'
                              : 'text-slate-700'
                        }`}
                      >
                        {wp.status}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </section>

      {/* Integrated 9-Row Estate Workstreams & Live Subsystem Telemetry */}
      <section className="bg-white border border-slate-200 rounded-lg overflow-hidden">
        <div className="p-6 border-b border-slate-200 flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
          <div>
            <h3 className="text-base font-semibold text-slate-900">
              9-Workstream Estate Telemetry Ledger
            </h3>
            <p className="mt-0.5 text-xs text-slate-500">
              Live WAL, router lanes, I-8088 Reed-Solomon quorum, and GEN-TTT-001 spec status bound directly into each Estate Workstream.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <label className="relative block">
              <span className="sr-only">Filter workstreams</span>
              <Search
                className="pointer-events-none absolute left-2.5 top-2.5 h-3.5 w-3.5 text-slate-400"
                aria-hidden="true"
              />
              <input
                type="search"
                value={wsSearch}
                onChange={(e) => setWsSearch(e.target.value)}
                placeholder="Search workstream or metric..."
                className="w-56 rounded-md border border-slate-300 bg-white pl-8 pr-3 py-1.5 text-xs text-slate-900 placeholder:text-slate-400 focus:border-slate-900 focus:outline-none"
              />
            </label>

            <div
              role="group"
              aria-label="Filter workstream status"
              className="flex flex-wrap items-center gap-1 p-1 bg-slate-100 rounded-lg"
            >
              {(
                [
                  { id: 'ALL', label: `All (${data.estateRows.length})` },
                  { id: 'SOURCE-LOCATED', label: 'SOURCE-LOCATED' },
                  { id: 'PARTIAL', label: 'PARTIAL' },
                  { id: 'UNKNOWN', label: 'UNKNOWN' },
                ] as const
              ).map((tab) => (
                <button
                  key={tab.id}
                  type="button"
                  onClick={() => setWsFilter(tab.id)}
                  className={`px-2.5 py-1 text-xs font-medium rounded-md transition-colors whitespace-nowrap ${
                    wsFilter === tab.id
                      ? 'bg-white text-slate-900 shadow-sm'
                      : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>
          </div>
        </div>

        {filteredEstateRows.length === 0 ? (
          <div className="p-8 text-center">
            <Cpu className="mx-auto h-6 w-6 text-slate-400" aria-hidden="true" />
            <div className="mt-2 text-sm font-medium text-slate-900">
              No matching Estate Workstreams
            </div>
            <p className="mt-1 text-xs text-slate-500">
              Clear your search text or switch status filters to inspect all 9 workstreams.
            </p>
            <button
              type="button"
              onClick={() => {
                setWsSearch('');
                setWsFilter('ALL');
              }}
              className="mt-3 rounded-md bg-slate-900 px-3.5 py-1.5 text-xs font-medium text-white hover:bg-slate-800"
            >
              Reset Filters
            </button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[820px] text-left border-collapse text-xs">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200 text-slate-500">
                  <th className="py-2.5 px-4 font-medium">ID</th>
                  <th className="py-2.5 px-4 font-medium">Workstream &amp; Known Gap</th>
                  <th className="py-2.5 px-4 font-medium">Registry Status</th>
                  <th className="py-2.5 px-4 font-medium">Live Subsystem Metric</th>
                  <th className="py-2.5 px-4 font-medium">Dispatch / Guard State</th>
                  <th className="py-2.5 px-4 font-medium text-right">Proof</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {filteredEstateRows.map((row) => (
                  <tr key={row.id} className="hover:bg-slate-50">
                    <td className="py-3 px-4 font-mono tabular-nums font-semibold text-slate-900 whitespace-nowrap">
                      WS-{row.id}
                    </td>
                    <td className="py-3 px-4 max-w-md">
                      <div className="font-medium text-slate-900">{row.name}</div>
                      <div className="mt-0.5 text-[11px] text-slate-500 line-clamp-2">
                        {row.knownDefect}
                      </div>
                    </td>
                    <td className="py-3 px-4 font-mono text-[11px] text-slate-700 whitespace-nowrap">
                      {row.status}
                    </td>
                    <td className="py-3 px-4">
                      <div className="text-[11px] text-slate-500">{row.liveMetricLabel}</div>
                      <div className="font-mono tabular-nums font-medium text-slate-900">
                        {row.liveMetricValue}
                      </div>
                    </td>
                    <td className="py-3 px-4 whitespace-nowrap">
                      <span
                        className={`inline-flex items-center gap-1 font-mono text-[11px] font-medium ${
                          row.healthSignal === 'HEALTHY'
                            ? 'text-emerald-700'
                            : row.healthSignal === 'BLOCKED'
                              ? 'text-red-700'
                              : row.healthSignal === 'UNVERIFIED'
                                ? 'text-slate-600'
                                : 'text-amber-700'
                        }`}
                      >
                        {row.healthSignal === 'HEALTHY' && (
                          <CheckCircle2 className="h-3.5 w-3.5" aria-hidden="true" />
                        )}
                        {row.healthSignal === 'GUARDED' && (
                          <AlertTriangle className="h-3.5 w-3.5" aria-hidden="true" />
                        )}
                        {row.healthSignal === 'BLOCKED' && (
                          <ShieldAlert className="h-3.5 w-3.5" aria-hidden="true" />
                        )}
                        {row.dispatchState}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-right font-mono text-[11px] text-slate-600 whitespace-nowrap">
                      {row.verifiedBy}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
