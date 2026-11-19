import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Check,
  Copy,
  Download,
  Lock,
  Radio,
  RefreshCw,
  Send,
  ShieldCheck,
  Terminal,
  UserPlus,
  WifiOff,
} from 'lucide-react';
import type {
  BoundaryEliminationProofResult,
  BoundaryManifestValidation,
  BrowserWorkforceOnboardingResult,
  MandatoryResilienceMatrixSnapshot,
  OperationalSettlementSnapshot,
  UniversalKarmicSettlementSnapshot,
  ZeroGaslightAdmissionDecision,
} from '../engine/meridianCapabilityCalculus';
import type {
  BusSurfaceClass,
  OmniflowBusMessage,
  OmniflowLiveBusSnapshot,
  OmniflowMessageVerb,
} from '../engine/omniflowLiveBus';

const SURFACE_OPTIONS: Array<{ value: BusSurfaceClass; label: string }> = [
  { value: 'CONSOLE_CLI', label: 'Console CLI (Argon / OpenCode / GLM)' },
  { value: 'WEB_BROWSER', label: 'Browser Session (TinyFish / Web)' },
  { value: 'API_WORKER', label: 'API Model Worker (Gemini / DeepSeek / PennyD)' },
  { value: 'CLOUD_RUNNER', label: 'Cloud Runner (GitHub Actions / Worker)' },
  { value: 'MOBILE_MESSAGING', label: 'Mobile / Messaging (WhatsApp / OTTO Telegram)' },
];

const VERB_OPTIONS: OmniflowMessageVerb[] = [
  'ASK',
  'OFFER',
  'PATCH_REF',
  'EVIDENCE_REF',
  'BLOCKED',
  'STATUS',
];

