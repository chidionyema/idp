import React from 'react';
import { ShieldCheck, Wifi, WifiOff, GitCommit, Key, Copy, Check, Server, Terminal } from 'lucide-react';
import { PINNED_RULES_HASH } from '../protocol/rules';

interface HeaderProps {
  isOnline: boolean;
  setIsOnline: (online: boolean) => void;
  activeReceiptCount: number;
  queuedCount: number;
}

export const Header: React.FC<HeaderProps> = ({
  isOnline,
  setIsOnline,
  activeReceiptCount,
  queuedCount,
}) => {
  const [copiedHash, setCopiedHash] = React.useState(false);

  const copyHash = () => {
    navigator.clipboard.writeText(PINNED_RULES_HASH);
    setCopiedHash(true);
    setTimeout(() => setCopiedHash(false), 2000);
  };

  return (
    <header className="border-b border-slate-800 bg-slate-950/80 backdrop-blur sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          {/* Logo & System Identity */}
          <div className="flex items-center space-x-3">
            <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-cyan-600 via-blue-600 to-indigo-600 flex items-center justify-center shadow-lg shadow-cyan-950/50">
              <ShieldCheck className="h-5 w-5 text-white" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h1 className="text-lg font-bold tracking-tight text-white">
                  Estate IDP Protocol & Client Harness
                </h1>
                <span className="text-xs px-2 py-0.5 rounded-full bg-cyan-950 text-cyan-300 border border-cyan-800 font-mono font-medium">
                  CONSULT Harness
                </span>
                <span className="text-[11px] px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 font-mono hidden sm:inline-block">
                  Upstream Mandate: IDP #7771 / #7790
                </span>
              </div>
              <p className="text-xs text-slate-400">
                Observability & Assurance Interface &bull; Invariant Tests &bull; Non-Authoritative Client
              </p>
            </div>
          </div>

          {/* Meta Badges & Network Mode Switcher */}
          <div className="flex flex-wrap items-center gap-2">
            {/* Pinned Rules Hash Badge */}
            <div className="flex items-center space-x-1.5 px-2.5 py-1 rounded-lg bg-slate-900 border border-slate-800 text-xs">
              <Key className="h-3.5 w-3.5 text-cyan-400" />
              <span className="text-slate-400">Rules Hash:</span>
              <span className="font-mono text-cyan-300 font-medium" title={PINNED_RULES_HASH}>
                {PINNED_RULES_HASH.slice(0, 10)}...{PINNED_RULES_HASH.slice(-6)}
              </span>
              <button
                onClick={copyHash}
                aria-label="Copy pinned rules hash"
                className="text-slate-400 hover:text-white transition-colors ml-1 p-0.5"
              >
                {copiedHash ? (
                  <Check className="h-3 w-3 text-emerald-400" />
                ) : (
                  <Copy className="h-3 w-3" />
                )}
              </button>
            </div>

            {/* Offline allowlist badge */}
            <div className="hidden xl:flex items-center space-x-1.5 px-2 py-1 rounded-lg bg-slate-900 border border-slate-800 text-[11px] font-mono text-slate-400">
              <Terminal className="h-3 w-3 text-amber-400" />
              <span>Candidate Offline: [launch, back, home, wait]</span>
            </div>

            {/* Receipts Presence Count */}
            <div className="flex items-center space-x-2 text-xs">
              <span className="px-2 py-1 rounded-md bg-cyan-950/60 border border-cyan-800/80 text-cyan-300 font-mono" title="Canonical Gateway Receipt Presence Guarantee">
                {activeReceiptCount} Receipts Present
              </span>
              {queuedCount > 0 && (
                <span className="px-2 py-1 rounded-md bg-amber-950/60 border border-amber-800/80 text-amber-300 font-mono">
                  {queuedCount} Queued
                </span>
              )}
            </div>

            {/* Connectivity Mode Toggle */}
            <button
              onClick={() => setIsOnline(!isOnline)}
              className={`flex items-center space-x-2 px-3 py-1.5 rounded-lg text-xs font-semibold border transition-all ${
                isOnline
                  ? 'bg-emerald-950/70 border-emerald-700 text-emerald-300 hover:bg-emerald-900/60'
                  : 'bg-rose-950/70 border-rose-700 text-rose-300 hover:bg-rose-900/60'
              }`}
              aria-label={isOnline ? 'Switch to offline mode' : 'Switch to online mode'}
            >
              {isOnline ? (
                <>
                  <Wifi className="h-3.5 w-3.5 text-emerald-400" />
                  <span>ONLINE (CLUSTER)</span>
                </>
              ) : (
                <>
                  <WifiOff className="h-3.5 w-3.5 text-rose-400" />
                  <span>OFFLINE (LOCAL)</span>
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </header>
  );
};
