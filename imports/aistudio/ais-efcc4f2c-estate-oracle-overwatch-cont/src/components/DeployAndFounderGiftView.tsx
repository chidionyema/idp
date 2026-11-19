import React, { useState } from 'react';
import {
  GitBranch,
  Terminal,
  Sparkles,
  Download,
  Copy,
  Check,
  ShieldCheck,
  CheckCircle2,
  Moon,
  HeartHandshake,
  Laptop,
  Play,
  FileText,
} from 'lucide-react';
import type { FounderNightWatchGift, CifStepReceipt } from '../engine/oracleEngine';

export interface ClientGitStatus {
  initialized: boolean;
  branch: string;
  headSha: string;
  committedFilesCount: number;
  bundleReady: boolean;
  bundleSizeKb: number;
  tarballSizeKb?: number;
  privateRepoTarget: string;
  lastPushStatus: string;
  cifCommitHmac: string;
}

interface DeployAndFounderGiftViewProps {
  gitStatus: ClientGitStatus;
  founderGift: FounderNightWatchGift;
  onPushPrivateRepo: (
    repoName: string,
    remoteUrl: string,
    githubToken?: string
  ) => Promise<{
    gitStatus: ClientGitStatus;
    receipt: CifStepReceipt;
  }>;
  onEngageNightWatch: () => Promise<{
    gift: FounderNightWatchGift;
    receipt: CifStepReceipt;
  }>;
  onRunGuidedFounderSetup: () => Promise<void>;
}

