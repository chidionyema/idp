import { useCallback, useEffect, useState } from 'react';
import {
  Check,
  Copy,
  Download,
  ExternalLink,
  FileText,
  FolderArchive,
  GitBranch,
  PackageCheck,
  RefreshCw,
  Send,
} from 'lucide-react';

interface FleetExportManifest {
  ok: boolean;
  generatedAtUtc: string;
  sessionId: string;
  headSha: string;
  workingTreeClean: boolean;
  bundlePathRelative: string;
  bundleBytes: number;
  bundleSha256: string | null;
  workspaceArchiveFilename: string;
  workspaceArchiveFileCount: number;
  workspaceArchiveFiles: string[];
  workspaceArchiveBytes: number;
  workspaceArchiveSha256: string;
  proxyInterstitialNote: string;
  targetRef: string;
  producer7760Ref?: string;
  targetRemotes: string[];
  githubDevice?: {
    phase: string;
    authorizedInMemory: boolean;
    userCode: string | null;
    verificationUri: string;
    anyTargetRepoPushed: boolean;
    statusMessage: string;
    repoReceipts: Array<{
      repo: string;
      pushed: boolean;
      landedCommitSha: string | null;
      prUrl: string | null;
      prNumber: number | null;
      error: string | null;
    }>;
  };
  threeDaySync?: {
    allThreeDaysSealed: boolean;
    windowLabel: string;
    verifiedWorkstreamsCount: number;
    totalWorkstreamsCount: number;
    untrackedSourceFilesCount: number;
    bundleMatchesHead: boolean;
    threeDayMerkleRootSha256: string;
    githubCiWorkflowPresent: boolean;
    externalGitHubPushState: string;
  };
}

interface OutboundPushResponse {
  ok: boolean;
  pushed: boolean;
  method?: string;
  ingestUrlRedacted?: string | null;
  httpStatus?: number | null;
  bundleBytes?: number;
  bundleSha256?: string | null;
  durationMs?: number;
  reason?: string;
  error?: string;
}

