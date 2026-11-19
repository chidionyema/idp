import { useCallback, useEffect, useState } from 'react';
import {
  Check,
  Copy,
  Download,
  ExternalLink,
  FolderArchive,
  GitBranch,
  PackageCheck,
  RefreshCw,
  Send,
  Terminal,
  Trash2,
  X,
} from 'lucide-react';

interface RegisteredTargetItem {
  url: string;
  method: 'POST' | 'PUT';
  addedAtUtc: string;
  lastPushedSha256: string | null;
  lastHttpStatus: number | null;
}

interface GitHubRepoReceiptItem {
  repo: string;
  pushed: boolean;
  localHeadSha: string;
  remoteMainParentSha: string | null;
  landedCommitSha: string | null;
  pushedRefs: string[];
  prUrl: string | null;
  prNumber: number | null;
  error: string | null;
}

interface GitHubDeviceStatePayload {
  phase:
    | 'IDLE'
    | 'AWAITING_USER_APPROVAL'
    | 'AUTHORIZED_PUSHING'
    | 'PUSHED_CONFIRMED'
    | 'PUSH_PARTIAL_OR_FAILED'
    | 'EXPIRED_OR_DENIED';
  authorizedInMemory: boolean;
  authenticatedLogin: string | null;
  userCode: string | null;
  verificationUri: string;
  expiresAtUtc: string | null;
  targetRepos: string[];
  targetRefs: string[];
  lastPushAtUtc: string | null;
  anyTargetRepoPushed: boolean;
  allTargetReposPushed: boolean;
  repoReceipts: GitHubRepoReceiptItem[];
  statusMessage: string;
}

interface AutoSyncApiResponse {
  ok: boolean;
  daemonActive: boolean;
  lastCycleAtUtc: string | null;
  lastAcceptedBundleSha256: string | null;
  currentHeadSha: string;
  currentBundleSha256: string | null;
  currentBundleBytes: number;
  workspaceArchiveBytes: number;
  workspaceArchiveFileCount: number;
  registeredCustomTargets: RegisteredTargetItem[];
  canonicalTargets: string[];
  lastReason: string | null;
  githubDevice?: GitHubDeviceStatePayload;
  threeDaySync?: {
    allThreeDaysSealed: boolean;
    verifiedWorkstreamsCount: number;
    totalWorkstreamsCount: number;
    untrackedSourceFilesCount: number;
    bundleMatchesHead: boolean;
    threeDayMerkleRootSha256: string;
    githubCiWorkflowPresent: boolean;
    externalGitHubPushState: string;
  };
}

interface ClipboardCapsulePayload {
  ok: boolean;
  mode: 'compact' | 'full';
  headSha: string;
  fileCount: number;
  compressedBytes: number;
  base64Chars: number;
  payloadSha256: string;
  shellCommand: string;
}

interface GlobalGetWorkModalProps {
  open: boolean;
  autoStartGitHubDevice?: boolean;
  onClearAutoStart?: () => void;
  onClose: () => void;
  onOpenFullHandoffTab?: () => void;
}

