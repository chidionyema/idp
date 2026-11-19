import React, { useState, useEffect } from 'react';
import {
  GitBranch,
  RefreshCw,
  Download,
  ExternalLink,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Copy,
  Check,
  ArrowRight,
  KeyRound,
} from 'lucide-react';
import type { EstateStateSnapshot } from '../types/estate';
import { ARGON_DEFAULT_LANE_BRANCH, ARGON_TARGET_REPO } from '../engine/argonSync';

export interface ArgonSyncActionResult {
  ok: boolean;
  syncedRemote?: boolean;
  authority?: string;
  errorCode?: string;
  reason?: string;
  message: string;
  commitSha?: string | null;
  pullRequestUrl?: string | null;
}

interface ArgonSyncPanelProps {
  argonSync: EstateStateSnapshot['argonSync'];
  onTriggerSync: (branch?: string) => Promise<ArgonSyncActionResult>;
  onRefreshState: () => Promise<void>;
  variant?: 'compact' | 'full';
  onOpenFullConsole?: () => void;
}

export const ArgonSyncPanel: React.FC<ArgonSyncPanelProps> = ({
  argonSync,
  onTriggerSync,
  onRefreshState,
  variant = 'full',
  onOpenFullConsole,
}) => {
  const { readiness, manifest, lastRemoteReceipt, devCallbackUrl, sharedCallbackUrl } = argonSync;

  const [branchInput, setBranchInput] = useState<string>(
    manifest.governedBranch || ARGON_DEFAULT_LANE_BRANCH
  );
  const [isSyncing, setIsSyncing] = useState(false);
  const [syncOutcome, setSyncOutcome] = useState<ArgonSyncActionResult | null>(null);
  const [showOAuthSetup, setShowOAuthSetup] = useState(false);
  const [showManifestTable, setShowManifestTable] = useState(false);
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  // Listen for GitHub Popup OAuth completion (`oauth-integration` skill §1)
  useEffect(() => {
    const handleMessage = (event: MessageEvent) => {
      const origin = event.origin || '';
      if (!origin.endsWith('.run.app') && !origin.includes('localhost')) {
        return;
      }
      if (event.data?.type === 'OAUTH_AUTH_SUCCESS') {
        setShowOAuthSetup(false);
        setSyncOutcome({
          ok: true,
          message:
            'GitHub OAuth session verified. Triggering governed Greenlane sync to chidionyema/argon…',
        });
        void (async () => {
          await onRefreshState();
          const res = await onTriggerSync(branchInput);
          setSyncOutcome(res);
        })();
      }
    };
    window.addEventListener('message', handleMessage);
    return () => window.removeEventListener('message', handleMessage);
  }, [branchInput, onRefreshState, onTriggerSync]);

  const handleCopy = async (key: string, value: string) => {
    try {
      await navigator.clipboard.writeText(value);
      setCopiedKey(key);
      window.setTimeout(() => setCopiedKey(null), 1800);
    } catch {
      // Clipboard unavailable in restricted context
    }
  };

  const handleRunSync = async (overrideBranch?: string) => {
    const targetBranch = overrideBranch ?? branchInput;
    setIsSyncing(true);
    setSyncOutcome(null);
    try {
      const res = await onTriggerSync(targetBranch);
      setSyncOutcome(res);
    } finally {
      setIsSyncing(false);
    }
  };

  const handleConnectGithubOAuth = async () => {
    setSyncOutcome(null);
    try {
      const originParam = encodeURIComponent(window.location.origin);
      const res = await fetch(`/api/auth/github/url?origin=${originParam}`);
      if (!res.ok) {
        setShowOAuthSetup(true);
        return;
      }
      const data = (await res.json()) as {
        configured: boolean;
        url: string | null;
      };
      if (!data.configured || !data.url) {
        setShowOAuthSetup((prev) => !prev);
        return;
      }
      const popup = window.open(data.url, 'github_oauth_popup', 'width=620,height=720');
      if (!popup) {
        setSyncOutcome({
          ok: false,
          message:
            'Popup blocked by browser. Allow popups for this preview origin or use GITHUB_TOKEN / Greenlane Apply Script.',
        });
      }
    } catch {
      setShowOAuthSetup(true);
    }
  };

  if (variant === 'compact') {
    return (
      <section
        aria-label="Argon Continuity Synchronization Bar"
        className="bg-white dark:bg-[#0B101D] border border-slate-200 dark:border-slate-800 rounded-xl px-4 py-3.5 space-y-2.5"
      >
        <div className="flex flex-col xl:flex-row xl:items-center xl:justify-between gap-3">
          <div className="min-w-0 space-y-0.5">
            <div className="flex flex-wrap items-center gap-x-2.5 gap-y-1 text-xs font-mono tabular-nums">
              <span className="font-semibold text-slate-900 dark:text-slate-100">
                ARGON CONTINUITY SYNC
              </span>
              <span aria-hidden="true" className="text-slate-400">
                ·
              </span>
              <span className="text-cyan-700 dark:text-cyan-400">
                {ARGON_TARGET_REPO} → {manifest.governedBranch}
              </span>
              <span aria-hidden="true" className="text-slate-400">
                ·
              </span>
              <span className="text-slate-600 dark:text-slate-400">
                Merkle {manifest.merkleRootSha256.slice(0, 12)} ({manifest.fileCount} files · seq #{manifest.registerHeadSeq})
              </span>
              <span aria-hidden="true" className="text-slate-400">
                ·
              </span>
              <span
                className={
                  readiness.authority === 'E1'
                    ? 'text-emerald-600 dark:text-emerald-400 font-semibold'
                    : readiness.authority === 'E2'
                      ? 'text-cyan-600 dark:text-cyan-400 font-semibold'
                      : 'text-amber-600 dark:text-amber-400 font-semibold'
                }
              >
                Authority {readiness.authority}{' '}
                {readiness.syncState === 'SYNCED_REMOTE_E1'
                  ? '(Remote Commit Verified)'
                  : '(Staged Outbox Bundle)'}
              </span>
            </div>
            <p className="text-xs text-slate-600 dark:text-slate-400 truncate">
              {readiness.honestDetail}
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2 shrink-0">
            <a
              href="/api/argon/export.tar.gz"
              download="genesis-2100-complete-export.tar.gz"
              className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold text-slate-950 bg-amber-400 hover:bg-amber-300 rounded-lg transition-colors whitespace-nowrap shrink-0"
            >
              <Download className="w-3.5 h-3.5" aria-hidden="true" />
              Download Everything (.tar.gz)
            </a>

            <button
              type="button"
              onClick={() => handleRunSync(ARGON_DEFAULT_LANE_BRANCH)}
              disabled={isSyncing}
              className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-semibold text-slate-800 dark:text-slate-100 bg-slate-100 dark:bg-slate-900 hover:bg-slate-200 dark:hover:bg-slate-800 border border-slate-200 dark:border-slate-700 disabled:opacity-60 rounded-lg transition-colors whitespace-nowrap shrink-0"
            >
              <RefreshCw
                className={`w-3.5 h-3.5 text-cyan-600 dark:text-cyan-400 ${isSyncing ? 'animate-spin' : ''}`}
                aria-hidden="true"
              />
              {isSyncing ? 'Syncing to Argon…' : 'Sync to Argon'}
            </button>

            <a
              href="/api/argon/apply-lane.sh"
              download="apply-argon-lane.sh"
              className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-medium text-slate-700 dark:text-slate-200 bg-slate-100 dark:bg-slate-900 hover:bg-slate-200 dark:hover:bg-slate-800 border border-slate-200 dark:border-slate-800 rounded-lg transition-colors whitespace-nowrap shrink-0"
            >
              <Download className="w-3.5 h-3.5 text-cyan-600 dark:text-cyan-400" aria-hidden="true" />
              Greenlane Apply (.sh)
            </a>

            {onOpenFullConsole && (
              <button
                type="button"
                onClick={onOpenFullConsole}
                className="inline-flex items-center gap-1 px-3 py-2 text-xs font-medium text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white rounded-lg transition-colors whitespace-nowrap shrink-0"
              >
                <span>Argon Console</span>
                <ArrowRight className="w-3.5 h-3.5" aria-hidden="true" />
              </button>
            )}
          </div>
        </div>

        {syncOutcome && (
          <div
            role="status"
            className={`px-3 py-2 rounded-lg border text-xs font-mono flex items-center justify-between gap-3 ${
              syncOutcome.ok
                ? 'bg-emerald-50/70 dark:bg-emerald-950/25 border-emerald-200 dark:border-emerald-800/80 text-emerald-800 dark:text-emerald-300'
                : 'bg-rose-50/70 dark:bg-rose-950/30 border-rose-200 dark:border-rose-800 text-rose-800 dark:text-rose-300'
            }`}
          >
            <span>{syncOutcome.message}</span>
            {syncOutcome.pullRequestUrl && (
              <a
                href={syncOutcome.pullRequestUrl}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1 underline shrink-0"
              >
                <span>Open PR</span>
                <ExternalLink className="w-3 h-3" />
              </a>
            )}
          </div>
        )}
      </section>
    );
  }

  return (
    <section
      aria-labelledby="argon-sync-console-heading"
      className="bg-white dark:bg-[#0B101D] border border-slate-200 dark:border-slate-800 rounded-xl p-5 space-y-5"
    >
      <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-4 pb-4 border-b border-slate-200 dark:border-slate-800">
        <div className="space-y-1">
          <div className="flex flex-wrap items-center gap-2 text-xs font-mono text-amber-600 dark:text-amber-400">
            <span>00. ARGON CONTINUITY &amp; GREENLANE SYNC ENGINE</span>
            <span aria-hidden="true">·</span>
            <span>SCHEMA {manifest.schema}</span>
          </div>
          <h2
            id="argon-sync-console-heading"
            className="text-lg font-semibold text-slate-900 dark:text-slate-50"
          >
            Synchronize Full Workspace, Register WAL &amp; Optimus Proofs to{' '}
            <code className="font-mono text-cyan-700 dark:text-cyan-400">{ARGON_TARGET_REPO}</code>
          </h2>
          <p className="text-xs text-slate-600 dark:text-slate-400 max-w-3xl leading-relaxed">
            Computes deterministic SHA-256 digests across all Genesis 2100 source modules,{' '}
            <code className="font-mono">.ops/register.jsonl</code>,{' '}
            <code className="font-mono">.ops/evidence/*.json</code>, and{' '}
            <code className="font-mono">.genesis/outbox/</code>. Enforces Greenlane law: direct{' '}
            <code className="font-mono">main</code> pushes fail closed; remote commits promote to{' '}
            <code className="font-mono">E1</code> only when GitHub returns a verified 40-char commit SHA.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2 shrink-0">
          <a
            href="/api/argon/export.tar.gz"
            download="genesis-2100-complete-export.tar.gz"
            className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-semibold text-slate-950 bg-amber-400 hover:bg-amber-300 rounded-lg transition-colors whitespace-nowrap shrink-0"
          >
            <Download className="w-3.5 h-3.5" aria-hidden="true" />
            Download Everything (.tar.gz)
          </a>

          <button
            type="button"
            onClick={() => handleRunSync()}
            disabled={isSyncing}
            className="inline-flex items-center gap-2 px-3.5 py-2 text-xs font-semibold text-slate-900 dark:text-slate-100 bg-slate-100 dark:bg-slate-900 hover:bg-slate-200 dark:hover:bg-slate-800 border border-slate-300 dark:border-slate-700 disabled:opacity-60 rounded-lg transition-colors whitespace-nowrap shrink-0"
          >
            <RefreshCw
              className={`w-3.5 h-3.5 text-cyan-600 dark:text-cyan-400 ${isSyncing ? 'animate-spin' : ''}`}
              aria-hidden="true"
            />
            {isSyncing ? 'Synchronizing Lane…' : 'Sync Everything to Argon'}
          </button>

          <button
            type="button"
            onClick={handleConnectGithubOAuth}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-medium text-slate-700 dark:text-slate-200 bg-slate-100 dark:bg-slate-900 hover:bg-slate-200 dark:hover:bg-slate-800 border border-slate-200 dark:border-slate-800 rounded-lg transition-colors whitespace-nowrap shrink-0"
          >
            <KeyRound className="w-3.5 h-3.5 text-cyan-600 dark:text-cyan-400" aria-hidden="true" />
            {readiness.authMode === 'GITHUB_OAUTH_POPUP'
              ? 'Reconnect GitHub OAuth'
              : 'Connect GitHub OAuth'}
          </button>
        </div>
      </div>

      {/* 4 Crisp Tabular KPI Readouts */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-3.5 font-mono tabular-nums">
        <div className="p-3.5 rounded-lg bg-slate-50 dark:bg-[#070B14] border border-slate-200 dark:border-slate-800/90 space-y-1">
          <div className="text-[11px] text-slate-500 dark:text-slate-400">GOVERNED TARGET</div>
          <div className="text-xs font-semibold text-slate-900 dark:text-slate-100 truncate">
            {ARGON_TARGET_REPO}
          </div>
          <div className="text-[11px] text-cyan-700 dark:text-cyan-400 truncate">
            {manifest.governedBranch}
          </div>
        </div>

        <div className="p-3.5 rounded-lg bg-slate-50 dark:bg-[#070B14] border border-slate-200 dark:border-slate-800/90 space-y-1">
          <div className="text-[11px] text-slate-500 dark:text-slate-400">MERKLE ROOT SHA-256</div>
          <div className="text-xs font-semibold text-slate-900 dark:text-slate-100 truncate">
            {manifest.merkleRootSha256.slice(0, 20)}…
          </div>
          <div className="text-[11px] text-slate-500 dark:text-slate-400">
            {manifest.fileCount} files · {(manifest.totalBytes / 1024).toFixed(1)} KB verified
          </div>
        </div>

        <div className="p-3.5 rounded-lg bg-slate-50 dark:bg-[#070B14] border border-slate-200 dark:border-slate-800/90 space-y-1">
          <div className="text-[11px] text-slate-500 dark:text-slate-400">REGISTER &amp; OUTBOX CURSOR</div>
          <div className="text-xs font-semibold text-slate-900 dark:text-slate-100">
            seq #{manifest.registerHeadSeq} ({manifest.registerEntryCount} entries)
          </div>
          <div className="text-[11px] text-slate-500 dark:text-slate-400 truncate">
            {manifest.outboxEnvelope.instruction_id}
          </div>
        </div>

        <div className="p-3.5 rounded-lg bg-slate-50 dark:bg-[#070B14] border border-slate-200 dark:border-slate-800/90 space-y-1">
          <div className="text-[11px] text-slate-500 dark:text-slate-400">EPISTEMIC SYNC STATE</div>
          <div
            className={`text-xs font-semibold flex items-center gap-1.5 ${
              readiness.authority === 'E1'
                ? 'text-emerald-700 dark:text-emerald-400'
                : readiness.authority === 'E2'
                  ? 'text-cyan-700 dark:text-cyan-400'
                  : 'text-amber-700 dark:text-amber-400'
            }`}
          >
            {readiness.authority === 'E1' ? (
              <CheckCircle2 className="w-3.5 h-3.5 shrink-0" />
            ) : (
              <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
            )}
            <span className="truncate">
              Authority {readiness.authority} ·{' '}
              {readiness.syncState === 'SYNCED_REMOTE_E1'
                ? 'SYNCED_REMOTE'
                : readiness.syncState === 'DRIFT_STAGED_LOCAL'
                  ? 'DELTA_STAGED'
                  : 'STAGED_OUTBOX'}
            </span>
          </div>
          <div className="text-[11px] text-slate-500 dark:text-slate-400 truncate">
            {lastRemoteReceipt
              ? `Commit ${lastRemoteReceipt.commitSha.slice(0, 12)}`
              : `Auth: ${readiness.authMode}`}
          </div>
        </div>
      </div>

      {/* Governed Branch Input + Negative Main-Push Guard Test + Portable Bundle Downloads */}
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-4 items-end pt-1">
        <div className="xl:col-span-6 space-y-1.5">
          <div className="flex items-center justify-between gap-2">
            <label
              htmlFor="argon-governed-branch-input"
              className="text-xs font-medium text-slate-700 dark:text-slate-300 flex items-center gap-1.5"
            >
              <GitBranch className="w-3.5 h-3.5 text-cyan-600 dark:text-cyan-400" aria-hidden="true" />
              <span>
                Governed Argon Branch (<code className="font-mono">lane/*</code> or{' '}
                <code className="font-mono">propose/aistudio-*</code>)
              </span>
            </label>
            <div className="flex items-center gap-1.5">
              <button
                type="button"
                onClick={() => {
                  setBranchInput('main');
                  void handleRunSync('main');
                }}
                className="px-2 py-0.5 text-[11px] font-mono text-rose-700 dark:text-rose-300 bg-rose-50 dark:bg-rose-950/40 hover:bg-rose-100 dark:hover:bg-rose-900/50 border border-rose-200 dark:border-rose-800/70 rounded transition-colors whitespace-nowrap"
              >
                Test main Refusal
              </button>
              <button
                type="button"
                onClick={() => {
                  setBranchInput(ARGON_DEFAULT_LANE_BRANCH);
                  setSyncOutcome(null);
                }}
                className="px-2 py-0.5 text-[11px] font-mono text-slate-600 dark:text-slate-300 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 rounded transition-colors whitespace-nowrap"
              >
                Reset Default Lane
              </button>
            </div>
          </div>
          <input
            id="argon-governed-branch-input"
            type="text"
            value={branchInput}
            onChange={(e) => setBranchInput(e.target.value)}
            className="w-full px-3 py-2 text-xs font-mono bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-lg text-slate-900 dark:text-slate-100"
          />
        </div>

        <div className="xl:col-span-6 flex flex-wrap items-center xl:justify-end gap-2">
          <a
            href="/api/argon/apply-lane.sh"
            download="apply-argon-lane.sh"
            className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold text-slate-900 dark:text-slate-100 bg-slate-100 dark:bg-slate-900 hover:bg-slate-200 dark:hover:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-lg transition-colors whitespace-nowrap shrink-0"
          >
            <Download className="w-3.5 h-3.5 text-cyan-600 dark:text-cyan-400" aria-hidden="true" />
            Download Greenlane Apply Script (.sh)
          </a>

          <a
            href="/api/argon/bundle.json"
            download="argon-sync-bundle-20261111.json"
            className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-medium text-slate-700 dark:text-slate-300 bg-white dark:bg-slate-950 hover:bg-slate-50 dark:hover:bg-slate-900 border border-slate-300 dark:border-slate-800 rounded-lg transition-colors whitespace-nowrap shrink-0"
          >
            <Download className="w-3.5 h-3.5 text-amber-600 dark:text-amber-400" aria-hidden="true" />
            Download Signed Bundle (.json)
          </a>

          <button
            type="button"
            onClick={() => setShowManifestTable((v) => !v)}
            className="px-3 py-2 text-xs font-medium text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100 rounded-lg transition-colors whitespace-nowrap"
          >
            {showManifestTable ? 'Hide File Digests' : `Inspect ${manifest.fileCount} File Digests`}
          </button>
        </div>
      </div>

      {/* Honest Epistemic Status Note */}
      <div className="p-3.5 rounded-lg bg-slate-50 dark:bg-[#070B14] border border-slate-200 dark:border-slate-800 text-xs text-slate-700 dark:text-slate-300 leading-relaxed">
        <span className="font-mono font-semibold text-slate-900 dark:text-slate-100 mr-2">
          STATUS:
        </span>
        {readiness.honestDetail}
      </div>

      {/* Live Action Feedback Banner */}
      {syncOutcome && (
        <div
          role="alert"
          className={`p-3.5 rounded-lg border text-xs flex items-start justify-between gap-3 ${
            syncOutcome.ok
              ? 'bg-emerald-50/70 dark:bg-emerald-950/30 border-emerald-200 dark:border-emerald-800 text-emerald-800 dark:text-emerald-300'
              : 'bg-rose-50/70 dark:bg-rose-950/30 border-rose-200 dark:border-rose-800 text-rose-800 dark:text-rose-300'
          }`}
        >
          <div className="flex items-start gap-2">
            {syncOutcome.ok ? (
              <CheckCircle2 className="w-4 h-4 shrink-0 mt-0.5" />
            ) : (
              <XCircle className="w-4 h-4 shrink-0 mt-0.5" />
            )}
            <span className="font-mono">{syncOutcome.message}</span>
          </div>
          {syncOutcome.pullRequestUrl && (
            <a
              href={syncOutcome.pullRequestUrl}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1 font-mono underline shrink-0"
            >
              <span>View Argon PR</span>
              <ExternalLink className="w-3.5 h-3.5" />
            </a>
          )}
        </div>
      )}

      {/* GitHub OAuth Callback & Server Secret Configuration Disclosure (Zero Raw Secret Inputs!) */}
      {showOAuthSetup && (
        <div className="p-4 rounded-xl bg-slate-50 dark:bg-[#070B14] border border-cyan-300/70 dark:border-cyan-800/70 space-y-3 text-xs">
          <div className="flex items-center justify-between gap-2">
            <div className="font-semibold text-slate-900 dark:text-slate-100">
              GitHub Authorization Setup for Direct Cloud Push to <code className="font-mono">chidionyema/argon</code>
            </div>
            <button
              type="button"
              onClick={() => setShowOAuthSetup(false)}
              className="text-slate-500 hover:text-slate-900 dark:hover:text-slate-100 font-mono"
            >
              Close
            </button>
          </div>
          <p className="text-slate-600 dark:text-slate-400">
            Configure either <code className="font-mono">GITHUB_TOKEN</code> (fine-grained token with Contents &amp; Pull Requests access on <code className="font-mono">chidionyema/argon</code>) OR GitHub OAuth App credentials (<code className="font-mono">CLIENT_ID</code> and <code className="font-mono">CLIENT_SECRET</code>) in the AI Studio Secrets panel using these exact callback URLs:
          </p>
          <div className="space-y-2 font-mono">
            <div className="flex flex-wrap items-center justify-between gap-2 p-2.5 bg-white dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-lg">
              <div className="truncate">
                <span className="text-slate-500 mr-2">Dev Callback:</span>
                <span className="text-cyan-700 dark:text-cyan-300">{devCallbackUrl}</span>
              </div>
              <button
                type="button"
                onClick={() => handleCopy('dev', devCallbackUrl)}
                className="inline-flex items-center gap-1 px-2 py-1 text-[11px] bg-slate-100 dark:bg-slate-800 rounded shrink-0"
              >
                {copiedKey === 'dev' ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
                <span>{copiedKey === 'dev' ? 'Copied' : 'Copy'}</span>
              </button>
            </div>
            <div className="flex flex-wrap items-center justify-between gap-2 p-2.5 bg-white dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-lg">
              <div className="truncate">
                <span className="text-slate-500 mr-2">Shared Callback:</span>
                <span className="text-cyan-700 dark:text-cyan-300">{sharedCallbackUrl}</span>
              </div>
              <button
                type="button"
                onClick={() => handleCopy('shared', sharedCallbackUrl)}
                className="inline-flex items-center gap-1 px-2 py-1 text-[11px] bg-slate-100 dark:bg-slate-800 rounded shrink-0"
              >
                {copiedKey === 'shared' ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
                <span>{copiedKey === 'shared' ? 'Copied' : 'Copy'}</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Expandable SHA-256 File Mapping Table */}
      {showManifestTable && (
        <div className="border border-slate-200 dark:border-slate-800 rounded-lg overflow-hidden">
          <div className="max-h-64 overflow-y-auto">
            <table className="w-full text-left border-collapse text-xs font-mono tabular-nums">
              <thead>
                <tr className="bg-slate-50 dark:bg-slate-900/80 border-b border-slate-200 dark:border-slate-800 text-slate-500 dark:text-slate-400">
                  <th className="py-2 px-3">Argon Repository Path</th>
                  <th className="py-2 px-3">Category</th>
                  <th className="py-2 px-3 text-right">Bytes</th>
                  <th className="py-2 px-3">SHA-256 Digest</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
                {manifest.files.map((file) => (
                  <tr key={file.argonRepoPath} className="hover:bg-slate-50/70 dark:hover:bg-slate-800/40">
                    <td className="py-2 px-3 text-slate-900 dark:text-slate-100">{file.argonRepoPath}</td>
                    <td className="py-2 px-3 text-slate-500 dark:text-slate-400">{file.category}</td>
                    <td className="py-2 px-3 text-right text-slate-600 dark:text-slate-300">{file.bytes}</td>
                    <td className="py-2 px-3 text-cyan-700 dark:text-cyan-400">
                      {file.sha256.slice(0, 16)}…
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </section>
  );
};