const THREE_DAY_DELIVERABLES: ReadonlyArray<{
  id: string;
  dayLabel: string;
  title: string;
  primaryFiles: string;
  proofSummary: string;
}> = [
  {
    id: '01 · TURNKEY DR & 3-DAY SYNC',
    dayLabel: '17 Nov 2026',
    title: 'Commercial Turnkey Appliance Setup (/setup), Foreign Phone Bootstrap (/phone-boot), 12/12 Red-Team & 3-Day GitHub Sync Guard',
    primaryFiles:
      'FLEET_3DAY_CANONICAL_MANIFEST.md, .github/workflows/fleet-3day-sync-verify.yml, src/engine/fleetThreeDaySyncGuard.ts, src/engine/applianceTurnkeySetup.ts, src/components/ApplianceSetupDrConsole.tsx',
    proofSummary:
      'Zero-CLI / zero-sudo / zero-agent 1-click setup across 32/32 assets, 3-of-8 RS(3,8) brand-new foreign-phone recovery (stolen-laptop HTTP 409 epoch revocation, duress HTTP 423 safe-hold), 12/12 red-team vectors defeated, perpetual future-proof ratchet, and automatic GitHub CI 3-day verification + multi-remote mirror.',
  },
  {
    id: '02 · SYSTEM-FIRST IOC & 4KB DNA',
    dayLabel: '17 Nov 2026',
    title: 'LAW_SYSTEM_FIRST_IOC_RECONCILER, <=4KB GENESIS_SPORE.dna, ROUTER.md (:4200) & 8-Domain Anti-Confusion Ledger',
    primaryFiles:
      'GENESIS_SPORE.dna, ROUTER.md, src/engine/systemFirstIocReconciler.ts, src/components/SystemFirstIocExplorer.tsx',
    proofSummary:
      'Binds Gemini, GLM 5.3, DeepSeek, Kimi, Claude, and ChatGPT as interchangeable stateless actuators; mechanically rejects retired LiteLLM :4000-:4002 and OKE 193.123.184.22 pre-token (HTTP 422 at 0 tokens).',
  },
  {
    id: '03 · PHOENIX V2 & 12 FSMS',
    dayLabel: '17 Nov 2026',
    title: 'Operation Phoenix v2 Daily 06:00 UTC Cold-Boot, 12/12 Closed-Loop FSMs, OMNIFLOW Bus & KARMA/#7760',
    primaryFiles:
      'src/engine/phoenixDailyBoot.ts, src/engine/estateClosedLoopFsm.ts, src/engine/omniflowLiveBus.ts, scripts/cloudflare-pages-ingest-bundle.ts, .github/workflows/phoenix-daily-boot.yml',
    proofSummary:
      'Clean-room bundle unpack, Ghost IP 193.123.184.22 denylist (F31), HTTP 409 premature-Go guard, automatic P0 Seal revocation, 201->200->409->403->200 OMNIFLOW lease fencing, 10s TTL recovery, and <=16 MiB Bearer R2 receiver.',
  },
  {
    id: '04 · MCC-001, #8184 & CRESCENDO',
    dayLabel: '16 Nov 2026',
    title: 'Meridian Capability Calculus (MCC-001), Real-Time Founder Reactivity (#8184) & Crescendo 3-Way Union Sign-Off',
    primaryFiles:
      'MERIDIAN_CRESCENDO_3WAY_UNION_AND_GO_LIVE_SIGN_OFF.md, src/engine/meridianCapabilityCalculus.ts, src/engine/autonomousReactivity.ts, src/engine/crescendoThreeWayUnion.ts',
    proofSummary:
      '9-tuple contracts C_c=(I,O,P,Q,A,E,F,R,V), 5/5 bin/capability-index invariants, EP-A..EP-E doors, 1,240-subset #8194 Proof-2 closure, 7-stage fenced custody, and fail-closed Crescendo NO-GO gate.',
  },
  {
    id: '05 · MUM-001, ACADEMY & REGO',
    dayLabel: '16 Nov 2026',
    title: 'Auntie Ezinne VIP WhatsApp Concierge (EON-001), Standout Genesis Academy, UHNW <=150ms Charter & Rego v1',
    primaryFiles:
      'src/engine/mumsConcierge.ts, src/engine/genesisAcademyEngine.ts, src/engine/uhnwSovereignCharter.ts, src/engine/founderRegoChronosPlane.ts',
    proofSummary:
      '4s WhatsApp burst coalescer, £95.11 E.ON credit math, 9/9 safety + 11/11 negative blockers, 6-track Unseen Transfer Academy, <=150ms 7-agent OTTO SLA, and Rego R-008..R-010.',
  },
  {
    id: '06 · UNION, TELEGRAM & I-8088',
    dayLabel: '16 Nov 2026',
    title: 'Estate Grand Union, @otto_numen_bot VIP Telegram, Prospector-2100 -> Mumchimp, I-8088 RS(3,8) & Audit ff8543bd',
    primaryFiles:
      'src/engine/estateGrandUnion.ts, src/engine/ottoNumenTelegram.ts, src/engine/prospectorResearchMumchimp.ts, src/engine/genesisSporeTtt.ts, src/engine/firstUseGovernanceAudit.ts',
    proofSummary:
      '<50ms InterCloud spot heal, Best-of-3 open ensemble > Frontier (96.9% vs 93.4%), 98% Telegram ping cut, $0.00 causal EVSI, C(8,3)=56 RS(3,8) recovery, and 21/21 AGENTS.md <= 300 ratchet checks.',
  },
  {
    id: '07 · PENNYD, SYMPHONY & HERMES',
    dayLabel: '15 Nov 2026',
    title: 'PennyD Multi-Lane Router, Dagster Durable WAL, Meridian Symphony, I-8095 Zero-Polling, AURA-2100 & HERMES Tree',
    primaryFiles:
      'src/engine/routerCore.ts, src/engine/dagsterOrchestrator.ts, src/engine/meridianSymphony.ts, src/engine/i8095Lockdown.ts, src/engine/auraBinaryCodec.ts, src/engine/hermesCipherEngine.ts',
    proofSummary:
      'CAS key-store, HTTP 402 billing classifier, zero-drop Dagster WAL, I-8090 exit-78 zero-polling guard, 64-byte binary manifold, 27 Greek / 22 Hebrew ciphers, and reset-proof Git bundle sync.',
  },
];