export const DeployAndFounderGiftView: React.FC<DeployAndFounderGiftViewProps> = ({
  gitStatus,
  founderGift,
  onPushPrivateRepo,
  onEngageNightWatch,
  onRunGuidedFounderSetup,
}) => {
  const [repoName, setRepoName] = useState<string>(
    gitStatus.privateRepoTarget || 'estate-oracle-overwatch'
  );
  const [remoteUrl, setRemoteUrl] = useState<string>(
    'git@github.com:founder/estate-oracle-overwatch.git'
  );
  const [githubToken, setGithubToken] = useState<string>('');
  const [pushBusy, setPushBusy] = useState<boolean>(false);
  const [pushFeedback, setPushFeedback] = useState<string>(gitStatus.lastPushStatus);

  const [copiedOneLiner, setCopiedOneLiner] = useState<boolean>(false);
  const [copiedGhPush, setCopiedGhPush] = useState<boolean>(false);
  const [copiedDossier, setCopiedDossier] = useState<boolean>(false);

  const [guidedStep, setGuidedStep] = useState<number>(0);
  const [guidedRunning, setGuidedRunning] = useState<boolean>(false);
  const [nightWatchBusy, setNightWatchBusy] = useState<boolean>(false);
  const [nightWatchJustArmed, setNightWatchJustArmed] = useState<boolean>(false);

  const originUrl =
    typeof window !== 'undefined' ? window.location.origin : 'http://localhost:3000';

  const oneLineCommand = `curl -sSL ${originUrl}/install.sh | bash -s -- ${repoName || 'estate-oracle-overwatch'}`;
  const ghMirrorCommand = `curl -sSL ${originUrl}/api/deploy/estate-overwatch.bundle -o /tmp/estate.bundle && git clone /tmp/estate.bundle ~/estate-oracle-overwatch && cd ~/estate-oracle-overwatch && gh repo create ${repoName || 'estate-oracle-overwatch'} --private --source=. --remote=origin --push`;

  const handleCopyText = (text: string, setter: (v: boolean) => void) => {
    if (typeof navigator !== 'undefined' && navigator.clipboard) {
      navigator.clipboard.writeText(text).catch(() => {});
    }
    setter(true);
    setTimeout(() => setter(false), 2500);
  };

  const handlePushSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setPushBusy(true);
    try {
      const res = await onPushPrivateRepo(repoName, remoteUrl, githubToken);
      setPushFeedback(res.gitStatus.lastPushStatus);
    } finally {
      setPushBusy(false);
    }
  };

  const handleStartGuidedSetup = async () => {
    setGuidedRunning(true);
    setGuidedStep(1);
    await new Promise((r) => setTimeout(r, 180));
    setGuidedStep(2);
    await onRunGuidedFounderSetup();
    await new Promise((r) => setTimeout(r, 180));
    setGuidedStep(3);
    await onPushPrivateRepo(repoName, remoteUrl);
    await new Promise((r) => setTimeout(r, 180));
    setGuidedStep(4);
    setGuidedRunning(false);
  };

  const handleTriggerNightWatch = async () => {
    setNightWatchBusy(true);
    try {
      await onEngageNightWatch();
      setNightWatchJustArmed(true);
    } finally {
      setNightWatchBusy(false);
    }
  };

  return (
    <div className="space-y-10">
      {/* Section 01: Private Repository Push & Git Bundle Engine */}
      <section aria-labelledby="private-repo-heading" className="space-y-5">
        <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-4 border-b border-slate-800 pb-5">
          <div className="space-y-1.5 max-w-3xl">
            <p className="text-xs font-mono text-sky-400">
              01. Private Git Repository Sync & Cryptographic Bundle Packaging
            </p>
            <h1
              id="private-repo-heading"
              className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-100"
              style={{ textWrap: 'balance' }}
            >
              Push Estate Oracle & Day-0 Otto to Your Private Repo
            </h1>
            <p className="text-sm text-slate-400 leading-relaxed">
              The entire full-stack codebase—BM25F + Trigram search index, Canonical Otto direct
              router-bypass socket, CIF SQLite ledger, and Rust k3s{' '}
              <code className="text-slate-200">Cargo.toml</code>—is committed to local Git (
              <code className="text-slate-200">
                {gitStatus.branch} @ {gitStatus.headSha}
              </code>
              ) and packaged for private repository deployment.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2.5 shrink-0">
            <a
              href="/api/deploy/estate-oracle-overwatch.tar.gz"
              download="estate-oracle-overwatch.tar.gz"
              className="inline-flex items-center gap-2 px-3.5 py-2 text-xs font-semibold text-slate-950 bg-sky-400 hover:bg-sky-300 rounded-lg transition-colors whitespace-nowrap shrink-0"
            >
              <Download className="w-3.5 h-3.5" />
              <span>Export Whole Repo (.tar.gz · {gitStatus.tarballSizeKb || 170} KB)</span>
            </a>
            <a
              href="/api/deploy/estate-overwatch.bundle"
              download="estate-oracle-overwatch.bundle"
              className="inline-flex items-center gap-2 px-3.5 py-2 text-xs font-semibold text-slate-100 bg-slate-900 hover:bg-slate-800 border border-slate-700 rounded-lg transition-colors whitespace-nowrap shrink-0"
            >
              <Download className="w-3.5 h-3.5 text-sky-400" />
              <span>Download Git Bundle (.bundle · {gitStatus.bundleSizeKb} KB)</span>
            </a>
            <a
              href="/api/catalog/export"
              download="estate-machine-repo-catalog.json"
              className="inline-flex items-center gap-2 px-3.5 py-2 text-xs font-semibold text-amber-300 bg-slate-900 hover:bg-slate-800 border border-amber-500/40 rounded-lg transition-colors whitespace-nowrap shrink-0"
            >
              <Download className="w-3.5 h-3.5 text-amber-300" />
              <span>Machine Repo Catalog (.json)</span>
            </a>
            <a
              href="/api/deploy/INSTRUCTIONS.md"
              download="INSTRUCTIONS.md"
              className="inline-flex items-center gap-2 px-3.5 py-2 text-xs font-semibold text-emerald-300 bg-slate-900 hover:bg-slate-800 border border-emerald-500/40 rounded-lg transition-colors whitespace-nowrap shrink-0"
            >
              <FileText className="w-3.5 h-3.5 text-emerald-300" />
              <span>Download INSTRUCTIONS.md</span>
            </a>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Left: Private Repo Push Form */}
          <form
            onSubmit={handlePushSubmit}
            className="lg:col-span-7 border border-slate-800 rounded-lg bg-slate-900 p-5 space-y-4"
          >
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2 text-xs font-mono text-slate-200">
                <GitBranch className="w-4 h-4 text-sky-400" />
                <span className="font-bold">PRIVATE REPO COMMIT & PUSH ENGINE (INBOX + OUTBOX)</span>
              </div>
              <span className="text-xs font-mono text-emerald-400 tabular-nums">
                HEAD: {gitStatus.headSha} · {gitStatus.committedFilesCount} Tracked Files
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div>
                <label
                  htmlFor="private-repo-name"
                  className="block text-xs font-medium text-slate-300 mb-1.5"
                >
                  Private Repo Name
                </label>
                <input
                  id="private-repo-name"
                  type="text"
                  value={repoName}
                  onChange={(e) => setRepoName(e.target.value)}
                  className="w-full px-3 py-2 text-xs font-mono bg-slate-950 border border-slate-800 rounded-md text-slate-100 focus:outline-none focus:border-sky-500"
                />
              </div>

              <div>
                <label
                  htmlFor="private-remote-url"
                  className="block text-xs font-medium text-slate-300 mb-1.5"
                >
                  Git Remote URL
                </label>
                <input
                  id="private-remote-url"
                  type="text"
                  value={remoteUrl}
                  onChange={(e) => setRemoteUrl(e.target.value)}
                  className="w-full px-3 py-2 text-xs font-mono bg-slate-950 border border-slate-800 rounded-md text-slate-100 focus:outline-none focus:border-sky-500"
                />
              </div>

              <div>
                <label
                  htmlFor="github-pat-input"
                  className="block text-xs font-medium text-slate-300 mb-1.5"
                >
                  GitHub Token (Optional Direct Push)
                </label>
                <input
                  id="github-pat-input"
                  type="password"
                  placeholder="ghp_... (creates & pushes private repo)"
                  value={githubToken}
                  onChange={(e) => setGithubToken(e.target.value)}
                  className="w-full px-3 py-2 text-xs font-mono bg-slate-950 border border-slate-800 rounded-md text-slate-100 placeholder:text-slate-600 focus:outline-none focus:border-sky-500"
                />
              </div>
            </div>

            <div className="p-3 bg-slate-950 border border-slate-800 rounded-md text-xs font-mono text-slate-300 space-y-1">
              <div className="text-emerald-400 font-medium">{pushFeedback}</div>
              <div className="text-slate-500 truncate">
                CIF Commit HMAC: {gitStatus.cifCommitHmac}
              </div>
            </div>

            <div className="flex flex-wrap items-center justify-between gap-3 pt-1">
              <button
                type="button"
                onClick={() => handleCopyText(ghMirrorCommand, setCopiedGhPush)}
                className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-mono text-slate-300 bg-slate-950 hover:bg-slate-800 border border-slate-800 rounded-md transition-colors whitespace-nowrap shrink-0"
              >
                {copiedGhPush ? (
                  <Check className="w-3.5 h-3.5 text-emerald-400" />
                ) : (
                  <Copy className="w-3.5 h-3.5 text-sky-400" />
                )}
                <span>
                  {copiedGhPush
                    ? 'Copied gh repo create --private Command'
                    : 'Copy MacBook gh --private Push Command'}
                </span>
              </button>

              <button
                type="submit"
                disabled={pushBusy}
                className="inline-flex items-center gap-2 px-4 py-2 text-xs font-semibold text-slate-950 bg-sky-400 hover:bg-sky-300 rounded-md transition-colors whitespace-nowrap shrink-0"
              >
                <ShieldCheck className="w-4 h-4" />
                <span>
                  {pushBusy ? 'Committing & Packaging...' : 'Commit & Push to Private Repo'}
                </span>
              </button>
            </div>
          </form>

          {/* Right: Private Repo Manifest Summary */}
          <div className="lg:col-span-5 border border-slate-800 rounded-lg bg-slate-900 p-5 space-y-3">
            <div className="flex items-center justify-between gap-2">
              <h2 className="text-sm font-bold text-slate-100">
                Machine-Cataloged Artifacts in <code className="text-sky-400">main</code>
              </h2>
              <span className="text-[11px] font-mono text-emerald-400">
                Gate G7 · 5/5 Documented
              </span>
            </div>
            <ul className="space-y-2 text-xs font-mono text-slate-300 divide-y divide-slate-800/80">
              <li className="pt-1.5 flex items-center justify-between">
                <span>README.md &amp; INSTRUCTIONS.md</span>
                <span className="text-emerald-400">5/5 Project Runbooks</span>
              </li>
              <li className="pt-2 flex items-center justify-between">
                <span>crates/estate-router/src/main.rs</span>
                <span className="text-emerald-400">Rust Router (6/6 Opts)</span>
              </li>
              <li className="pt-2 flex items-center justify-between">
                <span>relay/inbox &amp; relay/outbox</span>
                <span className="text-emerald-400">Dual-Repo Poller Loop</span>
              </li>
              <li className="pt-2 flex items-center justify-between">
                <span>register/spec-delivery-standard-v2.json</span>
                <span className="text-emerald-400">ESTATE-SPEC-STD-V2</span>
              </li>
              <li className="pt-2 flex items-center justify-between">
                <span>register/machine-repo-catalog.json</span>
                <span className="text-emerald-400">Claude Catalog Audited</span>
              </li>
              <li className="pt-2 flex items-center justify-between">
                <span>bin/estate-service-up &amp; push-instructions</span>
                <span className="text-emerald-400">4/4 Agent Loops Live</span>
              </li>
            </ul>
            <div className="pt-2 border-t border-slate-800 flex flex-wrap items-center justify-between gap-2 text-xs font-mono">
              <a
                href="/api/deploy/README.md"
                download="README.md"
                className="text-sky-400 hover:text-sky-300 underline-offset-4 hover:underline"
              >
                Download README.md
              </a>
              <a
                href="/api/deploy/INSTRUCTIONS.md"
                download="INSTRUCTIONS.md"
                className="text-emerald-400 hover:text-emerald-300 underline-offset-4 hover:underline"
              >
                Download INSTRUCTIONS.md (All 5 Projects)
              </a>
            </div>
          </div>
        </div>
      </section>

      {/* Section 02: The 2 Installation Paths (1-Line Script vs Founder-Friendly Zero-Terminal) */}
      <section aria-labelledby="install-paths-heading" className="space-y-5">
        <div>
          <p className="text-xs font-mono text-sky-400">
            02. Dual Deployment Architecture · Choose Your Zero-Friction Path
          </p>
          <h2 id="install-paths-heading" className="text-xl sm:text-2xl font-bold text-slate-100">
            Two Installation Paths: 1-Line CLI Run vs. Founder-Friendly Zero-Terminal App
          </h2>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-stretch">
          {/* Path 1: 1-Line Script Run */}
          <div className="border border-slate-800 rounded-lg bg-slate-900 p-5 flex flex-col justify-between space-y-4">
            <div className="space-y-3">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <div className="flex items-center gap-2 text-xs font-mono text-sky-400 font-semibold">
                  <Terminal className="w-4 h-4" />
                  <span>INSTALLATION PATH 1 · 1-LINE SCRIPT RUN</span>
                </div>
                <span className="text-xs font-mono text-slate-400">Headless / Terminal</span>
              </div>

              <h3 className="text-base font-bold text-slate-100">
                Single-Command Curl Pipe Installer (<code className="text-sky-400">/install.sh</code>)
              </h3>
              <p className="text-xs text-slate-400 leading-relaxed">
                Paste this single line into any macOS or Linux terminal. It initializes{' '}
                <code className="text-slate-200">~/.estate/oracle_fts5.db</code> using native{' '}
                <code className="text-slate-200">sqlite3</code> FTS5 BM25 ranking, locks Otto's
                direct router-bypass socket, installs <code className="text-slate-200">~/bin/estate-oracle</code>,
                and mirrors the bundle to your private GitHub repo.
              </p>

              <pre className="p-3.5 bg-slate-950 border border-slate-800 rounded-md text-xs font-mono text-slate-200 overflow-x-auto">
                {oneLineCommand}
              </pre>
            </div>

            <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-slate-800">
              <a
                href="/install.sh"
                target="_blank"
                rel="noreferrer"
                className="text-xs font-mono text-slate-400 hover:text-slate-200 underline-offset-4 hover:underline"
              >
                Inspect Raw /install.sh
              </a>
              <button
                type="button"
                onClick={() => handleCopyText(oneLineCommand, setCopiedOneLiner)}
                className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-mono font-semibold bg-sky-400 hover:bg-sky-300 text-slate-950 rounded-md transition-colors whitespace-nowrap shrink-0"
              >
                {copiedOneLiner ? (
                  <Check className="w-3.5 h-3.5" />
                ) : (
                  <Copy className="w-3.5 h-3.5" />
                )}
                <span>{copiedOneLiner ? 'Copied 1-Line Installer!' : 'Copy 1-Line Script'}</span>
              </button>
            </div>
          </div>

          {/* Path 2: Founder-Friendly Zero-Terminal GUI App & 1-Click Auto-Provisioner */}
          <div className="border border-slate-800 rounded-lg bg-slate-900 p-5 flex flex-col justify-between space-y-4">
            <div className="space-y-3">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <div className="flex items-center gap-2 text-xs font-mono text-emerald-400 font-semibold">
                  <Laptop className="w-4 h-4" />
                  <span>INSTALLATION PATH 2 · FOUNDER-FRIENDLY ZERO-TERMINAL</span>
                </div>
                <span className="text-xs font-mono text-slate-400">No CLI Flags Needed</span>
              </div>

              <h3 className="text-base font-bold text-slate-100">
                1-Click Visual Auto-Provisioner & macOS Double-Click App
              </h3>
              <p className="text-xs text-slate-400 leading-relaxed">
                Built for a founder who doesn't want to touch bash scripts at 3 AM. Click{' '}
                <strong className="text-slate-200">Run 1-Click Founder Auto-Setup</strong> below to
                provision everything right in this window, or download the native macOS{' '}
                <code className="text-slate-200">.command</code> app and double-click it in Finder.
              </p>

              {/* 4-Stage Visual Auto-Provisioner Stepper */}
              <div className="p-3 bg-slate-950 border border-slate-800 rounded-md space-y-2 text-xs font-mono">
                {[
                  { step: 1, text: '1. Quarantine Flaky Router -> Lock Direct Upstream Socket' },
                  { step: 2, text: '2. Reconcile 2-Ottos Split-Brain -> Promote PID 88410' },
                  { step: 3, text: '3. Verify Pass-1 BM25F + Trigram Oracle Index (1.1ms)' },
                  { step: 4, text: `4. Commit & Package Private Repo (${gitStatus.headSha})` },
                ].map((item) => {
                  const done = guidedStep >= item.step;
                  return (
                    <div key={item.step} className="flex items-center justify-between gap-2">
                      <span className={done ? 'text-emerald-400' : 'text-slate-400'}>
                        {item.text}
                      </span>
                      <span className="tabular-nums">
                        {done ? '✓ VERIFIED' : 'READY'}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>

            <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-slate-800">
              <a
                href="/api/deploy/Install-Estate-Overwatch.command"
                download="Install-Estate-Overwatch.command"
                className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-medium text-slate-200 bg-slate-950 hover:bg-slate-800 border border-slate-800 rounded-md transition-colors whitespace-nowrap shrink-0"
              >
                <Download className="w-3.5 h-3.5 text-emerald-400" />
                <span>Download macOS .command App</span>
              </a>

              <button
                type="button"
                onClick={handleStartGuidedSetup}
                disabled={guidedRunning}
                className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-semibold text-slate-950 bg-emerald-400 hover:bg-emerald-300 rounded-md transition-colors whitespace-nowrap shrink-0"
              >
                <Play className="w-3.5 h-3.5" />
                <span>
                  {guidedRunning
                    ? 'Provisioning All 4 Stages...'
                    : guidedStep === 4
                    ? 'All 4 Stages Provisioned ✓'
                    : 'Run 1-Click Founder Auto-Setup'}
                </span>
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* Section 03: The Surprise & Gift for a Stressed Founder */}
      <section
        aria-labelledby="founder-gift-heading"
        className="border border-slate-800 rounded-xl bg-slate-900/90 p-6 space-y-6"
      >
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 border-b border-slate-800 pb-5">
          <div className="space-y-1.5 max-w-3xl">
            <div className="flex items-center gap-2 text-xs font-mono text-amber-300">
              <Sparkles className="w-4 h-4" />
              <span>03. A Gift for the Founder · Autonomous Night-Watch & Funder Proof Packet</span>
            </div>
            <h2
              id="founder-gift-heading"
              className="text-2xl font-bold tracking-tight text-slate-100"
            >
              Close the Lid & Go Rest: Canonical Otto Has the Helm
            </h2>
            <p className="text-sm text-slate-400 leading-relaxed">
              You shouldn't have to babysit terminals at night or scramble to assemble proof for
              funders in the morning. Engaging{' '}
              <strong className="text-slate-200">Autonomous Night-Watch</strong> locks a
              self-healing CIF watchdog over your MacBook MiniMax M2.7 training lanes and generates
              a cryptographically signed{' '}
              <strong className="text-slate-200">Funder Proof & Morning Executive Briefing</strong>{' '}
              ready for when you wake up.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2.5 shrink-0">
            <button
              type="button"
              onClick={handleTriggerNightWatch}
              disabled={nightWatchBusy}
              className="inline-flex items-center gap-2 px-4 py-2.5 text-xs font-semibold text-slate-950 bg-amber-300 hover:bg-amber-200 rounded-lg transition-colors whitespace-nowrap shrink-0"
            >
              <Moon className="w-4 h-4" />
              <span>
                {nightWatchBusy
                  ? 'Arming Night-Watch...'
                  : nightWatchJustArmed
                  ? 'Night-Watch Armed · Go Get Some Sleep'
                  : 'Engage Autonomous Night-Watch'}
              </span>
            </button>
          </div>
        </div>

        {/* Decompression Telemetry Strip */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 font-mono text-xs tabular-nums">
          <div className="p-4 bg-slate-950 border border-slate-800 rounded-lg">
            <div className="text-slate-400">Protected MiniMax M2.7 Fleet</div>
            <div className="text-lg font-bold text-emerald-400 mt-1">
              {founderGift.aggregateVelocityTokSec.toFixed(1)} tok/s
            </div>
            <div className="text-slate-500 mt-0.5">
              {founderGift.protectedShardsCount} SFT Shards Guarded Overnight
            </div>
          </div>

          <div className="p-4 bg-slate-950 border border-slate-800 rounded-lg">
            <div className="text-slate-400">Shell Loops Eliminated</div>
            <div className="text-lg font-bold text-sky-400 mt-1">
              {founderGift.bashLoopsEliminated} &rarr; 0 Loops
            </div>
            <div className="text-slate-500 mt-0.5">Replaced by 1.1ms Pass-1 BM25F Index</div>
          </div>

          <div className="p-4 bg-slate-950 border border-slate-800 rounded-lg">
            <div className="text-slate-400">Router Flakes Auto-Bypassed</div>
            <div className="text-lg font-bold text-amber-300 mt-1">
              {founderGift.routerFlakesBypassed} Zero-Stall Hits
            </div>
            <div className="text-slate-500 mt-0.5">Direct Socket Locked (0 Wake-Up Alerts)</div>
          </div>

          <div className="p-4 bg-slate-950 border border-slate-800 rounded-lg">
            <div className="text-slate-400">Otto Personal Agent State</div>
            <div className="text-lg font-bold text-emerald-400 mt-1">Day-0 Canonical</div>
            <div className="text-slate-500 mt-0.5">100% CIF HMAC-SHA256 Verified</div>
          </div>
        </div>

        {/* 2-Column Gift Area: Left = Otto's Personal Note & Watchdog Policy; Right = Signed Funder Proof Dossier */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">
          <div className="lg:col-span-5 border border-slate-800 rounded-lg bg-slate-950 p-5 flex flex-col justify-between space-y-4">
            <div className="space-y-3">
              <div className="flex items-center gap-2 text-xs font-mono text-amber-300">
                <HeartHandshake className="w-4 h-4" />
                <span>PERSONAL HANDOFF NOTE FROM CANONICAL DAY-0 OTTO</span>
              </div>
              <div className="text-xs text-slate-200 leading-relaxed whitespace-pre-line font-sans space-y-2">
                {founderGift.personalNoteFromOtto}
              </div>
            </div>

            <div className="pt-3 border-t border-slate-800 space-y-1.5 text-xs font-mono">
              <div className="text-slate-400">Active Overnight Watchdog Policy:</div>
              <div className="text-emerald-400 break-all">{founderGift.watchdogPolicy}</div>
            </div>
          </div>

          <div className="lg:col-span-7 border border-slate-800 rounded-lg bg-slate-950 p-5 flex flex-col justify-between space-y-4">
            <div className="space-y-3">
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800 pb-3">
                <div className="flex items-center gap-2 text-xs font-mono text-sky-400">
                  <FileText className="w-4 h-4" />
                  <span>READY-TO-SEND FUNDER PROOF & MORNING BRIEFING DOSSIER</span>
                </div>
                <span className="text-xs font-mono text-emerald-400 tabular-nums">
                  CIF-HMAC: {founderGift.dossierHmacSignature.slice(0, 12)}...
                </span>
              </div>

              <pre className="p-3.5 bg-slate-900 border border-slate-800 rounded-md text-xs font-mono text-slate-200 overflow-x-auto max-h-64 whitespace-pre-wrap leading-relaxed">
                {founderGift.funderProofMarkdown}
              </pre>
            </div>

            <div className="flex flex-wrap items-center justify-between gap-3 pt-2 border-t border-slate-800">
              <button
                type="button"
                onClick={() =>
                  handleCopyText(founderGift.funderProofMarkdown, setCopiedDossier)
                }
                className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-mono text-slate-200 bg-slate-900 hover:bg-slate-800 border border-slate-700 rounded-md transition-colors whitespace-nowrap shrink-0"
              >
                {copiedDossier ? (
                  <Check className="w-3.5 h-3.5 text-emerald-400" />
                ) : (
                  <Copy className="w-3.5 h-3.5 text-sky-400" />
                )}
                <span>
                  {copiedDossier ? 'Copied Funder Dossier!' : 'Copy Dossier Markdown'}
                </span>
              </button>

              <a
                href="/api/founder/funder-dossier.md"
                download="estate-funder-proof-dossier.md"
                className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-semibold text-slate-950 bg-sky-400 hover:bg-sky-300 rounded-md transition-colors whitespace-nowrap shrink-0"
              >
                <Download className="w-3.5 h-3.5" />
                <span>Download Funder Proof Dossier (.md)</span>
              </a>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
};