export function OmniflowLiveRoomPanel() {
  const [snap, setSnap] = useState<OmniflowLiveBusSnapshot | null>(null);
  const [sseLive, setSseLive] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);
  const [banner, setBanner] = useState<string | null>(null);

  // Composer state
  const [fromAgent, setFromAgent] = useState('founder-web-cockpit');
  const [target, setTarget] = useState('@all');
  const [verb, setVerb] = useState<OmniflowMessageVerb>('ASK');
  const [body, setBody] = useState(
    'Report live status and claim any open Greenlane / shadow-verify / estate-bus obligation.'
  );
  const [requiresClaim, setRequiresClaim] = useState(true);

  // Register worker / console participant form
  const [newAgentId, setNewAgentId] = useState('glm-5.3-console');
  const [newSurface, setNewSurface] = useState<BusSurfaceClass>('CONSOLE_CLI');
  const [newCaps, setNewCaps] = useState('code:patch,shadow-verify,idp');

  // External spine probe form
  const [probeUrl, setProbeUrl] = useState('https://estate-bus.mumchimp.com/health');
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  // EP-A 100% Guarantee Else No Admission Guard (#8188 / #8194 / bin/verify_three_proofs.py)
  const [manifestText, setManifestText] = useState(
    'catalog/capabilities.yaml, docs/runbook.md, tests/test_catalog.py'
  );
  const [requireExternalLive, setRequireExternalLive] = useState(false);
  const [guardResult, setGuardResult] = useState<
    (BoundaryManifestValidation & { zeroGaslightDecision?: ZeroGaslightAdmissionDecision }) | null
  >(null);
  const [mathProof, setMathProof] = useState<{
    proof: BoundaryEliminationProofResult;
    settlement: OperationalSettlementSnapshot;
  } | null>(null);

  // KARMA #7452 & #8030 Universal Settlement + 7-Seat Browser Workforce (BR-KIMI-01) + Auto-Sync Live
  const [universalSettlement, setUniversalSettlement] =
    useState<UniversalKarmicSettlementSnapshot | null>(null);
  const [resilienceMatrix, setResilienceMatrix] =
    useState<MandatoryResilienceMatrixSnapshot | null>(null);
  const [selectedBrowserWorker, setSelectedBrowserWorker] = useState('BR-KIMI-01');
  const [lastOnboardingResult, setLastOnboardingResult] =
    useState<BrowserWorkforceOnboardingResult | null>(null);
  const [snapshotLiveState, setSnapshotLiveState] = useState<{
    isLiveState: boolean;
    telemetryFreshness: string;
  }>({ isLiveState: true, telemetryFreshness: 'LIVE_EXPRESS_RUNTIME' });
  const [autoSyncInfo, setAutoSyncInfo] = useState<{
    daemonActive: boolean;
    intervalSeconds: number;
    lastCycleAtUtc: string | null;
    lastAcceptedBundleSha256: string | null;
    currentHeadSha: string;
    currentBundleSha256: string | null;
    currentBundleBytes: number;
    workspaceArchiveBytes?: number;
    workspaceArchiveFileCount?: number;
    lastReason?: string | null;
  } | null>(null);

  const originBase =
    typeof window !== 'undefined' ? window.location.origin : 'http://localhost:3000';

  const loadState = useCallback(async () => {
    const [busRes, proofRes, universalRes, syncRes] = await Promise.all([
      fetch('/api/omniflow/state'),
      fetch('/api/omniflow/mathematical-proof'),
      fetch('/api/omniflow/universal-settlement'),
      fetch('/api/export/auto-sync'),
    ]);
    if (busRes.ok) {
      const json = (await busRes.json()) as OmniflowLiveBusSnapshot & {
        isLiveState?: boolean;
        telemetryFreshness?: string;
        staticProjectionMode?: boolean;
      };
      setSnap(json);
      if (json.staticProjectionMode || json.isLiveState === false) {
        setSnapshotLiveState({
          isLiveState: false,
          telemetryFreshness: json.telemetryFreshness ?? 'HISTORICAL_BUILD_SNAPSHOT_NOT_LIVE',
        });
      }
    }
    if (proofRes.ok) {
      const pJson = (await proofRes.json()) as {
        proof: BoundaryEliminationProofResult;
        settlement: OperationalSettlementSnapshot;
      };
      setMathProof({ proof: pJson.proof, settlement: pJson.settlement });
    }
    if (universalRes.ok) {
      const uJson = (await universalRes.json()) as {
        isLiveState?: boolean;
        telemetryFreshness?: string;
        projectionMode?: string;
        settlement: UniversalKarmicSettlementSnapshot;
      };
      setUniversalSettlement(uJson.settlement);
      if (uJson.isLiveState === false || uJson.projectionMode === 'STATIC_CDN_PROJECTION') {
        setSnapshotLiveState({
          isLiveState: false,
          telemetryFreshness: uJson.telemetryFreshness ?? 'HISTORICAL_BUILD_SNAPSHOT_NOT_LIVE',
        });
      } else if (uJson.isLiveState === true) {
        setSnapshotLiveState({
          isLiveState: true,
          telemetryFreshness: uJson.telemetryFreshness ?? 'LIVE_EXPRESS_RUNTIME',
        });
      }
      if (uJson.settlement?.resilienceMatrix) {
        setResilienceMatrix(uJson.settlement.resilienceMatrix);
      }
    }
    if (syncRes.ok) {
      const sJson = await syncRes.json();
      setAutoSyncInfo(sJson);
    }
  }, []);

  // Strict I-8090: EventSource SSE only (zero client HTTP polling)
  useEffect(() => {
    void loadState();

    // Register current browser founder session
    void fetch('/api/omniflow/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        agentId: 'founder-web-cockpit',
        displayName: 'Founder Browser Session (Live Web/iPhone)',
        surfaceClass: 'WEB_BROWSER',
        transport: 'SSE_HTTPS',
        capabilities: ['founder:approve', 'dispatch:all', 'karma:inspect'],
        formations: ['council', 'concierge', 'greenlane'],
        ttlMs: 300_000,
      }),
    }).catch(() => {});

    const es = new EventSource('/api/omniflow/stream');
    es.onopen = () => setSseLive(true);
    es.onerror = () => setSseLive(false);
    es.addEventListener('omniflow_snapshot', (ev) => {
      try {
        const parsed = JSON.parse((ev as MessageEvent<string>).data) as OmniflowLiveBusSnapshot;
        setSnap(parsed);
        setSseLive(true);
      } catch {
        // Ignore malformed frame
      }
    });

    return () => {
      es.close();
    };
  }, [loadState]);

  const cliJoinCommand = useMemo(
    () =>
      `curl -sSL "${originBase}/api/omniflow/cli-script" -o estate-bus-cli.mjs && node estate-bus-cli.mjs listen --bus "${originBase}" --agent "${newAgentId || 'console-worker-01'}" --caps "${newCaps || 'code:patch'}"`,
    [originBase, newAgentId, newCaps]
  );

  async function copyText(key: string, text: string) {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedKey(key);
    } catch {
      setBanner('Copy failed: copy manually from the snippet box.');
    }
  }

  async function handlePublish(ev: React.FormEvent) {
    ev.preventDefault();
    if (!body.trim()) return;
    setBusy('publish');
    try {
      const res = await fetch('/api/omniflow/publish', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          fromAgent,
          target,
          verb,
          body: body.trim(),
          requiresClaim,
        }),
      });
      const json = (await res.json()) as {
        ok?: boolean;
        message?: OmniflowBusMessage;
        snapshot?: OmniflowLiveBusSnapshot;
        error?: string;
      };
      if (json.snapshot) setSnap(json.snapshot);
      if (json.ok && json.message) {
        setBanner(
          `Broadcast ${json.message.envelopeId} -> ${json.message.target} (${json.message.custodyStage}).`
        );
        setBody('');
      } else if (json.error) {
        setBanner(`Rejected: ${json.error}`);
      }
    } finally {
      setBusy(null);
    }
  }

  async function handleRegister(ev: React.FormEvent) {
    ev.preventDefault();
    if (!newAgentId.trim()) return;
    setBusy('register');
    try {
      const res = await fetch('/api/omniflow/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          agentId: newAgentId.trim(),
          displayName: newAgentId.trim(),
          surfaceClass: newSurface,
          transport: newSurface === 'CONSOLE_CLI' ? 'CLI_BRIDGE' : 'SSE_HTTPS',
          capabilities: newCaps
            .split(',')
            .map((s) => s.trim())
            .filter(Boolean),
          ttlMs: 120_000,
        }),
      });
      const json = (await res.json()) as {
        ok?: boolean;
        snapshot?: OmniflowLiveBusSnapshot;
        error?: string;
      };
      if (json.snapshot) setSnap(json.snapshot);
      setBanner(
        json.ok
          ? `Registered ${newAgentId.trim()} (${newSurface}) in live OMNIFLOW presence.`
          : `Error: ${json.error ?? 'register failed'}`
      );
    } finally {
      setBusy(null);
    }
  }

  async function handleDisconnect(agentId: string) {
    setBusy(`drop:${agentId}`);
    try {
      const res = await fetch('/api/omniflow/disconnect', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ agentId }),
      });
      const json = (await res.json()) as {
        releasedEnvelopes?: string[];
        snapshot?: OmniflowLiveBusSnapshot;
      };
      if (json.snapshot) setSnap(json.snapshot);
      const released = json.releasedEnvelopes ?? [];
      setBanner(
        released.length > 0
          ? `Disconnected ${agentId}: automatically recovered ${released.length} active lease(s) (${released.join(', ')}) so zero work was lost.`
          : `Disconnected ${agentId} from active presence.`
      );
    } finally {
      setBusy(null);
    }
  }

  async function handleClaim(envelopeId: string, workerId: string) {
    setBusy(`claim:${envelopeId}`);
    try {
      const res = await fetch('/api/omniflow/lease', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'CLAIM', envelopeId, workerId }),
      });
      const json = (await res.json()) as {
        ok?: boolean;
        error?: string;
        message?: OmniflowBusMessage;
        snapshot?: OmniflowLiveBusSnapshot;
      };
      if (json.snapshot) setSnap(json.snapshot);
      setBanner(
        json.ok && json.message
          ? `Granted lease f_${json.message.fencingToken} on ${envelopeId} to ${workerId}.`
          : `Blocked (HTTP ${res.status}): ${json.error ?? 'claim denied'}`
      );
    } finally {
      setBusy(null);
    }
  }

  async function handleVerify(envelopeId: string, verifierId: string) {
    setBusy(`verify:${envelopeId}`);
    try {
      const res = await fetch('/api/omniflow/lease', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          action: 'VERIFY_EFFECT',
          envelopeId,
          verifierId,
          evidenceNote: 'Independently verified receipt in live OMNIFLOW room',
        }),
      });
      const json = (await res.json()) as {
        ok?: boolean;
        error?: string;
        message?: OmniflowBusMessage;
        snapshot?: OmniflowLiveBusSnapshot;
      };
      if (json.snapshot) setSnap(json.snapshot);
      setBanner(
        json.ok && json.message
          ? `Independent KARMA verification complete on ${envelopeId} (sha256:${json.message.verificationReceiptSha256?.slice(0, 12)}).`
          : `Blocked (HTTP ${res.status}): ${json.error ?? 'verification denied'}`
      );
    } finally {
      setBusy(null);
    }
  }

  async function handleProbeExternal(ev: React.FormEvent) {
    ev.preventDefault();
    setBusy('probe');
    try {
      const res = await fetch('/api/omniflow/probe-external', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: probeUrl.trim() }),
      });
      const json = (await res.json()) as {
        ok?: boolean;
        snapshot?: OmniflowLiveBusSnapshot;
      };
      if (json.snapshot) setSnap(json.snapshot);
      const p = json.snapshot?.externalSpineProbe;
      if (p) {
        setBanner(
          p.status === 'LIVE_VERIFIED'
            ? `LIVE_VERIFIED: ${p.targetUrl} returned HTTP ${p.httpStatus} in ${p.latencyMs}ms.`
            : `${p.status}: ${p.errorDetail ?? 'External probe failed'}`
        );
      }
    } finally {
      setBusy(null);
    }
  }

  function parseManifestFiles(): string[] {
    return manifestText
      .split(/[\n,]+/)
      .map((s) => s.trim())
      .filter(Boolean);
  }

  async function handleValidateManifest() {
    const proposedFiles = parseManifestFiles();
    setBusy('validate-manifest');
    try {
      const res = await fetch('/api/omniflow/validate-manifest', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          workerId: fromAgent,
          workerQuadAttested: true,
          proposedFiles,
          requireExternalSpineLive: requireExternalLive,
        }),
      });
      const json = (await res.json()) as BoundaryManifestValidation & {
        zeroGaslightDecision?: ZeroGaslightAdmissionDecision;
      };
      setGuardResult(json);
      const zg = json.zeroGaslightDecision;
      setBanner(
        zg?.admitted
          ? `ADMITTED (0 violations): ${json.summary}`
          : `NO ADMISSION (HTTP ${zg?.httpStatus ?? 422} · 0 tokens spent): ${zg?.explanation ?? json.summary}`
      );
    } finally {
      setBusy(null);
    }
  }

  async function handleAutoDecomposeDispatch() {
    const proposedFiles = parseManifestFiles();
    if (proposedFiles.length === 0) return;
    setBusy('auto-decompose');
    try {
      const res = await fetch('/api/omniflow/publish', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          fromAgent,
          target,
          verb: 'ASK',
          body: 'Scoped single-subsystem change lane (#8188 / bin/verify_three_proofs.py)',
          requiresClaim: true,
          proposedFiles,
          autoDecompose: true,
          requireExternalSpineLive: requireExternalLive,
        }),
      });
      const json = (await res.json()) as {
        ok?: boolean;
        error?: string;
        decomposedMessages?: OmniflowBusMessage[];
        message?: OmniflowBusMessage;
        boundaryValidation?: BoundaryManifestValidation;
        zeroGaslightDecision?: ZeroGaslightAdmissionDecision;
        snapshot?: OmniflowLiveBusSnapshot;
      };
      if (json.snapshot) setSnap(json.snapshot);
      if (json.boundaryValidation) {
        setGuardResult({
          ...json.boundaryValidation,
          zeroGaslightDecision: json.zeroGaslightDecision,
        });
      }
      if (!res.ok || !json.ok) {
        setBanner(`NO ADMISSION (HTTP ${res.status}): ${json.error ?? 'Blocked by admission guard'}`);
        return;
      }
      const lanesCount = json.decomposedMessages?.length ?? (json.message ? 1 : 0);
      setBanner(
        `Auto-Decomposed & Dispatched ${lanesCount} compliant 1-subsystem lane(s) (each <=5 files).`
      );
    } finally {
      setBusy(null);
    }
  }

  async function handleRunMathProof() {
    setBusy('math-proof');
    try {
      const res = await fetch('/api/omniflow/mathematical-proof', { method: 'POST' });
      if (res.ok) {
        const json = (await res.json()) as {
          proof: BoundaryEliminationProofResult;
          settlement: OperationalSettlementSnapshot;
        };
        setMathProof({ proof: json.proof, settlement: json.settlement });
        setBanner(
          `Mathematical Proof verified: ${json.proof.exhaustiveModelStats.validNonEmptySubsetsTested} non-empty subsets checked with ${json.proof.exhaustiveModelStats.validSubsetViolationsFound} violations; ${json.proof.exhaustiveModelStats.invalidMultiSubsystemBlockedCount} multi-subsystem vectors blocked (sha256:${json.proof.proofDigestSha256.slice(0, 12)}).`
        );
      }
    } finally {
      setBusy(null);
    }
  }

  async function handleOnboardBrowserWorker(workerId: string) {
    setBusy('onboard-worker');
    try {
      const res = await fetch('/api/omniflow/onboard-worker', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ workerId }),
      });
      const json = (await res.json()) as {
        ok?: boolean;
        error?: string;
        onboarding?: BrowserWorkforceOnboardingResult;
        settlement?: UniversalKarmicSettlementSnapshot;
        snapshot?: OmniflowLiveBusSnapshot;
      };
      if (json.snapshot) setSnap(json.snapshot);
      if (json.settlement) setUniversalSettlement(json.settlement);
      if (json.onboarding) setLastOnboardingResult(json.onboarding);
      setBanner(
        json.ok && json.onboarding
          ? `Registered ${json.onboarding.worker.workerId} schema ONLY (0/${universalSettlement?.browserWorkforceCount ?? 7} authenticated remote executions verified; external auth=${json.onboarding.worker.externalBrowserAuthState}).`
          : `Onboarding rejected: ${json.error ?? 'Refinement check failed'}`
      );
    } finally {
      setBusy(null);
    }
  }

  async function handleTriggerAutoSyncNow() {
    setBusy('auto-sync');
    try {
      const res = await fetch('/api/omniflow/auto-sync-now', { method: 'POST' });
      const json = (await res.json()) as {
        ok?: boolean;
        pushed?: boolean;
        headSha?: string;
        bundleSha256?: string | null;
        lastReason?: string | null;
        autoSync?: typeof autoSyncInfo;
        settlement?: UniversalKarmicSettlementSnapshot;
        error?: string;
      };
      if (json.autoSync) {
        setAutoSyncInfo((prev) => ({ ...prev, ...json.autoSync!, lastReason: json.lastReason }));
      }
      if (json.settlement) setUniversalSettlement(json.settlement);
      setBanner(
        json.pushed
          ? `Auto-Sync PUSHED remotely: HEAD ${json.headSha?.slice(0, 7)} (sha256:${json.bundleSha256?.slice(0, 12)}).`
          : `Local bundle sealed (HEAD ${json.headSha?.slice(0, 7)}, sha256:${json.bundleSha256?.slice(0, 12)}) · External #7760 receiver & private GitHub custody still unverified (${json.lastReason ?? 'see unblock commands'}).`
      );
    } finally {
      setBusy(null);
    }
  }

  async function handleRunResilienceMatrix() {
    setBusy('resilience-matrix');
    try {
      const res = await fetch('/api/resilience/matrix', { method: 'POST' });
      if (res.ok) {
        const json = (await res.json()) as {
          matrix: MandatoryResilienceMatrixSnapshot;
        };
        setResilienceMatrix(json.matrix);
        setBanner(
          `Executed ${json.matrix.localPrechecksPassedCount}/${json.matrix.totalScenarios} local UNIT PRE-CHECKS ONLY · Remote fault injections passed: ${json.matrix.remoteFaultInjectionsPassedCount}/${json.matrix.totalScenarios} (${json.matrix.resilienceVerdict}).`
        );
      }
    } finally {
      setBusy(null);
    }
  }

  async function handleRefreshGithubInventory() {
    setBusy('refresh-github');
    try {
      const res = await fetch('/api/audit/refresh-github', { method: 'POST' });
      const json = (await res.json()) as {
        ok?: boolean;
        refreshResult?: {
          inventoryFreshness: string;
          liveFailedRunsTotal: number | null;
          reposLiveMeasuredCount: number;
          reposQueriedCount: number;
        };
        settlement?: UniversalKarmicSettlementSnapshot;
        error?: string;
      };
      if (json.settlement) {
        setUniversalSettlement(json.settlement);
      }
      if (json.ok && json.refreshResult) {
        const rr = json.refreshResult;
        setBanner(
          `GitHub inventory refreshed (${rr.inventoryFreshness}): measured ${rr.reposLiveMeasuredCount}/${rr.reposQueriedCount} repos (live total=${rr.liveFailedRunsTotal ?? 'BLIND/PARTIAL_RATE_LIMITED'}).`
        );
      } else {
        setBanner(`GitHub refresh failed: ${json.error ?? 'Network or rate limit unavailable'}`);
      }
    } finally {
      setBusy(null);
    }
  }

  if (!snap) {
    return (
      <div className="bg-white border border-slate-200 rounded-xl p-6 text-xs text-slate-500">
        Connecting to Server-Authoritative OMNIFLOW SSE Room (`/api/omniflow/stream`)…
      </div>
    );
  }

  const probe = snap.externalSpineProbe;

  return (
    <div className="space-y-6">
      {/* Top Hero Strip + Real Cloud Spine Probe */}
      <section className="bg-white border border-slate-200 rounded-xl p-5 space-y-4">
        <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-4 border-b border-slate-100 pb-4">
          <div className="space-y-1 min-w-0">
            <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs font-mono">
              <span className="inline-flex items-center gap-1.5 font-semibold text-emerald-700">
                <Radio className="h-3.5 w-3.5" aria-hidden="true" />
                {sseLive ? 'LIVE SSE STREAM CONNECTED (0 POLLING)' : 'SSE RECONNECTING…'}
              </span>
              <span aria-hidden="true">·</span>
              <span className="text-slate-600 tabular-nums">
                {snap.connectedParticipantsCount} active surface(s)
              </span>
              <span aria-hidden="true">·</span>
              <span className="text-slate-600 tabular-nums">
                Fence f_{snap.fenceEpoch}
              </span>
              <span aria-hidden="true">·</span>
              <span className="text-slate-600 tabular-nums">
                {snap.recoveredExpiredLeasesCount} auto-recovered lease(s)
              </span>
            </div>
            <h3 className="text-lg font-bold text-slate-900">
              OMNIFLOW Universal Real-Time Collaboration Room (#7481 · #8133 · #7794)
            </h3>
            <p className="text-xs text-slate-600 max-w-3xl">
              One shared server-authoritative bus for Console CLIs, Web tabs, API models, Cloud
              runners, and WhatsApp/Telegram. Every message carries idempotency keys, monotonic
              fencing tokens, and automatic lease recovery if a worker drops.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2 shrink-0">
            <a
              href="/api/omniflow/pages-function-script"
              download="pages-api-route.ts"
              className="min-h-[38px] inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-800 hover:bg-slate-50 whitespace-nowrap"
            >
              <Download className="h-3.5 w-3.5" aria-hidden="true" />
              Pages Function (.ts)
            </a>
            <a
              href="/api/omniflow/worker-script"
              download="cloudflare-omniflow-bus.ts"
              className="min-h-[38px] inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-800 hover:bg-slate-50 whitespace-nowrap"
            >
              <Download className="h-3.5 w-3.5" aria-hidden="true" />
              Cloudflare Edge Spine (.ts)
            </a>
            <a
              href="/api/omniflow/cli-script"
              download="estate-bus-cli.mjs"
              className="min-h-[38px] inline-flex items-center gap-1.5 rounded-lg bg-slate-900 px-3 py-1.5 text-xs font-semibold text-white hover:bg-slate-800 whitespace-nowrap"
            >
              <Terminal className="h-3.5 w-3.5 text-cyan-400" aria-hidden="true" />
              Console Bridge CLI (.mjs)
            </a>
          </div>
        </div>

        {/* Explicit Non-Live Historical Snapshot Warning when static edge projection is active */}
        {!snapshotLiveState.isLiveState && (
          <div className="rounded-lg border border-rose-300 bg-rose-50 px-4 py-2.5 text-xs font-mono text-rose-900">
            <span className="font-bold">HISTORICAL_BUILD_SNAPSHOT_NOT_LIVE</span> · Viewing static build artifacts ({snapshotLiveState.telemetryFreshness}). These figures are NOT live runtime telemetry.
          </div>
        )}

        {/* Fail-Closed External Certification Withheld Banner (Zero Fake Greens / Never "nothing awaiting you") */}
        {universalSettlement && !universalSettlement.settled && (
          <div className="rounded-lg border border-amber-300 bg-amber-50/70 px-4 py-3 text-xs space-y-1">
            <div className="flex flex-wrap items-center justify-between gap-2 font-mono font-bold text-amber-900">
              <span>
                OPERATIONAL CERTIFICATION WITHHELD · HISTORICAL BASELINE {universalSettlement.allSeeingEye.historicalBaselineFailedRuns} RUNS · LIVE INVENTORY: {universalSettlement.allSeeingEye.liveFailedWorkflowRunsCount ?? 'UNREFRESHED/BLIND'} ({universalSettlement.allSeeingEye.inventoryFreshness})
              </span>
              <span>Argon #62 · Build {universalSettlement.allSeeingEye.deployedBuildObserved.split(' ')[0]}</span>
            </div>
            <p className="text-amber-900 [overflow-wrap:anywhere]">
              {universalSettlement.allSeeingEye.neverShowFalseGreenCopy}{' '}
              {!sseLive && 'SSE stream currently offline/static — remote Cloudflare DO edge adapter & Pages Function deployment required.'}
            </p>
          </div>
        )}

        {banner && (
          <div className="rounded-lg border border-slate-300 bg-slate-50 px-3.5 py-2.5 text-xs font-mono text-slate-900 flex items-center justify-between gap-3">
            <span className="min-w-0 [overflow-wrap:anywhere]">{banner}</span>
            <button
              type="button"
              onClick={() => setBanner(null)}
              className="text-slate-500 hover:text-slate-900 font-sans font-semibold shrink-0"
            >
              Dismiss
            </button>
          </div>
        )}

        {/* Outside-In Probe Bar (Enforces defect/live-services-failed-while-declared-2026-11-16) */}
        <form
          onSubmit={(ev) => void handleProbeExternal(ev)}
          className="rounded-lg border border-slate-200 bg-slate-50/70 p-3.5 flex flex-col lg:flex-row lg:items-center gap-3"
        >
          <div className="flex-1 min-w-0 space-y-1">
            <div className="flex flex-wrap items-center gap-2 text-xs">
              <span className="font-semibold text-slate-900">
                External Cloud Spine Probe (Zero Fake Greens):
              </span>
              <span
                className={`font-mono font-semibold ${
                  probe.status === 'LIVE_VERIFIED'
                    ? 'text-emerald-700'
                    : probe.status === 'NOT_PROBED'
                      ? 'text-slate-600'
                      : 'text-amber-700'
                }`}
              >
                {probe.status}
              </span>
              {probe.dnsResolvedIps.length > 0 && (
                <span className="font-mono text-[11px] text-slate-500">
                  DNS: {probe.dnsResolvedIps.join(', ')}
                </span>
              )}
            </div>
            <div className="text-[11px] font-mono text-slate-600 [overflow-wrap:anywhere]">
              {probe.errorDetail ??
                `Verified HTTP ${probe.httpStatus} in ${probe.latencyMs}ms · sha256:${probe.receiptSha256.slice(0, 12)}`}
            </div>
          </div>

          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2 shrink-0">
            <input
              type="url"
              aria-label="External cloud bus health URL"
              value={probeUrl}
              onChange={(e) => setProbeUrl(e.target.value)}
              className="min-h-[38px] w-full sm:w-80 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-mono text-slate-900"
            />
            <button
              type="submit"
              disabled={busy !== null}
              className="min-h-[38px] inline-flex items-center justify-center gap-1.5 rounded-lg border border-slate-900 bg-slate-900 px-3.5 py-1.5 text-xs font-semibold text-white hover:bg-slate-800 disabled:opacity-50 whitespace-nowrap"
            >
              <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" />
              {busy === 'probe' ? 'Probing DNS & HTTP…' : 'Probe Live Endpoint'}
            </button>
          </div>
        </form>

        {/* EP-A 100% Guarantee Else No Admission & Auto-Decompose Guard */}
        <div className="rounded-lg border border-slate-200 bg-white p-4 space-y-3">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
            <div>
              <h4 className="text-sm font-bold text-slate-900">
                EP-A 100%-Guarantee Admission &amp; Auto-Decompose Guard (RFCE #8188 · bin/verify_three_proofs.py)
              </h4>
              <p className="text-xs text-slate-600">
                Pre-token delivery boundary: unsealed changes require declared manifest P with{' '}
                <span className="font-mono font-semibold">1 subsystem</span> and{' '}
                <span className="font-mono font-semibold">&lt;= 5 files</span> — otherwise NO
                ADMISSION (0 tokens spent) or auto-split into compliant lanes.
              </p>
            </div>
            <div className="text-xs font-mono text-slate-600 tabular-nums shrink-0">
              Rejected: {snap.admissionBoundaryRejectedCount} · Auto-lanes:{' '}
              {snap.autoDecomposedLanesCount}
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-3 items-start">
            <div className="lg:col-span-7 space-y-2">
              <label htmlFor="epa-manifest" className="block text-xs font-medium text-slate-700">
                Proposed Change Manifest P (comma or newline separated)
              </label>
              <textarea
                id="epa-manifest"
                rows={2}
                value={manifestText}
                onChange={(e) => setManifestText(e.target.value)}
                className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-mono text-slate-900"
              />
              <label className="inline-flex items-center gap-2 text-xs text-slate-700 cursor-pointer">
                <input
                  type="checkbox"
                  checked={requireExternalLive}
                  onChange={(e) => setRequireExternalLive(e.target.checked)}
                  className="rounded border-slate-300 text-slate-900"
                />
                <span>
                  Require External Cloud Spine = LIVE_VERIFIED (else refuse admission: {probe.status})
                </span>
              </label>
            </div>

            <div className="lg:col-span-5 flex flex-col gap-2 pt-0 lg:pt-5">
              <button
                type="button"
                disabled={busy !== null}
                onClick={() => void handleValidateManifest()}
                className="min-h-[38px] inline-flex items-center justify-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3.5 py-1.5 text-xs font-semibold text-slate-900 hover:bg-slate-50 disabled:opacity-50"
              >
                <ShieldCheck className="h-3.5 w-3.5 text-slate-700" aria-hidden="true" />
                {busy === 'validate-manifest'
                  ? 'Validating Manifest…'
                  : 'Validate Admission Gate (Pre-Token)'}
              </button>
              <button
                type="button"
                disabled={busy !== null || parseManifestFiles().length === 0}
                onClick={() => void handleAutoDecomposeDispatch()}
                className="min-h-[38px] inline-flex items-center justify-center gap-1.5 rounded-lg bg-slate-900 px-3.5 py-1.5 text-xs font-semibold text-white hover:bg-slate-800 disabled:opacity-50"
              >
                <Send className="h-3.5 w-3.5 text-cyan-400" aria-hidden="true" />
                {busy === 'auto-decompose'
                  ? 'Decomposing & Dispatching…'
                  : 'Auto-Decompose & Dispatch Compliant Lanes'}
              </button>
            </div>
          </div>

          {guardResult && (
            <div
              className={`rounded-lg border p-3 text-xs space-y-2 ${
                guardResult.zeroGaslightDecision?.admitted
                  ? 'border-emerald-200 bg-emerald-50/50 text-slate-900'
                  : 'border-amber-300 bg-amber-50/50 text-slate-900'
              }`}
            >
              <div className="flex flex-wrap items-center justify-between gap-2 font-mono">
                <span className="font-bold">
                  {guardResult.zeroGaslightDecision?.admitted
                    ? 'ADMITTED_ZERO_GASLIGHT (HTTP 200)'
                    : `NO ADMISSION · HTTP ${guardResult.zeroGaslightDecision?.httpStatus ?? 422} · ${guardResult.zeroGaslightDecision?.status ?? 'BOUNDARY_INVALID_NO_ADMISSION'}`}
                </span>
                <span className="text-[11px] text-slate-600 tabular-nums">
                  tokensSpentBeforeReject=0 · files={guardResult.fileCount}/5 · subsystems=
                  {guardResult.subsystemCount}
                </span>
              </div>
              <p className="text-xs text-slate-700 [overflow-wrap:anywhere]">
                {guardResult.zeroGaslightDecision?.explanation ?? guardResult.summary}
              </p>
              {guardResult.decomposedLanes.length > 0 && (
                <div className="grid grid-cols-1 md:grid-cols-3 gap-2 pt-1">
                  {guardResult.decomposedLanes.map((lane) => (
                    <div
                      key={lane.laneId}
                      className="rounded border border-slate-200 bg-white p-2 font-mono text-[11px] space-y-0.5"
                    >
                      <div className="font-bold text-slate-900">{lane.laneId}</div>
                      <div className="text-slate-600">
                        subsystem={lane.subsystem} · {lane.fileCount}/5 file(s)
                      </div>
                      <div className="text-slate-500 truncate">{lane.files.join(', ')}</div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Mathematical Proof & CA1-CA5 Operational Restitution Settlement Gate */}
        {mathProof && (
          <div className="rounded-lg border border-slate-200 bg-slate-50/70 p-4 space-y-3 min-w-0 overflow-hidden">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 min-w-0">
              <div className="space-y-0.5 min-w-0">
                <h4 className="text-sm font-bold text-slate-900">
                  Mathematical Proof &amp; CA1–CA5 Operational Restitution Gate ({mathProof.settlement.karmaRecordId})
                </h4>
                <p className="text-xs text-slate-600 [overflow-wrap:anywhere]">
                  Compensation = Operational Restoration (never monetary). Settlement remains{' '}
                  <span className="font-mono font-semibold text-amber-800 break-all">
                    {mathProof.settlement.overallSettlementVerdict}
                  </span>
                </p>
              </div>
              <button
                type="button"
                disabled={busy !== null}
                onClick={() => void handleRunMathProof()}
                className="min-h-[36px] inline-flex items-center justify-center gap-1.5 rounded-lg border border-slate-900 bg-slate-900 px-3 py-1.5 text-xs font-semibold text-white hover:bg-slate-800 disabled:opacity-50 shrink-0"
              >
                <ShieldCheck className="h-3.5 w-3.5 text-emerald-400" aria-hidden="true" />
                {busy === 'math-proof' ? 'Replaying Subsets…' : 'Re-Run Exhaustive Proof'}
              </button>
            </div>

            <div className="rounded border border-slate-200 bg-white p-3 space-y-2 text-xs min-w-0">
              <div className="flex flex-wrap items-center justify-between gap-2 font-mono">
                <span className="font-bold text-emerald-800">
                  {mathProof.proof.mathematicalTheoremProven
                    ? 'THEOREM PROVEN (0 COUNTEREXAMPLES)'
                    : 'THEOREM CHECK FAILED'}
                </span>
                <span className="text-[11px] text-slate-600 tabular-nums [overflow-wrap:anywhere]">
                  {mathProof.proof.exhaustiveModelStats.validNonEmptySubsetsTested} non-empty subsets (Ø != D ⊆ M) · 0 violations ·{' '}
                  {mathProof.proof.exhaustiveModelStats.invalidMultiSubsystemBlockedCount} invalid multi-subsystem blocked ·{' '}
                  {mathProof.proof.exhaustiveModelStats.proofExecutionMs}ms
                </span>
              </div>
              <p className="text-slate-700 leading-relaxed [overflow-wrap:anywhere]">
                {mathProof.proof.theoremStatement}
              </p>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-2 pt-1">
                {mathProof.proof.lemmas.map((l) => (
                  <div
                    key={l.lemmaId}
                    className="rounded border border-slate-200 bg-slate-50/70 p-2 text-[11px] space-y-0.5 min-w-0"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-1 font-mono font-bold text-slate-900">
                      <span>{l.title}</span>
                      <span className={l.proven ? 'text-emerald-700' : 'text-rose-700'}>
                        {l.proven ? 'PROVEN' : 'FAILED'}
                      </span>
                    </div>
                    <div className="font-mono text-slate-700 [overflow-wrap:anywhere]">
                      {l.formalStatement}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-3 min-w-0">
              <div className="rounded border border-slate-200 bg-white p-3 space-y-1.5 min-w-0">
                <div className="text-xs font-bold text-slate-900">CA1–CA5 Settlement Gates</div>
                {mathProof.settlement.caGates.map((g) => (
                  <div key={g.gateId} className="text-[11px] border-t border-slate-100 pt-1.5 first:border-t-0 first:pt-0 min-w-0">
                    <div className="flex flex-wrap items-center justify-between gap-1 font-mono font-semibold">
                      <span className="text-slate-900">{g.gateId}</span>
                      <span
                        className={`break-all ${
                          g.status === 'SATISFIED_MATHEMATICALLY_LOCAL'
                            ? 'text-emerald-700'
                            : 'text-amber-700'
                        }`}
                      >
                        {g.status}
                      </span>
                    </div>
                    <div className="text-slate-600 [overflow-wrap:anywhere]">{g.requirement}</div>
                  </div>
                ))}
              </div>

              <div className="rounded border border-slate-200 bg-white p-3 space-y-1.5 min-w-0">
                <div className="text-xs font-bold text-slate-900">
                  Recovery Mandate Table (Local Enforced vs External Estate Receipt)
                </div>
                {mathProof.settlement.mandateTable.map((row) => (
                  <div
                    key={row.referenceId}
                    className="text-[11px] border-t border-slate-100 pt-1.5 first:border-t-0 first:pt-0 min-w-0"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-1 font-mono">
                      <span className="font-bold text-slate-900">
                        {row.obligation} ({row.referenceId})
                      </span>
                      <span className="text-amber-700 font-semibold break-all">
                        {row.externalEstateStatus}
                      </span>
                    </div>
                    <div className="text-slate-600 [overflow-wrap:anywhere]">{row.detail}</div>
                  </div>
                ))}
              </div>
            </div>

            {mathProof.settlement.measuredHosts && (
              <div className="rounded border border-slate-200 bg-white p-3 space-y-2 min-w-0">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="text-xs font-bold text-slate-900">
                    R-ZAI-01 Measured External Hosts (ZAI-BR-01-P0-20261117 · 1/8 Live, 7/8 Gated NO_ADMISSION)
                  </div>
                  <span className="text-[11px] font-mono text-slate-500">
                    c146299 bin/estate-live-probe
                  </span>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2">
                  {mathProof.settlement.measuredHosts.map((h) => (
                    <div
                      key={h.host}
                      className="rounded border border-slate-200 bg-slate-50/60 p-2 text-[11px] space-y-0.5 min-w-0"
                    >
                      <div className="font-mono font-bold text-slate-900 [overflow-wrap:anywhere]">{h.host}</div>
                      <div
                        className={`font-mono font-semibold ${
                          h.admissionAllowed ? 'text-emerald-700' : 'text-amber-700'
                        }`}
                      >
                        {h.verdict} · {h.admissionAllowed ? 'ADMIT' : 'NO_ADMISSION'}
                      </div>
                      <div className="text-slate-600 [overflow-wrap:anywhere]">{h.detail}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* KARMA #7452 & #8030 Universal Settlement Gate + 7-Seat Browser Workforce (BR-KIMI-01) + Auto-Sync Live */}
        {universalSettlement && (
          <div className="rounded-lg border border-slate-300 bg-white p-4 space-y-4 min-w-0 overflow-hidden">
            <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-2 border-b border-slate-100 pb-3 min-w-0">
              <div className="space-y-0.5 min-w-0">
                <div className="flex flex-wrap items-center gap-2 text-[11px] font-mono">
                  <span className="font-bold text-slate-900">
                    {universalSettlement.karmaAuthorityId} &amp; {universalSettlement.centralComplaintAuthorityId}
                  </span>
                  <span aria-hidden="true">·</span>
                  <span className="text-slate-600 tabular-nums">
                    Repetition Burden: {universalSettlement.totalAccumulatedRepetitions}x ({universalSettlement.proportionalAssuranceMultiplier}x depth)
                  </span>
                  <span aria-hidden="true">·</span>
                  <span
                    className={`font-bold break-all ${
                      universalSettlement.settled ? 'text-emerald-700' : 'text-amber-700'
                    }`}
                  >
                    {universalSettlement.verdict}
                  </span>
                </div>
                <h4 className="text-sm font-bold text-slate-900">
                  Universal Settlement Ledger (Settlement &hArr; &forall; o &isin; O, Verified(o))
                </h4>
                <p className="text-xs text-slate-600 [overflow-wrap:anywhere]">
                  Local Verified: {universalSettlement.localVerifiedCount}/{universalSettlement.totalObligationsCount} ·
                  External Live Verified: {universalSettlement.externalLiveVerifiedCount}/{universalSettlement.totalObligationsCount} ·
                  Doctrine: {universalSettlement.compensationDoctrine}
                </p>
              </div>

              {autoSyncInfo && (
                <div className="flex flex-wrap items-center gap-2 shrink-0">
                  <button
                    type="button"
                    disabled={busy !== null}
                    onClick={() => void handleTriggerAutoSyncNow()}
                    className="min-h-[36px] inline-flex items-center justify-center gap-1.5 rounded-lg bg-slate-900 px-3 py-1.5 text-xs font-semibold text-white hover:bg-slate-800 disabled:opacity-50"
                  >
                    <RefreshCw className="h-3.5 w-3.5 text-cyan-400" aria-hidden="true" />
                    {busy === 'auto-sync' ? 'Syncing & Probing…' : 'Trigger Sync Cycle Now'}
                  </button>
                </div>
              )}
            </div>

            {/* Zero-Reminder Auto-Sync Strip + 1-Click BR-KIMI-01 / Browser Workforce Onboarding */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-3 min-w-0">
              {autoSyncInfo && (
                <div className="lg:col-span-6 rounded border border-slate-200 bg-slate-50/70 p-3 space-y-1.5 text-xs min-w-0">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="font-bold text-slate-900">
                      Zero-Reminder 45s Bundle Auto-Sync
                    </span>
                    <span
                      className={`font-mono text-[11px] font-semibold ${
                        autoSyncInfo.lastAcceptedBundleSha256
                          ? 'text-emerald-700'
                          : 'text-amber-700'
                      }`}
                    >
                      {autoSyncInfo.daemonActive ? 'DAEMON ACTIVE (45s)' : 'DAEMON OFF'} ·{' '}
                      {autoSyncInfo.lastAcceptedBundleSha256 ? 'REMOTE_ACCEPTED' : 'LOCAL_SEALED_ONLY'}
                    </span>
                  </div>
                  <div className="font-mono text-[11px] text-slate-700 space-y-0.5 break-all">
                    <div>
                      HEAD: {autoSyncInfo.currentHeadSha.slice(0, 12)} · Bundle:{' '}
                      {autoSyncInfo.currentBundleSha256?.slice(0, 12) ?? 'none'} (
                      {Math.round(autoSyncInfo.currentBundleBytes / 1024)} KB)
                    </div>
                    <div className="text-slate-600 [overflow-wrap:anywhere]">
                      Outbound Reason:{' '}
                      {autoSyncInfo.lastReason ??
                        'Pending first remote 200 OK from Pages / pre-signed PUT'}
                    </div>
                  </div>
                </div>
              )}

              <div className="lg:col-span-6 rounded border border-slate-200 bg-slate-50/70 p-3 space-y-2 text-xs min-w-0">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="font-bold text-slate-900">
                    7-Seat Browser Workforce ({universalSettlement.browserWorkforceRefinedCount}/{universalSettlement.browserWorkforceCount} Registered Only · {universalSettlement.browserWorkforceAuthenticatedExecutionsCount}/{universalSettlement.browserWorkforceCount} Authenticated Executions Verified)
                  </span>
                </div>
                <div className="flex flex-col sm:flex-row gap-2 min-w-0">
                  <select
                    aria-label="Browser workforce seat"
                    value={selectedBrowserWorker}
                    onChange={(e) => setSelectedBrowserWorker(e.target.value)}
                    className="flex-1 min-w-0 min-h-[36px] rounded-lg border border-slate-300 bg-white px-2.5 py-1 text-xs font-mono text-slate-900"
                  >
                    {universalSettlement.browserWorkforce.map((bw) => (
                      <option key={bw.worker.workerId} value={bw.worker.workerId}>
                        {bw.worker.workerId} — {bw.executionStatus}
                      </option>
                    ))}
                  </select>
                  <button
                    type="button"
                    disabled={busy !== null}
                    onClick={() => void handleOnboardBrowserWorker(selectedBrowserWorker)}
                    className="min-h-[36px] inline-flex items-center justify-center gap-1.5 rounded-lg border border-slate-900 bg-slate-900 px-3 py-1.5 text-xs font-semibold text-white hover:bg-slate-800 disabled:opacity-50 shrink-0"
                  >
                    <UserPlus className="h-3.5 w-3.5 text-emerald-400" aria-hidden="true" />
                    {busy === 'onboard-worker'
                      ? 'Checking 9-Tuple…'
                      : `Register ${selectedBrowserWorker} Schema Only`}
                  </button>
                </div>
                {lastOnboardingResult && (
                  <div className="text-[11px] font-mono text-slate-700 [overflow-wrap:anywhere]">
                    {lastOnboardingResult.honestStatusNote}
                  </div>
                )}
              </div>
            </div>

            {/* Mission #7760 Dedicated gemini-sync Receiver & DO Edge Adapter Convergence */}
            {universalSettlement.geminiSync7760 && (
              <div className="rounded border border-slate-200 bg-slate-50/70 p-3 space-y-2 text-xs min-w-0">
                <div className="flex flex-wrap items-center justify-between gap-2 font-mono">
                  <span className="font-bold text-slate-900">
                    Mission {universalSettlement.geminiSync7760.missionId} · {universalSettlement.geminiSync7760.existingReceiverRepo} ({universalSettlement.geminiSync7760.ciTestsPassedCount}/6 CI Checks Passed · Cap {universalSettlement.geminiSync7760.maxBundleLabel})
                  </span>
                  <span className={universalSettlement.geminiSync7760.latestSourceInPrivateGithubCustody ? 'text-emerald-700 font-bold' : 'text-amber-700 font-bold'}>
                    {universalSettlement.geminiSync7760.latestSourceInPrivateGithubCustody ? 'CUSTODY_DELIVERED' : 'UNDEPLOYED · CUSTODY_MISSING'}
                  </span>
                </div>
                <p className="text-[11px] text-slate-700 [overflow-wrap:anywhere]">
                  {universalSettlement.geminiSync7760.honestStatusSummary} DO Worker is strictly scoped as an edge adapter to canonical OMNIFLOW (not a competing authority).
                </p>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-[11px]">
                  <div className="rounded border border-slate-200 bg-white p-2 space-y-1">
                    <div className="font-bold text-slate-900">6/6 Verified Receiver Assurance in gemini-sync</div>
                    <ul className="list-disc pl-4 text-slate-700 space-y-0.5">
                      {universalSettlement.geminiSync7760.ciPassingChecks.map((chk) => (
                        <li key={chk}>{chk}</li>
                      ))}
                    </ul>
                  </div>
                  <div className="rounded border border-slate-200 bg-white p-2 space-y-1">
                    <div className="font-bold text-slate-900">Mandatory Edge Controls Before Settlement</div>
                    <ul className="list-disc pl-4 text-slate-700 space-y-0.5">
                      {universalSettlement.geminiSync7760.requiredEdgeControls.map((ctrl) => (
                        <li key={ctrl}>{ctrl}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>
            )}

            {/* All 5 Accumulated Obligations o in O */}
            <div className="divide-y divide-slate-100 rounded border border-slate-200 bg-white min-w-0">
              {universalSettlement.obligations.map((obl) => (
                <div key={obl.obligationId} className="p-3 space-y-1 text-xs min-w-0">
                  <div className="flex flex-wrap items-center justify-between gap-2 font-mono">
                    <div className="font-bold text-slate-900 min-w-0 [overflow-wrap:anywhere]">
                      {obl.title} ({obl.referenceIds.join(' · ')}) · Repeated {obl.founderRepetitionsCount}x
                    </div>
                    <div className="flex flex-wrap items-center gap-2 shrink-0 text-[11px] font-semibold">
                      <span className={obl.localVerified ? 'text-emerald-700' : 'text-amber-700'}>
                        LOCAL: {obl.localVerified ? 'VERIFIED' : 'OPEN'}
                      </span>
                      <span aria-hidden="true">·</span>
                      <span className={obl.externalLiveVerified ? 'text-emerald-700' : 'text-amber-700'}>
                        EXTERNAL: {obl.externalLiveVerified ? 'LIVE_VERIFIED' : 'UNSETTLED_EXTERNAL'}
                      </span>
                    </div>
                  </div>
                  <div className="text-[11px] text-slate-600 [overflow-wrap:anywhere]">
                    <span className="font-semibold text-slate-800">Local:</span> {obl.localEvidence}{' '}
                    <span className="font-semibold text-slate-800">External:</span> {obl.externalEvidence}
                  </div>
                </div>
              ))}
            </div>

            {/* Founder-Friction Operational Compensation Mechanisms + 1-Click External Unblock Pack */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-3 min-w-0">
              <div className="lg:col-span-6 rounded border border-slate-200 bg-slate-50/70 p-3 space-y-2 min-w-0">
                <div className="text-xs font-bold text-slate-900">
                  Operational Restitution: 5 Active Friction-Elimination Compensations
                </div>
                {universalSettlement.compensationMechanisms.map((c) => (
                  <div
                    key={c.compensationId}
                    className="rounded border border-slate-200 bg-white p-2 text-[11px] space-y-0.5 min-w-0"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-1 font-mono font-bold text-slate-900">
                      <span>{c.compensationId}</span>
                      <span className="text-emerald-700">{c.founderTimeSavedEstimate}</span>
                    </div>
                    <div className="text-slate-600 [overflow-wrap:anywhere]">
                      {c.operationalMechanism}
                    </div>
                  </div>
                ))}
              </div>

              <div className="lg:col-span-6 rounded border border-slate-200 bg-slate-950 text-slate-100 p-3 space-y-2 min-w-0">
                <div className="text-xs font-bold text-white">
                  1-Click External Estate Unblock Command Pack (Closes Remaining CA4/CA5 Externally)
                </div>
                {universalSettlement.unblockPackCommands.map((cmd) => (
                  <div
                    key={cmd.id}
                    className="rounded border border-slate-800 bg-slate-900/90 p-2 space-y-1 text-[11px] min-w-0"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-semibold text-cyan-200 min-w-0 [overflow-wrap:anywhere]">
                        {cmd.label}
                      </span>
                      <button
                        type="button"
                        onClick={() => void copyText(cmd.id, cmd.command)}
                        className="inline-flex items-center gap-1 rounded border border-slate-700 bg-slate-800 px-2 py-0.5 text-[11px] font-semibold text-cyan-300 hover:bg-slate-700 shrink-0"
                      >
                        {copiedKey === cmd.id ? (
                          <>
                            <Check className="h-3 w-3" aria-hidden="true" />
                            Copied
                          </>
                        ) : (
                          <>
                            <Copy className="h-3 w-3" aria-hidden="true" />
                            Copy
                          </>
                        )}
                      </button>
                    </div>
                    <pre className="font-mono text-[10px] text-slate-300 whitespace-pre-wrap break-all">
                      {cmd.command}
                    </pre>
                  </div>
                ))}
              </div>
            </div>

            {/* 9 Explicit KARMA Restitution Outcomes (Measurable Operational Delivery Only) */}
            {universalSettlement.restitutionOutcomes && (
              <div className="rounded border border-slate-200 bg-slate-50/60 p-3 space-y-2 min-w-0">
                <div className="text-xs font-bold text-slate-900">
                  KARMA #7452 — 9 Required Operational Restitution Outcomes (Measured Delivery vs Local Prerequisite)
                </div>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
                  {universalSettlement.restitutionOutcomes.map((ro) => (
                    <div
                      key={ro.outcomeId}
                      className="rounded border border-slate-200 bg-white p-2.5 text-[11px] space-y-1 min-w-0"
                    >
                      <div className="flex flex-wrap items-center justify-between gap-1 font-mono font-bold">
                        <span className="text-slate-900">{ro.operationalRestitution}</span>
                        <span
                          className={
                            ro.deliveryStatus === 'MEASURED_DELIVERED'
                              ? 'text-emerald-700'
                              : ro.deliveryStatus === 'PARTIAL_LOCAL_PREREQUISITE_ONLY'
                                ? 'text-amber-700'
                                : 'text-rose-700'
                          }
                        >
                          {ro.deliveryStatus === 'MEASURED_DELIVERED'
                            ? 'DELIVERED'
                            : ro.deliveryStatus === 'PARTIAL_LOCAL_PREREQUISITE_ONLY'
                              ? 'LOCAL_PREREQ_ONLY'
                              : 'NOT_DELIVERED'}
                        </span>
                      </div>
                      <div className="font-medium text-slate-800 [overflow-wrap:anywhere]">
                        {ro.requiredOutcome}
                      </div>
                      <div className="font-mono text-[10px] text-slate-700 [overflow-wrap:anywhere]">
                        Measured: {ro.measuredDeliveryMetric}
                      </div>
                      <div className="text-[10px] text-slate-500 [overflow-wrap:anywhere]">
                        SLO: {ro.targetSlo} · {ro.honestGapNote}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* 10 Mandatory Resilience Verification Scenarios (Unit Pre-Checks vs Remote Fault Injection) */}
            {resilienceMatrix && (
              <div className="rounded border border-slate-200 bg-white p-3 space-y-2.5 min-w-0">
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 min-w-0">
                  <div className="space-y-0.5 min-w-0">
                    <div className="text-xs font-bold text-slate-900">
                      Unit Pre-Checks vs Actual Remote Fault Injection ({resilienceMatrix.localPrechecksPassedCount}/{resilienceMatrix.totalScenarios} Unit Pre-Checks · {resilienceMatrix.remoteFaultInjectionsPassedCount}/{resilienceMatrix.totalScenarios} Remote Faults Executed — {resilienceMatrix.productionCertified ? 'CERTIFIED' : 'WITHHELD'})
                    </div>
                    <p className="text-[11px] text-slate-600 [overflow-wrap:anywhere]">
                      {resilienceMatrix.externalBlockerSummary}
                    </p>
                  </div>
                  <button
                    type="button"
                    disabled={busy !== null}
                    onClick={() => void handleRunResilienceMatrix()}
                    className="min-h-[34px] inline-flex items-center justify-center gap-1.5 rounded-lg border border-slate-900 bg-slate-900 px-3 py-1 text-xs font-semibold text-white hover:bg-slate-800 disabled:opacity-50 shrink-0"
                  >
                    <ShieldCheck className="h-3.5 w-3.5 text-emerald-400" aria-hidden="true" />
                    {busy === 'resilience-matrix'
                      ? 'Running Unit Pre-Checks…'
                      : 'Run Local Unit Pre-Checks Only (0/10 Remote Faults)'}
                  </button>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                  {resilienceMatrix.scenarios.map((sc) => (
                    <div
                      key={sc.scenarioId}
                      className="rounded border border-slate-200 bg-slate-50/70 p-2 text-[11px] space-y-0.5 min-w-0"
                    >
                      <div className="flex flex-wrap items-center justify-between gap-1 font-mono font-bold">
                        <span className="text-slate-900">
                          {sc.scenarioId}: {sc.failureScenario} &rarr; {sc.requiredOperationalProof}
                        </span>
                        <span className="inline-flex items-center gap-1 shrink-0">
                          <span className={sc.localUnitPrecheckPassed ? 'text-emerald-700' : 'text-rose-700'}>
                            {sc.localUnitPrecheckPassed ? 'UNIT_PRECHECK_OK' : 'UNIT_FAIL'}
                          </span>
                          <span className="text-slate-400">·</span>
                          <span className={sc.remoteFaultInjectionPassed ? 'text-emerald-700' : 'text-amber-700'}>
                            {sc.remoteFaultInjectionPassed ? 'REMOTE_PASSED' : 'REMOTE_0/1_UNEXECUTED'}
                          </span>
                        </span>
                      </div>
                      <div className="text-slate-600 [overflow-wrap:anywhere]">
                        {sc.localPrecheckEvidence}
                      </div>
                      <div className="text-[10px] font-mono text-slate-500 [overflow-wrap:anywhere]">
                        Required remote injection: {sc.requiredRemoteInjectionMethod}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Updated All-Seeing Eye Independent Audit (Continuous GitHub Inventory vs 359 Historical Baseline) */}
            {universalSettlement.allSeeingEye && (
              <div className="rounded border border-slate-200 bg-slate-50/70 p-3 space-y-2.5 min-w-0">
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
                  <div className="space-y-0.5 min-w-0">
                    <div className="text-xs font-bold text-slate-900">
                      All-Seeing Eye Estate Inventory · Historical Baseline: {universalSettlement.allSeeingEye.historicalBaselineFailedRuns} Runs · Live Failed Runs: {universalSettlement.allSeeingEye.liveFailedWorkflowRunsCount ?? 'UNREFRESHED / BLIND'} ({universalSettlement.allSeeingEye.inventoryFreshness})
                    </div>
                    <div className="text-[11px] font-mono text-slate-600 [overflow-wrap:anywhere]">
                      Repos ({universalSettlement.allSeeingEye.repositoriesInspected}): {universalSettlement.allSeeingEye.repositoriesList.join(', ')}
                      {universalSettlement.allSeeingEye.refreshedAtUtc && ` · Last Refresh: ${universalSettlement.allSeeingEye.refreshedAtUtc}`}
                    </div>
                  </div>
                  <button
                    type="button"
                    disabled={busy !== null}
                    onClick={() => void handleRefreshGithubInventory()}
                    className="min-h-[34px] inline-flex items-center justify-center gap-1.5 rounded-lg border border-slate-900 bg-slate-900 px-3 py-1 text-xs font-semibold text-white hover:bg-slate-800 disabled:opacity-50 shrink-0"
                  >
                    <RefreshCw className="h-3.5 w-3.5 text-cyan-400" aria-hidden="true" />
                    {busy === 'refresh-github' ? 'Querying GitHub API…' : 'Refresh GitHub Inventory Now'}
                  </button>
                </div>

                {universalSettlement.allSeeingEye.repoInventory && (
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
                    {universalSettlement.allSeeingEye.repoInventory.map((r) => (
                      <div key={r.fullRepo} className="rounded border border-slate-200 bg-white p-2 text-[11px] space-y-0.5 min-w-0">
                        <div className="flex items-center justify-between gap-1 font-mono font-bold">
                          <span className="text-slate-900">{r.fullRepo}</span>
                          <span className={r.fetchStatus === 'LIVE_MEASURED' ? 'text-emerald-700' : 'text-amber-700'}>
                            {r.liveFailedCount ?? r.fetchStatus}
                          </span>
                        </div>
                        <div className="text-slate-600 [overflow-wrap:anywhere]">{r.detail}</div>
                      </div>
                    ))}
                  </div>
                )}

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-2.5">
                  <div className="rounded border border-slate-200 bg-white p-2.5 space-y-1.5 text-[11px] min-w-0">
                    <div className="font-bold text-slate-900">
                      7 Audited External Workstreams (17 Nov 2026)
                    </div>
                    {universalSettlement.allSeeingEye.workstreams.map((ws) => (
                      <div key={ws.workstream} className="border-t border-slate-100 pt-1 first:border-t-0 first:pt-0">
                        <div className="flex flex-wrap items-center justify-between gap-1 font-mono font-semibold">
                          <span className="text-slate-900">{ws.workstream}</span>
                          <span className="text-amber-700">{ws.auditedStatus}</span>
                        </div>
                        <div className="text-slate-600 [overflow-wrap:anywhere]">{ws.detail}</div>
                      </div>
                    ))}
                  </div>

                  <div className="rounded border border-slate-200 bg-white p-2.5 space-y-1.5 text-[11px] min-w-0">
                    <div className="font-bold text-slate-900">
                      Outside-In Browser Surface Audit ({universalSettlement.allSeeingEye.deployedBuildObserved})
                    </div>
                    {universalSettlement.allSeeingEye.deployedBrowserChecks.map((chk) => (
                      <div key={chk.surfaceFunction} className="border-t border-slate-100 pt-1 first:border-t-0 first:pt-0">
                        <div className="flex flex-wrap items-center justify-between gap-1 font-mono font-semibold">
                          <span className="text-slate-900">{chk.surfaceFunction}</span>
                          <span className={chk.externalProductionVerified ? 'text-emerald-700' : 'text-amber-700'}>
                            {chk.observedResult}
                          </span>
                        </div>
                        <div className="text-slate-600 [overflow-wrap:anywhere]">
                          Fix ready: {chk.remediationInWorkspace}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </section>

      {/* Main Two-Column Collaboration Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Column: Composer + Live Participant Roster + CLI Join Command */}
        <div className="lg:col-span-5 space-y-5 min-w-0">
          {/* Publish / Broadcast Directive */}
          <form
            onSubmit={(ev) => void handlePublish(ev)}
            className="bg-white border border-slate-200 rounded-xl p-4 space-y-3"
          >
            <div className="text-sm font-bold text-slate-900">
              Send / Broadcast Real-Time Envelope
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
              <div className="space-y-1">
                <label htmlFor="bus-from" className="block text-xs font-medium text-slate-700">
                  From Surface / Agent
                </label>
                <select
                  id="bus-from"
                  value={fromAgent}
                  onChange={(e) => setFromAgent(e.target.value)}
                  className="w-full min-h-[38px] rounded-lg border border-slate-300 bg-white px-2.5 py-1.5 text-xs font-mono text-slate-900"
                >
                  {snap.participants.map((p) => (
                    <option key={p.agentId} value={p.agentId}>
                      {p.agentId} ({p.surfaceClass})
                    </option>
                  ))}
                </select>
              </div>

              <div className="space-y-1">
                <label htmlFor="bus-target" className="block text-xs font-medium text-slate-700">
                  Address Target
                </label>
                <select
                  id="bus-target"
                  value={target}
                  onChange={(e) => setTarget(e.target.value)}
                  className="w-full min-h-[38px] rounded-lg border border-slate-300 bg-white px-2.5 py-1.5 text-xs font-mono text-slate-900"
                >
                  <option value="@all">@all (Full Workforce Broadcast)</option>
                  <option value="@formation:greenlane">@formation:greenlane (CI &amp; Merge)</option>
                  <option value="@formation:concierge">@formation:concierge (Auntie Ezinne)</option>
                  {snap.participants
                    .filter((p) => p.agentId !== fromAgent)
                    .map((p) => (
                      <option key={p.agentId} value={`@agent:${p.agentId}`}>
                        @agent:{p.agentId}
                      </option>
                    ))}
                </select>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 items-center">
              <div className="space-y-1">
                <label htmlFor="bus-verb" className="block text-xs font-medium text-slate-700">
                  OMNIFLOW Verb
                </label>
                <select
                  id="bus-verb"
                  value={verb}
                  onChange={(e) => setVerb(e.target.value as OmniflowMessageVerb)}
                  className="w-full min-h-[38px] rounded-lg border border-slate-300 bg-white px-2.5 py-1.5 text-xs font-mono text-slate-900"
                >
                  {VERB_OPTIONS.map((v) => (
                    <option key={v} value={v}>
                      {v}
                    </option>
                  ))}
                </select>
              </div>

              <label className="inline-flex items-center gap-2 pt-4 text-xs text-slate-700 cursor-pointer">
                <input
                  type="checkbox"
                  checked={requiresClaim}
                  onChange={(e) => setRequiresClaim(e.target.checked)}
                  className="rounded border-slate-300 text-slate-900"
                />
                <span>Require durable fenced lease</span>
              </label>
            </div>

            <div className="space-y-1">
              <label htmlFor="bus-body" className="block text-xs font-medium text-slate-700">
                Message / Task Instruction
              </label>
              <textarea
                id="bus-body"
                rows={3}
                value={body}
                onChange={(e) => setBody(e.target.value)}
                placeholder="Ask a single worker, broadcast to @all, or hand off a PATCH_REF…"
                className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs text-slate-900"
              />
            </div>

            <button
              type="submit"
              disabled={busy !== null || !body.trim()}
              className="w-full min-h-[40px] inline-flex items-center justify-center gap-1.5 rounded-lg bg-slate-900 px-4 py-2 text-xs font-semibold text-white hover:bg-slate-800 disabled:opacity-50"
            >
              <Send className="h-3.5 w-3.5 text-cyan-400" aria-hidden="true" />
              {busy === 'publish' ? 'Publishing via SSE…' : `Publish to ${target}`}
            </button>
          </form>

          {/* Connected Participants + Register Console / Browser / API Worker */}
          <section className="bg-white border border-slate-200 rounded-xl p-4 space-y-3.5">
            <div className="flex items-center justify-between gap-2">
              <h4 className="text-sm font-bold text-slate-900">
                Live Participants ({snap.connectedParticipantsCount} online)
              </h4>
              <span className="text-[11px] font-mono text-slate-500">
                TTL Auto-Recovery Active
              </span>
            </div>

            <div className="divide-y divide-slate-100 rounded-lg border border-slate-200">
              {snap.participants.map((p) => (
                <div key={p.agentId} className="p-3 space-y-1 text-xs">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-mono font-bold text-slate-900 truncate">
                      {p.agentId}
                    </span>
                    <span
                      className={`font-mono text-[11px] font-semibold shrink-0 ${
                        p.connected ? 'text-emerald-700' : 'text-amber-700'
                      }`}
                    >
                      {p.connected ? 'ONLINE' : 'DROPPED'}
                    </span>
                  </div>
                  <div className="text-[11px] text-slate-600 font-mono">
                    {p.surfaceClass} · {p.transport} · leases: {p.activeLeasesCount}
                  </div>
                  <div className="flex flex-wrap items-center justify-between gap-2 pt-1">
                    <span className="text-[11px] text-slate-500 font-mono">
                      [{p.capabilities.join(', ')}]
                    </span>
                    {p.connected && p.agentId !== 'founder-genesis-cockpit' && (
                      <button
                        type="button"
                        disabled={busy !== null}
                        onClick={() => void handleDisconnect(p.agentId)}
                        className="inline-flex items-center gap-1 rounded border border-slate-300 bg-white px-2 py-0.5 text-[11px] font-medium text-slate-700 hover:bg-slate-50"
                      >
                        <WifiOff className="h-3 w-3" aria-hidden="true" />
                        Simulate Drop
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>

            {/* Quick Register Any Agent / Console / Browser */}
            <form onSubmit={(ev) => void handleRegister(ev)} className="pt-2 border-t border-slate-100 space-y-2">
              <div className="text-xs font-semibold text-slate-800">
                Join Console, Browser, or API Worker
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                <input
                  type="text"
                  aria-label="New worker agent ID"
                  value={newAgentId}
                  onChange={(e) => setNewAgentId(e.target.value)}
                  placeholder="glm-5.3-console"
                  className="min-h-[36px] rounded-lg border border-slate-300 px-2.5 py-1 text-xs font-mono text-slate-900"
                />
                <select
                  aria-label="New worker surface class"
                  value={newSurface}
                  onChange={(e) => setNewSurface(e.target.value as BusSurfaceClass)}
                  className="min-h-[36px] rounded-lg border border-slate-300 bg-white px-2.5 py-1 text-xs text-slate-900"
                >
                  {SURFACE_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </div>
              <div className="flex gap-2">
                <input
                  type="text"
                  aria-label="Worker capabilities"
                  value={newCaps}
                  onChange={(e) => setNewCaps(e.target.value)}
                  placeholder="code:patch,idp"
                  className="flex-1 min-h-[36px] rounded-lg border border-slate-300 px-2.5 py-1 text-xs font-mono text-slate-900"
                />
                <button
                  type="submit"
                  disabled={busy !== null || !newAgentId.trim()}
                  className="min-h-[36px] inline-flex items-center gap-1 rounded-lg border border-slate-900 bg-white px-3 py-1 text-xs font-semibold text-slate-900 hover:bg-slate-50 whitespace-nowrap"
                >
                  <UserPlus className="h-3.5 w-3.5" aria-hidden="true" />
                  Join Room
                </button>
              </div>
            </form>

            {/* 1-Line Live Terminal Attach Snippet */}
            <div className="rounded-lg border border-slate-200 bg-slate-950 text-slate-100 p-3 space-y-1.5">
              <div className="flex items-center justify-between gap-2 text-[11px] font-mono text-slate-400">
                <span>Connect Any Live Terminal Right Now (No Polling):</span>
                <button
                  type="button"
                  onClick={() => void copyText('cli', cliJoinCommand)}
                  className="inline-flex items-center gap-1 text-cyan-300 hover:text-cyan-200 font-semibold"
                >
                  {copiedKey === 'cli' ? (
                    <>
                      <Check className="h-3 w-3" aria-hidden="true" />
                      Copied
                    </>
                  ) : (
                    <>
                      <Copy className="h-3 w-3" aria-hidden="true" />
                      Copy CLI Command
                    </>
                  )}
                </button>
              </div>
              <pre className="text-[11px] font-mono text-slate-200 whitespace-pre-wrap break-all">
                {cliJoinCommand}
              </pre>
            </div>
          </section>
        </div>

        {/* Right Column: Live Ordered Message & Custody Feed */}
        <section className="lg:col-span-7 bg-white border border-slate-200 rounded-xl p-4 space-y-3 min-w-0">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-3">
            <div>
              <h4 className="text-sm font-bold text-slate-900">
                Real-Time Ordered OMNIFLOW Stream ({snap.messages.length} envelopes)
              </h4>
              <p className="text-xs text-slate-500 font-mono tabular-nums">
                Open claimable: {snap.openClaimableCount} · Active leases: {snap.activeLeasedCount}{' '}
                · Verified: {snap.verifiedCount} · Stale 409s: {snap.staleFenceRejectionsCount} ·
                Self-verify 403s: {snap.selfVerifyBlockedCount}
              </p>
            </div>
          </div>

          <div className="divide-y divide-slate-100">
            {snap.messages.slice(0, 14).map((msg) => {
              const claimCandidate =
                snap.participants.find(
                  (p) => p.connected && p.agentId !== msg.fromAgent
                )?.agentId ??
                newAgentId.trim() ??
                'glm-5.3-console';

              return (
                <article key={msg.envelopeId} className="py-3.5 space-y-2 text-xs">
                  <div className="flex flex-wrap items-center justify-between gap-2 font-mono">
                    <div className="text-slate-900 font-semibold min-w-0 [overflow-wrap:anywhere]">
                      <span>#{msg.seq}</span>
                      <span aria-hidden="true"> · </span>
                      <span>{msg.envelopeId}</span>
                      <span aria-hidden="true"> · </span>
                      <span className="text-cyan-800">{msg.fromAgent}</span>
                      <span aria-hidden="true"> &rarr; </span>
                      <span>{msg.target}</span>
                      <span aria-hidden="true"> · </span>
                      <span>{msg.verb}</span>
                    </div>
                    <span
                      className={`font-semibold shrink-0 ${
                        msg.custodyStage === 'VERIFIED_EFFECT'
                          ? 'text-emerald-700'
                          : msg.custodyStage === 'LEASE_EXPIRED_RECOVERING'
                            ? 'text-amber-700'
                            : msg.custodyStage === 'LEASED' || msg.custodyStage === 'EXECUTING'
                              ? 'text-blue-700'
                              : 'text-slate-700'
                      }`}
                    >
                      {msg.custodyStage}
                      {msg.fencingToken ? ` · f_${msg.fencingToken}` : ''}
                    </span>
                  </div>

                  <p className="text-slate-800 text-xs leading-relaxed [overflow-wrap:anywhere]">
                    {msg.body}
                  </p>

                  <div className="flex flex-wrap items-center justify-between gap-2 pt-1">
                    <div className="text-[11px] font-mono text-slate-500 tabular-nums">
                      <span>Holder: {msg.holderAgentId ?? 'unclaimed'}</span>
                      {msg.verifierId && (
                        <>
                          <span aria-hidden="true"> · </span>
                          <span>Verifier: {msg.verifierId}</span>
                        </>
                      )}
                      {msg.recoveryCount > 0 && (
                        <>
                          <span aria-hidden="true"> · </span>
                          <span className="text-amber-700">Recovered {msg.recoveryCount}x</span>
                        </>
                      )}
                      <span aria-hidden="true"> · </span>
                      <span>sha256:{msg.envelopeSha256.slice(0, 10)}</span>
                    </div>

                    {msg.requiresClaim && msg.custodyStage !== 'VERIFIED_EFFECT' && (
                      <div className="flex flex-wrap items-center gap-1.5">
                        {(msg.custodyStage === 'DELIVERED' ||
                          msg.custodyStage === 'LEASE_EXPIRED_RECOVERING') && (
                          <button
                            type="button"
                            disabled={busy !== null}
                            onClick={() => void handleClaim(msg.envelopeId, claimCandidate)}
                            className="min-h-[30px] inline-flex items-center gap-1 rounded border border-slate-300 bg-white px-2.5 py-1 text-[11px] font-semibold text-slate-800 hover:bg-slate-50"
                          >
                            <Lock className="h-3 w-3" aria-hidden="true" />
                            Claim as {claimCandidate}
                          </button>
                        )}
                        {msg.holderAgentId && (
                          <button
                            type="button"
                            disabled={busy !== null}
                            onClick={() =>
                              void handleVerify(msg.envelopeId, 'karma-independent-verifier')
                            }
                            className="min-h-[30px] inline-flex items-center gap-1 rounded bg-emerald-700 px-2.5 py-1 text-[11px] font-semibold text-white hover:bg-emerald-800"
                          >
                            <ShieldCheck className="h-3 w-3" aria-hidden="true" />
                            Independent Verify (KARMA)
                          </button>
                        )}
                      </div>
                    )}
                  </div>
                </article>
              );
            })}
          </div>
        </section>
      </div>
    </div>
  );
}