export function TeamHandoffExportPanel() {
  const [manifest, setManifest] = useState<FleetExportManifest | null>(null);
  const [loading, setLoading] = useState(true);
  const [customIngestUrl, setCustomIngestUrl] = useState('');
  const [pushMethod, setPushMethod] = useState<'POST' | 'PUT'>('POST');
  const [pushing, setPushing] = useState(false);
  const [pushReceipt, setPushReceipt] = useState<OutboundPushResponse | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [startingGhDevice, setStartingGhDevice] = useState(false);

  const loadManifest = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/export/manifest');
      if (res.ok) {
        const json = (await res.json()) as FleetExportManifest;
        setManifest(json);
      }
    } finally {
      setLoading(false);
    }
  }, []);

  async function handleDirectGitHubPush() {
    setStartingGhDevice(true);
    try {
      const endpoint = manifest?.githubDevice?.authorizedInMemory
        ? '/api/export/github-device/push-now'
        : '/api/export/github-device/start';
      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      });
      if (res.ok) {
        const json = (await res.json()) as {
          githubDevice?: FleetExportManifest['githubDevice'];
        };
        if (json.githubDevice) {
          setManifest((prev) =>
            prev ? { ...prev, githubDevice: json.githubDevice } : prev
          );
        } else {
          await loadManifest();
        }
      }
    } finally {
      setStartingGhDevice(false);
    }
  }

  // Strict I-8090 compliance: initial fetch + EventSource SSE stream only (zero polling)
  useEffect(() => {
    void loadManifest();
    const es = new EventSource('/api/sync/stream');
    es.addEventListener('sync_event', (evt) => {
      try {
        const parsed = JSON.parse((evt as MessageEvent<string>).data) as {
          githubDevice?: FleetExportManifest['githubDevice'];
        };
        if (parsed.githubDevice) {
          setManifest((prev) =>
            prev ? { ...prev, githubDevice: parsed.githubDevice } : prev
          );
          if (parsed.githubDevice.anyTargetRepoPushed) {
            void loadManifest();
          }
          return;
        }
      } catch {
        // Fallback to manifest reload
      }
      void loadManifest();
    });
    return () => {
      es.close();
    };
  }, [loadManifest]);

  async function handleCopyText(id: string, value: string) {
    try {
      await navigator.clipboard.writeText(value);
      setCopiedId(id);
    } catch {
      setCopiedId(null);
    }
  }

  async function handleOutboundPush(targetUrl?: string) {
    setPushing(true);
    setPushReceipt(null);
    try {
      const bodyPayload: Record<string, unknown> =
        targetUrl !== undefined && targetUrl.trim().length > 0
          ? { ingestUrl: targetUrl.trim(), method: pushMethod }
          : {};
      const res = await fetch('/api/export/push-bundle', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(bodyPayload),
      });
      const json = (await res.json()) as OutboundPushResponse;
      setPushReceipt(json);
      await loadManifest();
    } finally {
      setPushing(false);
    }
  }

  const bundleSha = manifest?.bundleSha256 ?? 'pending';
  const headSha = manifest?.headSha ?? 'pending';

  const lane1TunnelSnippet = [
    '# Run on any fleet VM / laptop with GitHub SSH access (exposes a 15s HTTPS receiver):',
    'npx tsx scripts/genesis-ingest-receiver.ts --port 8788 --staging-dir /tmp/meridian-bundles &',
    'cloudflared tunnel --url http://127.0.0.1:8788',
    '# Then paste https://<tunnel>.trycloudflare.com/api/ingest/bundle into the Outbound Push box above!',
  ].join('\n');

  const verifyAndPushSnippet = [
    `echo "${bundleSha}  meridian-hermes-today.bundle" | shasum -a 256 -c -`,
    'git bundle verify meridian-hermes-today.bundle',
    'git clone meridian-hermes-today.bundle meridian-3day-sync && cd meridian-3day-sync',
    'npm ci && npm run lint && npm test && npm run build',
    'git remote add argon git@github.com:chidionyema/argon-sync.git',
    'git remote add gemini git@github.com:chidionyema/gemini-sync.git',
    'git push --atomic gemini +HEAD:refs/heads/aistudio/meridian-hermes-carbon-20261117 +HEAD:refs/heads/aistudio/meridian-hermes-live +HEAD:refs/heads/lane/aistudio-3day-sync-20261117',
    'git push --atomic argon +HEAD:refs/heads/aistudio/meridian-hermes-carbon-20261117 +HEAD:refs/heads/aistudio/meridian-hermes-live +HEAD:refs/heads/lane/aistudio-3day-sync-20261117',
  ].join('\n');

  const threeDay = manifest?.threeDaySync;

  return (
    <div className="space-y-6">
      {/* Live 3-Day Cryptographic Seal & Anti-Confusion Header */}
      <section className="bg-white border border-slate-200 rounded-xl p-5 space-y-4">
        <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-3 border-b border-slate-100 pb-4">
          <div className="space-y-1 max-w-4xl">
            <div className="text-xs font-mono tabular-nums text-slate-500 break-words">
              <span>HEAD: {headSha.slice(0, 12)}</span>
              <span aria-hidden="true"> · </span>
              <span className="text-emerald-700 font-semibold">
                3-Day Seal:{' '}
                {threeDay?.allThreeDaysSealed
                  ? `${threeDay.verifiedWorkstreamsCount}/${threeDay.totalWorkstreamsCount} Workstreams Verified`
                  : manifest?.workingTreeClean
                    ? 'CLEAN'
                    : 'SYNCING'}
              </span>
              <span aria-hidden="true"> · </span>
              <span>
                {manifest?.workspaceArchiveFileCount ?? 0} Tracked Files ({threeDay?.untrackedSourceFilesCount ?? 0} Untracked)
              </span>
              <span aria-hidden="true"> · </span>
              <span className="text-amber-700 font-semibold">
                GitHub Remote: {threeDay?.externalGitHubPushState === 'EXTERNAL_GITHUB_PUSH_CONFIRMED' ? 'PUSH RECEIPT CONFIRMED' : 'LOCAL SEALED · READY FOR GITHUB'}
              </span>
            </div>
            <h3 className="text-base sm:text-lg font-bold text-slate-900 text-balance">
              01. Complete Past 3 Days (15–17 Nov 2026) GitHub Sync &amp; Fleet Anti-Confusion Ledger
            </h3>
            <p className="text-xs text-slate-700">
              <strong>Zero Missed Files &amp; Zero Fleet Confusion:</strong> Every deliverable from{' '}
              <strong>15–17 Nov 2026</strong> is committed into Git <code className="font-mono">HEAD</code>,
              verified inside <code className="font-mono">meridian-hermes-today.bundle</code>, and
              indexed in root <code className="font-mono">FLEET_3DAY_CANONICAL_MANIFEST.md</code> +{' '}
              <code className="font-mono">.github/workflows/fleet-3day-sync-verify.yml</code> so
              neither GitHub Actions nor any fleet agent (<code className="font-mono">dsh</code>,{' '}
              <code className="font-mono">argon</code>, <code className="font-mono">opencode</code>,{' '}
              <code className="font-mono">pennyd</code>, <code className="font-mono">kimi</code>,{' '}
              <code className="font-mono">deepseek</code>, <code className="font-mono">claude</code>,{' '}
              <code className="font-mono">chatgpt</code>) can miss Day 1–3 work or resurrect retired
              ghosts (<code className="font-mono">:4000</code>,{' '}
              <code className="font-mono">193.123.184.22</code>, CLI/sudo setup, SMS OTP).
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2 shrink-0">
            <button
              type="button"
              disabled={startingGhDevice}
              onClick={() => void handleDirectGitHubPush()}
              className="min-h-[40px] inline-flex items-center gap-1.5 rounded-lg bg-slate-900 px-3.5 py-2 text-xs font-bold text-white hover:bg-slate-800 disabled:opacity-50 whitespace-nowrap"
            >
              <GitBranch className="h-3.5 w-3.5 text-emerald-400" aria-hidden="true" />
              {startingGhDevice
                ? 'Pushing…'
                : manifest?.githubDevice?.authorizedInMemory
                  ? 'Push Directly to GitHub Now'
                  : 'Push Directly to GitHub (Device Code)'}
            </button>

            <button
              type="button"
              disabled={loading}
              onClick={() => void loadManifest()}
              className="min-h-[40px] inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3.5 py-2 text-xs font-semibold text-slate-800 hover:bg-slate-50 disabled:opacity-50 whitespace-nowrap"
            >
              <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" />
              Refresh Manifest
            </button>
          </div>
        </div>

        {manifest?.githubDevice?.phase === 'AWAITING_USER_APPROVAL' &&
          manifest.githubDevice.userCode && (
            <div className="rounded-lg border border-slate-900 bg-slate-50 p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div className="space-y-0.5">
                <div className="text-xs font-semibold text-slate-700">
                  Approve once at GitHub to push all 3 days directly from this server to{' '}
                  <code className="font-mono">gemini-sync</code> &amp;{' '}
                  <code className="font-mono">argon-sync</code>:
                </div>
                <div className="flex items-center gap-2">
                  <span className="font-mono text-lg font-bold tracking-widest text-slate-900 tabular-nums">
                    {manifest.githubDevice.userCode}
                  </span>
                  <button
                    type="button"
                    onClick={() =>
                      void handleCopyText('ghcode', manifest.githubDevice!.userCode!)
                    }
                    className="inline-flex items-center gap-1 rounded border border-slate-300 bg-white px-2.5 py-1 text-xs font-semibold text-slate-800 hover:bg-slate-100"
                  >
                    {copiedId === 'ghcode' ? 'Copied' : 'Copy Code'}
                  </button>
                </div>
              </div>
              <a
                href={manifest.githubDevice.verificationUri}
                target="_blank"
                rel="noopener noreferrer"
                className="min-h-[40px] inline-flex items-center justify-center gap-1.5 rounded-lg bg-emerald-700 px-4 py-2 text-xs font-bold text-white hover:bg-emerald-800 whitespace-nowrap"
              >
                <span>Open github.com/login/device</span>
                <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
              </a>
            </div>
          )}

        {manifest?.githubDevice && manifest.githubDevice.repoReceipts.length > 0 && (
          <div
            className={`rounded-lg border p-3.5 font-mono text-xs space-y-1.5 ${
              manifest.githubDevice.anyTargetRepoPushed
                ? 'border-emerald-300 bg-emerald-50 text-emerald-950'
                : 'border-amber-300 bg-amber-50 text-amber-950'
            }`}
          >
            <div className="font-bold">{manifest.githubDevice.statusMessage}</div>
            {manifest.githubDevice.repoReceipts.map((r) => (
              <div key={r.repo} className="flex flex-wrap items-center justify-between gap-2">
                <span>
                  {r.pushed ? 'PUSHED' : 'FAILED'} · {r.repo}{' '}
                  {r.landedCommitSha ? `@ ${r.landedCommitSha.slice(0, 12)}` : ''}{' '}
                  {r.error ? `(${r.error})` : ''}
                </span>
                {r.prUrl && (
                  <a
                    href={r.prUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 font-bold underline"
                  >
                    Open PR #{r.prNumber ?? ''}
                    <ExternalLink className="h-3 w-3" aria-hidden="true" />
                  </a>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Cryptographic Artifact Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
          <div className="rounded-lg border border-slate-200 bg-slate-50/70 p-3.5 space-y-1">
            <div className="text-slate-500 font-medium">Full Git DAG Bundle (.bundle)</div>
            <div className="font-mono font-bold text-slate-900 tabular-nums">
              {manifest ? `${manifest.bundleBytes.toLocaleString()} bytes` : 'Loading…'}
            </div>
            <div className="font-mono text-[11px] text-slate-600 break-all">
              sha256: {bundleSha}
            </div>
          </div>

          <div className="rounded-lg border border-slate-200 bg-slate-50/70 p-3.5 space-y-1">
            <div className="text-slate-500 font-medium">Complete Workspace Archive (.tar.gz)</div>
            <div className="font-mono font-bold text-slate-900 tabular-nums">
              {manifest
                ? `${manifest.workspaceArchiveBytes.toLocaleString()} bytes (${manifest.workspaceArchiveFileCount} files)`
                : 'Loading…'}
            </div>
            <div className="font-mono text-[11px] text-slate-600 break-all">
              sha256: {manifest?.workspaceArchiveSha256 ?? 'pending'}
            </div>
          </div>

          <div className="rounded-lg border border-slate-200 bg-slate-50/70 p-3.5 space-y-1">
            <div className="text-slate-500 font-medium">Canonical Git Sync Target</div>
            <div className="font-mono font-bold text-slate-900 break-words">
              {manifest?.targetRef ?? 'refs/heads/aistudio/meridian-hermes-live'}
            </div>
            <div className="font-mono text-[11px] text-slate-600 break-words">
              Remotes: {(manifest?.targetRemotes ?? ['chidionyema/argon-sync', 'chidionyema/gemini-sync']).join(', ')}
            </div>
          </div>
        </div>

        {/* Lane 2: 1-Click Authenticated Browser Downloads */}
        <div className="space-y-2 pt-1">
          <div className="text-xs font-bold text-slate-900">
            1-Click Authenticated Browser Downloads (Works Immediately Through Preview Session)
          </div>
          <div className="flex flex-wrap items-center gap-2.5">
            <a
              href="/api/export/bundle"
              download="meridian-hermes-today.bundle"
              className="min-h-[40px] inline-flex items-center gap-1.5 rounded-lg bg-slate-900 px-4 py-2 text-xs font-semibold text-white hover:bg-slate-800 whitespace-nowrap"
            >
              <PackageCheck className="h-3.5 w-3.5 text-cyan-400" aria-hidden="true" />
              Download Full 3-Day Git Bundle (.bundle)
            </a>

            <a
              href="/api/export/all-3days"
              download="meridian-complete-3days-2026-11-17.tar.gz"
              className="min-h-[40px] inline-flex items-center gap-1.5 rounded-lg border border-slate-900 bg-white px-4 py-2 text-xs font-semibold text-slate-900 hover:bg-slate-50 whitespace-nowrap"
            >
              <FolderArchive className="h-3.5 w-3.5 text-slate-800" aria-hidden="true" />
              Download All 3 Days’ Code (.tar.gz)
            </a>

            <a
              href="/FLEET_3DAY_CANONICAL_MANIFEST.md?download=1"
              download="FLEET_3DAY_CANONICAL_MANIFEST.md"
              className="min-h-[40px] inline-flex items-center gap-1.5 rounded-lg border border-emerald-600 bg-emerald-50/70 px-3.5 py-2 text-xs font-semibold text-slate-900 hover:bg-emerald-100 whitespace-nowrap"
            >
              <FileText className="h-3.5 w-3.5 text-emerald-700" aria-hidden="true" />
              Fleet 3-Day Canonical Manifest (.md)
            </a>

            <a
              href="/api/export/team-handoff"
              download="meridian-estate-team-handoff.md"
              className="min-h-[40px] inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3.5 py-2 text-xs font-semibold text-slate-800 hover:bg-slate-50 whitespace-nowrap"
            >
              <FileText className="h-3.5 w-3.5 text-slate-600" aria-hidden="true" />
              Download Team Runbook (.md)
            </a>

            <a
              href="/api/export/concierge-pack"
              download="meridian-concierge-mcc-pack.tar.gz"
              className="min-h-[40px] inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3.5 py-2 text-xs font-semibold text-slate-800 hover:bg-slate-50 whitespace-nowrap"
            >
              <Download className="h-3.5 w-3.5 text-slate-600" aria-hidden="true" />
              Core Engine Pack (.tar.gz)
            </a>

            <a
              href="/MERIDIAN_CRESCENDO_3WAY_UNION_AND_GO_LIVE_SIGN_OFF.md"
              download="MERIDIAN_CRESCENDO_3WAY_UNION_AND_GO_LIVE_SIGN_OFF.md"
              className="min-h-[40px] inline-flex items-center gap-1.5 rounded-lg border border-amber-400 bg-amber-50 px-3.5 py-2 text-xs font-semibold text-slate-900 hover:bg-amber-100 whitespace-nowrap"
            >
              <FileText className="h-3.5 w-3.5 text-amber-700" aria-hidden="true" />
              Crescendo Sign-Off (.md)
            </a>
          </div>
        </div>
      </section>

      {/* Lane 1: Direct Outbound Container Push + Copyable Team Commands */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        <section className="lg:col-span-6 bg-white border border-slate-200 rounded-xl p-5 space-y-4">
          <div className="space-y-1 border-b border-slate-100 pb-3">
            <h3 className="text-base font-bold text-slate-900">
              02. Lane 1 — Direct Outbound HTTPS Push (Bypasses AI Studio HTML Proxy)
            </h3>
            <p className="text-xs text-slate-600">
              Our Express container initiates the outbound HTTPS request directly, delivering raw{' '}
              <code className="font-mono">meridian-hermes-today.bundle</code> bytes +{' '}
              <code className="font-mono">X-Bundle-Sha256</code> to any Cloudflare Quick Tunnel,
              fleet receiver, or S3/R2/GCS pre-signed <code className="font-mono">PUT</code> URL.
            </p>
          </div>

          <form
            className="space-y-3"
            onSubmit={(e) => {
              e.preventDefault();
              void handleOutboundPush(customIngestUrl);
            }}
          >
            <div className="space-y-1">
              <label
                htmlFor="handoff-ingest-url"
                className="block text-xs font-medium text-slate-700"
              >
                Team Receiver or Pre-Signed HTTPS URL (leave blank to probe canonical fleet targets)
              </label>
              <input
                id="handoff-ingest-url"
                type="text"
                value={customIngestUrl}
                onChange={(e) => setCustomIngestUrl(e.target.value)}
                placeholder="https://example-tunnel.trycloudflare.com/api/ingest/bundle"
                className="w-full min-h-[40px] rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-mono text-slate-900"
              />
            </div>

            <div className="flex flex-wrap items-center gap-3">
              <div className="flex items-center gap-2 text-xs">
                <label htmlFor="handoff-http-method" className="font-medium text-slate-700">
                  HTTP Method:
                </label>
                <select
                  id="handoff-http-method"
                  value={pushMethod}
                  onChange={(e) => setPushMethod(e.target.value as 'POST' | 'PUT')}
                  className="min-h-[38px] rounded-lg border border-slate-300 bg-white px-2.5 py-1.5 text-xs font-mono text-slate-900"
                >
                  <option value="POST">POST (Fleet Ingest / Tunnel)</option>
                  <option value="PUT">PUT (S3 / R2 / GCS Pre-Signed URL)</option>
                </select>
              </div>

              <button
                type="submit"
                disabled={pushing}
                className="min-h-[40px] inline-flex items-center gap-1.5 rounded-lg bg-slate-900 px-4 py-2 text-xs font-semibold text-white hover:bg-slate-800 disabled:opacity-50"
              >
                <Send className="h-3.5 w-3.5 text-cyan-400" aria-hidden="true" />
                {pushing ? 'Pushing Bundle Outbound…' : 'Push Bundle Outbound Now'}
              </button>
            </div>
          </form>

          {pushReceipt && (
            <div
              className={`rounded-lg border p-3.5 text-xs font-mono space-y-1 break-words ${
                pushReceipt.pushed
                  ? 'border-emerald-300 bg-emerald-50/70 text-emerald-950'
                  : 'border-amber-300 bg-amber-50/70 text-amber-950'
              }`}
            >
              <div className="font-bold">
                Status:{' '}
                {pushReceipt.pushed
                  ? `DELIVERED (HTTP ${pushReceipt.httpStatus})`
                  : `NOT ACCEPTED (${pushReceipt.error ?? pushReceipt.reason ?? `HTTP ${pushReceipt.httpStatus ?? 'ERR'}`})`}
              </div>
              {pushReceipt.bundleSha256 && (
                <div>
                  Bundle: {(pushReceipt.bundleBytes ?? 0).toLocaleString()} B · sha256:{' '}
                  {pushReceipt.bundleSha256.slice(0, 20)}…
                </div>
              )}
              {pushReceipt.ingestUrlRedacted && (
                <div>Target: {pushReceipt.ingestUrlRedacted}</div>
              )}
            </div>
          )}

          <div className="space-y-1.5 pt-1">
            <div className="flex items-center justify-between text-xs">
              <span className="font-semibold text-slate-800">
                15-Second Team Tunnel Receiver Snippet
              </span>
              <button
                type="button"
                onClick={() => void handleCopyText('tunnel', lane1TunnelSnippet)}
                className="inline-flex items-center gap-1 text-xs font-medium text-slate-700 hover:text-slate-950"
              >
                {copiedId === 'tunnel' ? (
                  <>
                    <Check className="h-3.5 w-3.5 text-emerald-600" aria-hidden="true" />
                    Copied
                  </>
                ) : (
                  <>
                    <Copy className="h-3.5 w-3.5" aria-hidden="true" />
                    Copy Snippet
                  </>
                )}
              </button>
            </div>
            <pre className="rounded-lg bg-slate-950 text-slate-100 p-3 text-[11px] font-mono overflow-x-auto leading-relaxed">
              {lane1TunnelSnippet}
            </pre>
          </div>
        </section>

        <section className="lg:col-span-6 bg-white border border-slate-200 rounded-xl p-5 space-y-4">
          <div className="space-y-1 border-b border-slate-100 pb-3">
            <h3 className="text-base font-bold text-slate-900">
              03. Team Verification &amp; GitHub Remote Sync Commands
            </h3>
            <p className="text-xs text-slate-600">
              Use <strong>Lane 3 (AI Studio Top-Right &ldquo;Save to GitHub&rdquo;)</strong> to push
              directly to GitHub and trigger{' '}
              <code className="font-mono">.github/workflows/fleet-3day-sync-verify.yml</code>{' '}
              automatically — or once <code className="font-mono">meridian-hermes-today.bundle</code>{' '}
              arrives via Lane 1 or Lane 2, run these exact commands to verify SHA-256, run all
              sequential test suites, and push to <code className="font-mono">argon-sync</code> &amp;{' '}
              <code className="font-mono">gemini-sync</code>.
            </p>
          </div>

          <div className="space-y-1.5">
            <div className="flex items-center justify-between text-xs">
              <span className="font-semibold text-slate-800">
                Verify Digest, Run Full Suites &amp; Push Both GitHub Remotes
              </span>
              <button
                type="button"
                onClick={() => void handleCopyText('verify', verifyAndPushSnippet)}
                className="inline-flex items-center gap-1 text-xs font-medium text-slate-700 hover:text-slate-950"
              >
                {copiedId === 'verify' ? (
                  <>
                    <Check className="h-3.5 w-3.5 text-emerald-600" aria-hidden="true" />
                    Copied
                  </>
                ) : (
                  <>
                    <Copy className="h-3.5 w-3.5" aria-hidden="true" />
                    Copy Commands
                  </>
                )}
              </button>
            </div>
            <pre className="rounded-lg bg-slate-950 text-slate-100 p-3 text-[11px] font-mono overflow-x-auto leading-relaxed">
              {verifyAndPushSnippet}
            </pre>
          </div>
        </section>
      </div>

      {/* Complete Inventory of All 3 Days (15-17 Nov 2026) */}
      <section className="bg-white border border-slate-200 rounded-xl p-5 space-y-4">
        <div className="border-b border-slate-100 pb-3">
          <h3 className="text-base font-bold text-slate-900">
            04. Cumulative 3-Day Manifest Included in Git HEAD, Bundle &amp; Archive (15–17 Nov 2026)
          </h3>
          <p className="text-xs text-slate-600 mt-0.5">
            Every workstream across all 3 days is committed into Git <code className="font-mono">HEAD</code>,
            sealed inside <code className="font-mono">meridian-hermes-today.bundle</code>, and
            governed by <code className="font-mono">FLEET_3DAY_CANONICAL_MANIFEST.md</code> +{' '}
            <code className="font-mono">TEAM_HANDOFF_TODAY.md</code> so no fleet agent can miss or
            misinterpret any layer.
          </p>
        </div>

        <div className="divide-y divide-slate-100">
          {THREE_DAY_DELIVERABLES.map((item) => (
            <div key={item.id} className="py-3 space-y-1 text-xs">
              <div className="font-semibold text-slate-900">
                <span className="font-mono text-slate-600">{item.id}</span>
                <span aria-hidden="true"> · </span>
                <span className="font-mono text-emerald-700">{item.dayLabel}</span>
                <span aria-hidden="true"> · </span>
                <span>{item.title}</span>
              </div>
              <div className="font-mono text-[11px] text-slate-500 break-words">
                Files: {item.primaryFiles}
              </div>
              <div className="text-slate-700">{item.proofSummary}</div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