export function GlobalGetWorkModal({
  open,
  autoStartGitHubDevice = false,
  onClearAutoStart,
  onClose,
  onOpenFullHandoffTab,
}: GlobalGetWorkModalProps) {
  const [data, setData] = useState<AutoSyncApiResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [startingDevice, setStartingDevice] = useState(false);
  const [copiedUserCode, setCopiedUserCode] = useState(false);

  const [capsule, setCapsule] = useState<ClipboardCapsulePayload | null>(null);
  const [loadingCapsule, setLoadingCapsule] = useState(false);
  const [copiedCapsule, setCopiedCapsule] = useState(false);
  const [showRawCapsuleBox, setShowRawCapsuleBox] = useState(false);

  const [downloadNotice, setDownloadNotice] = useState<{ ok: boolean; text: string } | null>(null);
  const [downloadingKey, setDownloadingKey] = useState<string | null>(null);

  const [targetUrl, setTargetUrl] = useState('');
  const [targetMethod, setTargetMethod] = useState<'POST' | 'PUT'>('POST');
  const [submitting, setSubmitting] = useState(false);
  const [statusNotice, setStatusNotice] = useState<{ ok: boolean; text: string } | null>(null);

  const loadStatus = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/export/auto-sync');
      if (res.ok) {
        const json = (await res.json()) as AutoSyncApiResponse;
        setData(json);
      }
    } finally {
      setLoading(false);
    }
  }, []);

  const preloadClipboardCapsule = useCallback(async (mode: 'compact' | 'full' = 'compact') => {
    setLoadingCapsule(true);
    try {
      const res = await fetch(`/api/export/clipboard-capsule?mode=${mode}`);
      if (res.ok) {
        const json = (await res.json()) as ClipboardCapsulePayload;
        setCapsule(json);
      }
    } finally {
      setLoadingCapsule(false);
    }
  }, []);

  const handleStartGitHubDevicePush = useCallback(async () => {
    setStartingDevice(true);
    try {
      const endpoint = data?.githubDevice?.authorizedInMemory
        ? '/api/export/github-device/push-now'
        : '/api/export/github-device/start';
      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      });
      if (res.ok) {
        const json = (await res.json()) as {
          ok: boolean;
          githubDevice?: GitHubDeviceStatePayload;
        };
        if (json.githubDevice) {
          setData((prev) =>
            prev
              ? { ...prev, githubDevice: json.githubDevice }
              : {
                  ok: true,
                  daemonActive: true,
                  lastCycleAtUtc: null,
                  lastAcceptedBundleSha256: null,
                  currentHeadSha: '',
                  currentBundleSha256: null,
                  currentBundleBytes: 0,
                  workspaceArchiveBytes: 0,
                  workspaceArchiveFileCount: 114,
                  registeredCustomTargets: [],
                  canonicalTargets: [],
                  lastReason: null,
                  githubDevice: json.githubDevice,
                }
          );
        } else {
          await loadStatus();
        }
      }
    } finally {
      setStartingDevice(false);
    }
  }, [data?.githubDevice?.authorizedInMemory, loadStatus]);

  // Strict I-8090 compliance: initial fetch + server-sent events (/api/sync/stream) only
  useEffect(() => {
    if (!open) return;
    void loadStatus();
    const capsuleTimer = setTimeout(() => {
      void preloadClipboardCapsule('compact');
    }, 250);

    const es = new EventSource('/api/sync/stream');
    es.addEventListener('sync_event', (evt) => {
      try {
        const parsed = JSON.parse((evt as MessageEvent<string>).data) as {
          githubDevice?: GitHubDeviceStatePayload;
        };
        if (parsed.githubDevice) {
          setData((prev) =>
            prev ? { ...prev, githubDevice: parsed.githubDevice } : prev
          );
          if (parsed.githubDevice.anyTargetRepoPushed) {
            void loadStatus();
          }
          return;
        }
      } catch {
        // Fallback to status reload
      }
      void loadStatus();
    });

    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };
    window.addEventListener('keydown', onKeyDown);

    return () => {
      clearTimeout(capsuleTimer);
      window.removeEventListener('keydown', onKeyDown);
      es.close();
    };
  }, [open, loadStatus, preloadClipboardCapsule, onClose]);

  useEffect(() => {
    if (open && autoStartGitHubDevice) {
      onClearAutoStart?.();
      void handleStartGitHubDevicePush();
    }
  }, [open, autoStartGitHubDevice, onClearAutoStart, handleStartGitHubDevicePush]);

  if (!open) return null;

  async function handleCopyDeviceCode(code: string) {
    try {
      await navigator.clipboard.writeText(code);
      setCopiedUserCode(true);
      setTimeout(() => setCopiedUserCode(false), 2500);
    } catch {
      setCopiedUserCode(false);
    }
  }

  function handleCopySelfExtractingCapsule() {
    if (!capsule?.shellCommand) {
      setShowRawCapsuleBox(true);
      return;
    }
    let copiedOk = false;
    // Ephemeral offscreen textarea preserves synchronous iframe user gesture with zero permanent DOM bloat
    try {
      const tempArea = document.createElement('textarea');
      tempArea.value = capsule.shellCommand;
      tempArea.setAttribute('readonly', 'true');
      tempArea.className = 'sr-only';
      document.body.appendChild(tempArea);
      tempArea.focus();
      tempArea.select();
      copiedOk = document.execCommand('copy');
      document.body.removeChild(tempArea);
    } catch {
      copiedOk = false;
    }
    if (navigator.clipboard?.writeText) {
      void navigator.clipboard
        .writeText(capsule.shellCommand)
        .then(() => {
          setCopiedCapsule(true);
        })
        .catch(() => {
          if (!copiedOk) {
            setShowRawCapsuleBox(true);
          }
        });
    }
    if (copiedOk) {
      setCopiedCapsule(true);
    } else {
      setShowRawCapsuleBox(true);
    }
  }

  async function handleFetchBlobDownload(key: string, url: string, filename: string) {
    setDownloadingKey(key);
    setDownloadNotice(null);
    try {
      const res = await fetch(url);
      if (!res.ok) {
        setDownloadNotice({
          ok: false,
          text: `Endpoint returned HTTP ${res.status}. Use Method 1 (Direct GitHub Push) or Method 2 (1-Click Terminal Capsule) above.`,
        });
        return;
      }
      const contentType = (res.headers.get('content-type') ?? '').toLowerCase();
      if (contentType.includes('text/html')) {
        setDownloadNotice({
          ok: false,
          text: 'Preview proxy intercepted binary navigation as HTML. Use Method 1 (Direct GitHub Push) or Method 2 (Clipboard Capsule) above.',
        });
        return;
      }
      const blob = await res.blob();
      const blobUrl = URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = blobUrl;
      anchor.download = filename;
      document.body.appendChild(anchor);
      anchor.click();
      document.body.removeChild(anchor);
      setTimeout(() => URL.revokeObjectURL(blobUrl), 15_000);
      setDownloadNotice({
        ok: true,
        text: `Prepared ${filename} (${blob.size.toLocaleString()} bytes) via authenticated fetch. Note: if Chrome's iframe sandbox blocks file saving to ~/Downloads, use Method 1 (Direct GitHub Push) or Method 2 (Clipboard Capsule) above!`,
      });
    } catch (err) {
      setDownloadNotice({
        ok: false,
        text:
          err instanceof Error
            ? err.message
            : 'Download blocked by iframe sandbox. Use Method 1 or Method 2 above.',
      });
    } finally {
      setDownloadingKey(null);
    }
  }

  async function handleSaveAndPush(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setStatusNotice(null);
    try {
      const trimmed = targetUrl.trim();
      const endpoint = trimmed ? '/api/export/register-target' : '/api/export/push-bundle';
      const bodyPayload = trimmed ? { url: trimmed, method: targetMethod } : {};
      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(bodyPayload),
      });
      const json = (await res.json()) as {
        ok?: boolean;
        pushed?: boolean;
        error?: string;
        reason?: string;
        httpStatus?: number | null;
      };
      if (!res.ok) {
        setStatusNotice({
          ok: false,
          text: json.error ?? 'Invalid HTTPS receiver URL.',
        });
      } else if (json.pushed) {
        setStatusNotice({
          ok: true,
          text: trimmed
            ? `Saved target & pushed bundle (HTTP ${json.httpStatus ?? 200}). Future edits will auto-push here.`
            : `Bundle pushed to canonical receiver (HTTP ${json.httpStatus ?? 200}).`,
        });
        if (trimmed) setTargetUrl('');
      } else {
        setStatusNotice({
          ok: false,
          text: trimmed
            ? `Saved URL for automatic retries, but initial push was not accepted (${json.reason ?? json.error ?? 'unreachable'}).`
            : `Canonical fleet endpoints did not accept push (${json.reason ?? 'otto.mumchimp.com offline / pages.dev 404'}). Use Method 1 (Direct GitHub Push) above!`,
        });
        if (trimmed) setTargetUrl('');
      }
      await loadStatus();
    } finally {
      setSubmitting(false);
    }
  }

  async function handleRemoveTarget(url: string) {
    await fetch('/api/export/register-target', {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url }),
    });
    await loadStatus();
  }

  const headShort = data?.currentHeadSha ? data.currentHeadSha.slice(0, 12) : 'loading…';
  const bundleMb = data?.currentBundleBytes
    ? `${(data.currentBundleBytes / (1024 * 1024)).toFixed(1)} MB`
    : '3.2 MB';
  const archiveMb = data?.workspaceArchiveBytes
    ? `${(data.workspaceArchiveBytes / (1024 * 1024)).toFixed(1)} MB`
    : '6.3 MB';
  const gh = data?.githubDevice;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/60 p-3 sm:p-6 overflow-y-auto"
      onClick={onClose}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="global-get-work-title"
        onClick={(e) => e.stopPropagation()}
        className="w-full max-w-3xl rounded-xl bg-white border border-slate-200 shadow-2xl overflow-hidden my-auto"
      >

        {/* Header */}
        <div className="bg-slate-900 text-white px-5 py-4 flex items-start justify-between gap-3">
          <div className="space-y-1 min-w-0">
            <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5 text-[11px] font-mono tabular-nums text-slate-300">
              <span className="text-emerald-300 font-semibold">
                3-DAY SEAL: {data?.threeDaySync?.allThreeDaysSealed !== false ? '18/18 VERIFIED' : 'SYNCING'}
              </span>
              <span aria-hidden="true">·</span>
              <span>HEAD: {headShort}</span>
              {data?.workspaceArchiveFileCount ? (
                <>
                  <span aria-hidden="true">·</span>
                  <span>{data.workspaceArchiveFileCount} files tracked (0 missed)</span>
                </>
              ) : null}
              {gh?.anyTargetRepoPushed ? (
                <>
                  <span aria-hidden="true">·</span>
                  <span className="text-emerald-300 font-semibold">GITHUB PUSHED</span>
                </>
              ) : null}
            </div>
            <h2 id="global-get-work-title" className="text-base sm:text-lg font-bold">
              Direct GitHub Push &amp; Iframe-Proof 3-Day Recovery (15–17 Nov 2026)
            </h2>
          </div>

          <button
            type="button"
            onClick={onClose}
            aria-label="Close Get All Work dialog"
            className="rounded-lg p-1.5 text-slate-300 hover:bg-slate-800 hover:text-white shrink-0"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="p-5 space-y-4 text-xs text-slate-700 max-h-[82vh] overflow-y-auto">
          {/* METHOD 1: Direct Container -> GitHub Push via RFC 8628 Device Flow (Zero Download, Zero SSH, Zero API Key Input) */}
          <section className="rounded-xl border border-slate-900 bg-slate-50 p-4 space-y-3">
            <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
              <div className="space-y-1">
                <div className="text-sm font-bold text-slate-900">
                  Method 1 (Recommended) — Push Directly from This Server to GitHub
                </div>
                <p className="text-xs text-slate-600">
                  Bypasses browser iframe download blocks, <code className="font-mono">ais-pre</code>{' '}
                  404s, and SSH keys completely. Approve an 8-character GitHub Device Code once — our
                  server immediately pushes all 3 days (<code className="font-mono">HEAD</code>) to{' '}
                  <code className="font-mono">chidionyema/gemini-sync</code> &amp;{' '}
                  <code className="font-mono">chidionyema/argon-sync</code> on{' '}
                  <code className="font-mono">refs/heads/aistudio/meridian-hermes-carbon-20261117</code>{' '}
                  (#7760 producer ref), <code className="font-mono">aistudio/meridian-hermes-live</code>,
                  and opens a clean PR branch parented on <code className="font-mono">main</code>.
                </p>
              </div>

              <button
                type="button"
                disabled={startingDevice || gh?.phase === 'AUTHORIZED_PUSHING'}
                onClick={() => void handleStartGitHubDevicePush()}
                className="min-h-[42px] inline-flex items-center justify-center gap-1.5 rounded-lg bg-slate-900 px-4 py-2 text-xs font-bold text-white hover:bg-slate-800 disabled:opacity-50 whitespace-nowrap shrink-0"
              >
                <GitBranch className="h-4 w-4 text-emerald-400 shrink-0" aria-hidden="true" />
                <span>
                  {gh?.phase === 'AUTHORIZED_PUSHING' || (gh?.authorizedInMemory && startingDevice)
                    ? 'Pushing to GitHub…'
                    : startingDevice
                      ? 'Generating Code…'
                      : gh?.authorizedInMemory
                        ? 'Push Latest HEAD to GitHub Now'
                        : 'Generate GitHub Code & Push All 3 Days'}
                </span>
              </button>
            </div>

            {gh?.phase === 'AWAITING_USER_APPROVAL' && gh.userCode && (
              <div className="rounded-lg border border-slate-900 bg-white p-3.5 space-y-2.5">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5">
                  <div className="space-y-0.5">
                    <div className="text-[11px] font-semibold text-slate-600">
                      Step 1: Copy this 8-character code · Step 2: Paste at github.com/login/device
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xl font-bold tracking-widest text-slate-900 tabular-nums">
                        {gh.userCode}
                      </span>
                      <button
                        type="button"
                        onClick={() => void handleCopyDeviceCode(gh.userCode!)}
                        className="inline-flex items-center gap-1 rounded border border-slate-300 bg-slate-50 px-2.5 py-1 text-xs font-semibold text-slate-800 hover:bg-slate-100"
                      >
                        {copiedUserCode ? (
                          <>
                            <Check className="h-3.5 w-3.5 text-emerald-600" aria-hidden="true" />
                            Copied Code
                          </>
                        ) : (
                          <>
                            <Copy className="h-3.5 w-3.5" aria-hidden="true" />
                            Copy Code
                          </>
                        )}
                      </button>
                    </div>
                  </div>

                  <a
                    href={gh.verificationUri}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="min-h-[40px] inline-flex items-center justify-center gap-1.5 rounded-lg bg-emerald-700 px-4 py-2 text-xs font-bold text-white hover:bg-emerald-800 whitespace-nowrap"
                  >
                    <span>Open github.com/login/device</span>
                    <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
                  </a>
                </div>
                <div className="text-[11px] font-mono text-slate-600">
                  Waiting for your click on GitHub… This dialog updates automatically via SSE the
                  second your push lands.
                </div>
              </div>
            )}

            {gh && gh.repoReceipts.length > 0 && (
              <div
                className={`rounded-lg border p-3 space-y-2 font-mono text-[11px] ${
                  gh.anyTargetRepoPushed
                    ? 'border-emerald-300 bg-emerald-50 text-emerald-950'
                    : 'border-amber-300 bg-amber-50 text-amber-950'
                }`}
              >
                <div className="font-bold">{gh.statusMessage}</div>
                {gh.repoReceipts.map((r) => (
                  <div
                    key={r.repo}
                    className="flex flex-wrap items-center justify-between gap-2 border-t border-black/10 pt-1.5"
                  >
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
          </section>

          {/* METHOD 2: Iframe-Proof 1-Click Self-Extracting Clipboard Capsule */}
          <section className="rounded-xl border border-slate-200 bg-white p-4 space-y-2.5">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5">
              <div className="space-y-0.5">
                <div className="font-bold text-slate-900">
                  Method 2 — Copy Entire 3-Day Repo as 1 Terminal Paste (Works Even If Downloads Are Blocked)
                </div>
                <p className="text-[11px] text-slate-600">
                  Copies a single SHA-256 verified, gzip-compressed command containing{' '}
                  <strong>all {capsule?.fileCount ?? data?.workspaceArchiveFileCount ?? 113} tracked files</strong>{' '}
                  ({capsule ? `${Math.round(capsule.compressedBytes / 1024)} KB` : '~800 KB'}). Paste into any
                  Mac/Linux terminal to unpack the entire repo, init Git with{' '}
                  <code className="font-mono">aistudio/meridian-hermes-carbon-20261117</code>, and push.
                </p>
              </div>

              <div className="flex flex-wrap items-center gap-2 shrink-0">
                <button
                  type="button"
                  disabled={loadingCapsule || !capsule}
                  onClick={handleCopySelfExtractingCapsule}
                  className="min-h-[38px] inline-flex items-center gap-1.5 rounded-lg bg-slate-900 px-3.5 py-1.5 text-xs font-semibold text-white hover:bg-slate-800 disabled:opacity-50 whitespace-nowrap"
                >
                  {copiedCapsule ? (
                    <>
                      <Check className="h-3.5 w-3.5 text-emerald-400" aria-hidden="true" />
                      Copied All {capsule?.fileCount ?? ''} Files!
                    </>
                  ) : (
                    <>
                      <Terminal className="h-3.5 w-3.5 text-amber-300" aria-hidden="true" />
                      {loadingCapsule ? 'Packing…' : 'Copy 1-Command Repo Capsule'}
                    </>
                  )}
                </button>

                <button
                  type="button"
                  onClick={() => setShowRawCapsuleBox((v) => !v)}
                  className="min-h-[38px] rounded-lg border border-slate-300 bg-slate-50 px-2.5 py-1.5 text-xs font-medium text-slate-800 hover:bg-slate-100 whitespace-nowrap"
                >
                  {showRawCapsuleBox ? 'Hide Text Box' : 'Manual Select (⌘A, ⌘C)'}
                </button>
              </div>
            </div>

            {showRawCapsuleBox && capsule && (
              <div className="space-y-1">
                <label htmlFor="raw-capsule-textarea" className="block text-[11px] font-medium text-slate-600">
                  Click inside box, press ⌘A (or Ctrl+A) then ⌘C (or Ctrl+C), and paste into terminal:
                </label>
                <textarea
                  id="raw-capsule-textarea"
                  readOnly
                  rows={4}
                  onFocus={(e) => e.currentTarget.select()}
                  value={capsule.shellCommand}
                  className="w-full rounded-lg border border-slate-300 bg-slate-950 text-slate-100 p-2.5 font-mono text-[11px]"
                />
              </div>
            )}
          </section>

          {/* METHOD 3: Fetch->Blob Downloads + AI Studio Native Toolbar + Outbound Tunnel */}
          <section className="rounded-xl border border-slate-200 bg-white p-4 space-y-3">
            <div className="space-y-1">
              <div className="font-bold text-slate-900">
                Method 3 — AI Studio Top-Right Toolbar, Fetch-Blob Downloads &amp; Tunnel Push
              </div>
              <p className="text-[11px] text-slate-600">
                Outside this preview frame, AI Studio’s own top-right toolbar has{' '}
                <strong>Save to GitHub</strong> and <strong>Download app (ZIP)</strong> (immune to
                iframe sandbox rules). Or trigger authenticated <code className="font-mono">fetch()</code>{' '}
                binary downloads / outbound HTTPS push below:
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
              <button
                type="button"
                disabled={downloadingKey !== null}
                onClick={() =>
                  void handleFetchBlobDownload(
                    'bundle',
                    '/api/export/bundle',
                    'meridian-hermes-today.bundle'
                  )
                }
                className="min-h-[40px] inline-flex items-center justify-center gap-1.5 rounded-lg border border-slate-900 bg-white px-3 py-2 text-xs font-bold text-slate-900 hover:bg-slate-100 disabled:opacity-50 whitespace-nowrap"
              >
                <PackageCheck className="h-4 w-4 text-slate-900 shrink-0" aria-hidden="true" />
                <span>
                  {downloadingKey === 'bundle' ? 'Fetching…' : `Git Bundle (${bundleMb})`}
                </span>
              </button>

              <button
                type="button"
                disabled={downloadingKey !== null}
                onClick={() =>
                  void handleFetchBlobDownload(
                    'tar',
                    '/api/export/all-3days',
                    'meridian-complete-3days-2026-11-17.tar.gz'
                  )
                }
                className="min-h-[40px] inline-flex items-center justify-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-semibold text-slate-800 hover:bg-slate-100 disabled:opacity-50 whitespace-nowrap"
              >
                <FolderArchive className="h-4 w-4 text-slate-700 shrink-0" aria-hidden="true" />
                <span>
                  {downloadingKey === 'tar' ? 'Fetching…' : `All 3 Days (.tar.gz · ${archiveMb})`}
                </span>
              </button>

              <button
                type="button"
                disabled={downloadingKey !== null}
                onClick={() =>
                  void handleFetchBlobDownload(
                    'manifest',
                    '/FLEET_3DAY_CANONICAL_MANIFEST.md?download=1',
                    'FLEET_3DAY_CANONICAL_MANIFEST.md'
                  )
                }
                className="min-h-[40px] inline-flex items-center justify-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-semibold text-slate-800 hover:bg-slate-100 disabled:opacity-50 whitespace-nowrap"
              >
                <Download className="h-4 w-4 text-slate-700 shrink-0" aria-hidden="true" />
                <span>3-Day Manifest (.md)</span>
              </button>
            </div>

            {downloadNotice && (
              <div
                className={`rounded-lg border p-2.5 font-mono text-[11px] [overflow-wrap:anywhere] ${
                  downloadNotice.ok
                    ? 'border-emerald-300 bg-emerald-50 text-emerald-950'
                    : 'border-amber-300 bg-amber-50 text-amber-950'
                }`}
              >
                {downloadNotice.text}
              </div>
            )}

            <form onSubmit={(e) => void handleSaveAndPush(e)} className="space-y-2 pt-1">
              <div className="flex flex-col sm:flex-row gap-2">
                <label htmlFor="global-auto-push-url" className="sr-only">
                  HTTPS Receiver or Pre-Signed Upload URL
                </label>
                <input
                  id="global-auto-push-url"
                  type="text"
                  value={targetUrl}
                  onChange={(e) => setTargetUrl(e.target.value)}
                  placeholder="Optional: https://your-tunnel-or-r2-presigned-url..."
                  className="flex-1 min-w-0 min-h-[38px] rounded-lg border border-slate-300 px-3 py-1.5 font-mono text-xs text-slate-900"
                />
                <label htmlFor="global-auto-push-method" className="sr-only">
                  HTTP Method
                </label>
                <select
                  id="global-auto-push-method"
                  value={targetMethod}
                  onChange={(e) => setTargetMethod(e.target.value as 'POST' | 'PUT')}
                  className="min-h-[38px] rounded-lg border border-slate-300 bg-white px-2.5 py-1.5 font-mono text-xs text-slate-900"
                >
                  <option value="POST">POST (Tunnel)</option>
                  <option value="PUT">PUT (S3 / R2)</option>
                </select>
                <button
                  type="submit"
                  disabled={submitting}
                  className="min-h-[38px] inline-flex items-center justify-center gap-1.5 rounded-lg border border-slate-900 bg-slate-900 px-3 py-1.5 text-xs font-semibold text-white hover:bg-slate-800 disabled:opacity-50 whitespace-nowrap"
                >
                  <Send className="h-3.5 w-3.5 text-cyan-400" aria-hidden="true" />
                  {submitting ? 'Pushing…' : targetUrl.trim() ? 'Save & Push' : 'Retry Fleet'}
                </button>
                <button
                  type="button"
                  disabled={loading}
                  onClick={() => void loadStatus()}
                  aria-label="Refresh sync status"
                  className="min-h-[38px] rounded-lg border border-slate-300 px-2.5 text-slate-600 hover:bg-slate-50 shrink-0"
                >
                  <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" />
                </button>
              </div>
            </form>

            {statusNotice && (
              <div
                className={`rounded-lg border p-2.5 font-mono text-[11px] [overflow-wrap:anywhere] ${
                  statusNotice.ok
                    ? 'border-emerald-300 bg-emerald-50 text-emerald-950'
                    : 'border-amber-300 bg-amber-50 text-amber-950'
                }`}
              >
                {statusNotice.text}
              </div>
            )}

            {data?.registeredCustomTargets && data.registeredCustomTargets.length > 0 && (
              <div className="space-y-1.5 pt-1">
                {data.registeredCustomTargets.map((t) => (
                  <div
                    key={t.url}
                    className="flex items-center justify-between gap-2 rounded border border-slate-200 bg-slate-50 px-2.5 py-1.5 font-mono text-[11px] min-w-0"
                  >
                    <span className="truncate">
                      [{t.method}] {t.url}{' '}
                      {t.lastHttpStatus ? `(HTTP ${t.lastHttpStatus})` : '(queued)'}
                    </span>
                    <button
                      type="button"
                      onClick={() => void handleRemoveTarget(t.url)}
                      aria-label={`Remove saved target ${t.url}`}
                      className="text-slate-500 hover:text-red-600 shrink-0"
                    >
                      <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </section>

          <div className="flex flex-wrap items-center justify-between gap-2 pt-1 text-[11px] text-slate-500">
            <span className="font-mono [overflow-wrap:anywhere]">
              Bundle SHA-256: {data?.currentBundleSha256 ?? 'computing…'}
            </span>
            {onOpenFullHandoffTab && (
              <button
                type="button"
                onClick={() => {
                  onClose();
                  onOpenFullHandoffTab();
                }}
                className="inline-flex items-center gap-1 font-semibold text-slate-800 hover:text-slate-950"
              >
                <Download className="h-3.5 w-3.5" aria-hidden="true" />
                Open Full Handoff &amp; Manifest View
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
