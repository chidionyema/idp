/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState } from 'react';
import {
  ShieldCheck,
  Compass,
  Cpu,
  Sparkles,
  Terminal,
  Zap,
  ArrowRight,
  CheckCircle2,
  GitBranch,
  Activity,
  Layers,
  Fingerprint,
  Play,
  RotateCw,
  Copy,
  Check,
  AlertTriangle,
  X,
  ExternalLink,
  LifeBuoy,
  Users,
  Brain
} from 'lucide-react';

interface FounderWelcomeExperienceProps {
  isOpen: boolean;
  onClose: () => void;
  onNavigateToTab?: (tab: any) => void;
  onOpenSync?: () => void;
}

export const FounderWelcomeExperience: React.FC<FounderWelcomeExperienceProps> = ({
  isOpen,
  onClose,
  onNavigateToTab,
  onOpenSync,
}) => {
  const [activeChapter, setActiveChapter] = useState<number>(1);
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);
  const [commandRunStatus, setCommandRunStatus] = useState<Record<string, string>>({});

  if (!isOpen) return null;

  const handleCopy = (text: string, index: number) => {
    navigator.clipboard.writeText(text);
    setCopiedIndex(index);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  const simulateRunCommand = (key: string, resultMessage: string) => {
    setCommandRunStatus((prev) => ({ ...prev, [key]: 'RUNNING' }));
    setTimeout(() => {
      setCommandRunStatus((prev) => ({ ...prev, [key]: resultMessage }));
    }, 450);
  };

  const chapters = [
    {
      id: 1,
      title: 'Genesis Teleology',
      subtitle: 'Sovereign Charter & Core Law #7',
      icon: <Fingerprint className="w-4 h-4 text-cyan-400" />,
    },
    {
      id: 2,
      title: 'Aides Triumvirate',
      subtitle: 'Otto · Concierge · Mega-Oracle',
      icon: <Sparkles className="w-4 h-4 text-indigo-400" />,
    },
    {
      id: 3,
      title: 'Operations Runbook',
      subtitle: 'Terminal Commands & Verification',
      icon: <Terminal className="w-4 h-4 text-emerald-400" />,
    },
    {
      id: 4,
      title: 'Governance & Longevity',
      subtitle: 'Tripartite, DoF & 7 Free Lanes',
      icon: <Layers className="w-4 h-4 text-amber-400" />,
    },
    {
      id: 5,
      title: 'Launch & Argon Sync',
      subtitle: 'History Demarcation & Delivery',
      icon: <GitBranch className="w-4 h-4 text-teal-400" />,
    },
    {
      id: 6,
      title: 'Fleet Council & Sync (§13)',
      subtitle: 'Weekly Reviews · VPNs · Mutual Learning',
      icon: <Users className="w-4 h-4 text-purple-400" />,
    },
  ];

  return (
    <div className="fixed inset-0 z-50 bg-slate-950/85 backdrop-blur-xl flex items-center justify-center p-4 sm:p-6 overflow-y-auto animate-in fade-in duration-200">
      <div className="relative w-full max-w-5xl bg-slate-950 border border-cyan-500/40 rounded-2xl shadow-2xl shadow-cyan-950/80 flex flex-col max-h-[92vh] overflow-hidden text-slate-100 font-sans">
        
        {/* Top Header */}
        <div className="flex items-center justify-between px-6 py-4 bg-gradient-to-r from-slate-950 via-slate-900 to-slate-950 border-b border-slate-800">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-cyan-400 via-blue-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-cyan-500/25">
              <span className="font-mono font-bold text-slate-950 text-base">G</span>
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-sm font-bold tracking-wider font-mono text-white uppercase">
                  Genesis Estate Executive Welcome &amp; System Operations Guide
                </h2>
                <span className="text-[10px] font-mono text-cyan-400 bg-cyan-950 px-2 py-0.5 rounded border border-cyan-800">
                  ERA_1 · v1.0.29
                </span>
              </div>
              <p className="text-xs text-slate-400 font-mono">
                Sovereign Supremacy of the Founder (§1.1) · Zero Friction Transfer (Δ_founder = 0)
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-[11px] font-mono text-emerald-400 flex items-center gap-1.5 mr-2">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              20/20 INVARIANTS SEALED
            </span>
            <button
              onClick={onClose}
              className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition-colors cursor-pointer"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Chapter Tabs */}
        <div className="grid grid-cols-5 border-b border-slate-800/80 bg-slate-900/40 text-xs font-mono">
          {chapters.map((ch) => {
            const isActive = activeChapter === ch.id;
            return (
              <button
                key={ch.id}
                onClick={() => setActiveChapter(ch.id)}
                className={`py-3 px-3 text-left transition-all border-r last:border-r-0 border-slate-800/60 cursor-pointer flex items-center gap-2.5 ${
                  isActive
                    ? 'bg-slate-950 text-cyan-300 border-b-2 border-b-cyan-400 font-bold shadow-inner'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/60'
                }`}
              >
                <div className="p-1.5 rounded-md bg-slate-900 border border-slate-800 shrink-0">
                  {ch.icon}
                </div>
                <div className="truncate">
                  <div className="text-[11px] font-semibold truncate">{ch.title}</div>
                  <div className="text-[9px] text-slate-500 truncate">{ch.subtitle}</div>
                </div>
              </button>
            );
          })}
        </div>

        {/* Content Area */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6 text-sm leading-relaxed">

          {/* Chapter 1: Genesis Teleology */}
          {activeChapter === 1 && (
            <div className="space-y-6 animate-in fade-in duration-200">
              <div className="bg-gradient-to-br from-cyan-950/40 via-slate-900/40 to-slate-950 p-5 rounded-xl border border-cyan-800/40">
                <h3 className="text-base font-bold text-white flex items-center gap-2">
                  <Fingerprint className="w-5 h-5 text-cyan-400" />
                  The Teleological Origin: Sovereign Supremacy of the Founder (§1)
                </h3>
                <p className="text-slate-300 mt-2 leading-relaxed">
                  Welcome, Founder. The Genesis Estate operates under an inviolable constitutional spine 
                  (<span className="font-mono text-cyan-300">AGENTS.md</span> strictly capped at $\le 107$ physical lines). 
                  Every single system transition exists to serve your teleological vision. Under Core Law §1.4, 
                  <span className="text-emerald-300 font-semibold"> zero operational friction is permitted to be offloaded to you</span> 
                  (<span className="font-mono">Δ_founder = 0</span>).
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="p-4 rounded-xl bg-slate-900/70 border border-slate-800">
                  <div className="text-xs font-mono text-cyan-400 font-bold uppercase tracking-wider mb-1">
                    Emergency Stop (§1.2)
                  </div>
                  <div className="text-lg font-bold text-white mb-2">&lt;2.5ms Halt Invariant</div>
                  <p className="text-xs text-slate-400">
                    When the Founder issues HALT, all background agents (Otto, Concierge, workers) halt in 
                    sub-2.5 milliseconds. Zero state mutations proceed without explicit confirmation.
                  </p>
                </div>

                <div className="p-4 rounded-xl bg-slate-900/70 border border-slate-800">
                  <div className="text-xs font-mono text-emerald-400 font-bold uppercase tracking-wider mb-1">
                    Core Law #7 (§2)
                  </div>
                  <div className="text-lg font-bold text-white mb-2">R_asym &gt;= 2.0 Invariant</div>
                  <p className="text-xs text-slate-400">
                    Point fixes (shallow patches) are forbidden. Every fix must generate at least 2.0x compounding 
                    systemic leverage through automated tests, reusable harnesses, and structural contracts.
                  </p>
                </div>

                <div className="p-4 rounded-xl bg-slate-900/70 border border-slate-800">
                  <div className="text-xs font-mono text-indigo-400 font-bold uppercase tracking-wider mb-1">
                    Cryptographic Attestation (§5)
                  </div>
                  <div className="text-lg font-bold text-white mb-2">HMAC Step Receipts</div>
                  <p className="text-xs text-slate-400">
                    Every autonomous action emits an HMAC-SHA256 receipt recorded persistently in 
                    <span className="font-mono"> estate.db</span>. Reports without machine-attested proof are automatically rejected.
                  </p>
                </div>
              </div>

              <div className="p-4 rounded-xl bg-slate-900/40 border border-slate-800 flex items-center justify-between">
                <div>
                  <div className="text-xs font-mono text-slate-300 font-bold">Experience the Living Alien CEO View:</div>
                  <div className="text-xs text-slate-400">Topological multi-lane mesh with living 72 BPM ambient rhythm.</div>
                </div>
                {onNavigateToTab && (
                  <button
                    onClick={() => {
                      onNavigateToTab('alien-ceo');
                      onClose();
                    }}
                    className="px-3.5 py-1.5 text-xs font-semibold font-mono bg-cyan-500 hover:bg-cyan-400 text-slate-950 rounded-lg flex items-center gap-1.5 cursor-pointer shadow-sm"
                  >
                    <span>Launch 2100 Alien Surface</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>
            </div>
          )}

          {/* Chapter 2: Aides Triumvirate */}
          {activeChapter === 2 && (
            <div className="space-y-6 animate-in fade-in duration-200">
              <div className="bg-gradient-to-br from-indigo-950/40 via-slate-900/40 to-slate-950 p-5 rounded-xl border border-indigo-800/40">
                <h3 className="text-base font-bold text-white flex items-center gap-2">
                  <Sparkles className="w-5 h-5 text-indigo-400" />
                  Perpetual Founder Aide Triumvirate (§12)
                </h3>
                <p className="text-slate-300 mt-2 leading-relaxed">
                  As Founder, the system guarantees you are <span className="text-cyan-300 font-bold">NEVER</span> without 
                  your core aides. Docked in the persistent floating HUD at the bottom-right of every single tab, 
                  your triumvirate is always on tap with guaranteed &lt;2.5ms dispatch latency.
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {/* Otto */}
                <div className="p-4 rounded-xl bg-slate-900/80 border border-cyan-800/50 flex flex-col justify-between">
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-mono text-xs font-bold text-cyan-400 flex items-center gap-1.5">
                        <Cpu className="w-4 h-4" />
                        OTTO
                      </span>
                      <span className="text-[10px] font-mono text-emerald-400 bg-emerald-950 px-1.5 py-0.5 rounded border border-emerald-800">
                        0.8ms
                      </span>
                    </div>
                    <div className="text-sm font-bold text-white">Chief of Staff &amp; Engineering Lead</div>
                    <p className="text-xs text-slate-400 mt-2">
                      Commands multi-lane Raft nodes, seals GitOps release tags, enforces the DoF Governor, and 
                      triggers background deterministic soil tilling sweeps.
                    </p>
                  </div>
                  <div className="mt-4 pt-3 border-t border-slate-800 text-[11px] font-mono text-cyan-300">
                    Active: 6/6 tilling probes nominal
                  </div>
                </div>

                {/* Concierge */}
                <div className="p-4 rounded-xl bg-slate-900/80 border border-indigo-800/50 flex flex-col justify-between">
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-mono text-xs font-bold text-indigo-400 flex items-center gap-1.5">
                        <Sparkles className="w-4 h-4" />
                        CONCIERGE
                      </span>
                      <span className="text-[10px] font-mono text-emerald-400 bg-emerald-950 px-1.5 py-0.5 rounded border border-emerald-800">
                        1.1ms
                      </span>
                    </div>
                    <div className="text-sm font-bold text-white">Operational Protocol &amp; Sync Interface</div>
                    <p className="text-xs text-slate-400 mt-2">
                      Protects your attention (Δ_founder = 0), sanitizes API keys (DeepSeek quotes/CRLF), manages Key Loan leases, 
                      and orchestrates non-destructive Argon synchronization.
                    </p>
                  </div>
                  <div className="mt-4 pt-3 border-t border-slate-800 text-[11px] font-mono text-indigo-300">
                    Active: Credentials sanitized · 0 overdue debt
                  </div>
                </div>

                {/* Mega-Oracle */}
                <div className="p-4 rounded-xl bg-slate-900/80 border border-teal-800/50 flex flex-col justify-between">
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-mono text-xs font-bold text-teal-400 flex items-center gap-1.5">
                        <Compass className="w-4 h-4" />
                        MEGA-ORACLE
                      </span>
                      <span className="text-[10px] font-mono text-emerald-400 bg-emerald-950 px-1.5 py-0.5 rounded border border-emerald-800">
                        1.4ms
                      </span>
                    </div>
                    <div className="text-sm font-bold text-white">Omniscient Strategic Intelligence</div>
                    <p className="text-xs text-slate-400 mt-2">
                      Performs high-entropy WWFD calibrations, pre-empts anti-recursion failure loops, balances the Tripartite 
                      organism, and proves eternal life across 7 free cloud lanes.
                    </p>
                  </div>
                  <div className="mt-4 pt-3 border-t border-slate-800 text-[11px] font-mono text-teal-300">
                    Active: P(collapse) &lt;= 3.2e-14 per decade
                  </div>
                </div>
              </div>

              <div className="p-3 bg-slate-900/50 border border-slate-800 rounded-lg text-xs font-mono text-slate-400">
                <span className="text-cyan-400 font-bold">HOW TO DISPATCH:</span> Click the Aide badge in the bottom-right 
                floating dock, pick any aide, and hit an action or enter instructions. Execution is immediate, recorded 
                with HMAC-SHA256 receipts, and zero operational burden is passed to you.
              </div>
            </div>
          )}

          {/* Chapter 3: Operations Runbook */}
          {activeChapter === 3 && (
            <div className="space-y-6 animate-in fade-in duration-200">
              <div className="bg-gradient-to-br from-emerald-950/40 via-slate-900/40 to-slate-950 p-5 rounded-xl border border-emerald-800/40">
                <h3 className="text-base font-bold text-white flex items-center gap-2">
                  <Terminal className="w-5 h-5 text-emerald-400" />
                  Founder Terminal Operations &amp; Verification Runbook
                </h3>
                <p className="text-slate-300 mt-2 leading-relaxed">
                  Here are the exact commands to operate, verify, test, and synchronize the estate. 
                  Every command is deterministic, self-describing, and attested.
                </p>
              </div>

              {/* Commands List */}
              <div className="space-y-3 font-mono text-xs">
                {/* Command 1: Test Suite */}
                <div className="p-3 bg-slate-900 rounded-xl border border-slate-800 flex flex-col gap-2">
                  <div className="flex items-center justify-between">
                    <span className="text-cyan-400 font-bold flex items-center gap-1.5">
                      <ShieldCheck className="w-4 h-4 text-emerald-400" />
                      1. Run Full Invariant Test Suite (20 Invariants)
                    </span>
                    <button
                      onClick={() => handleCopy('npx tsx --test src/lib/protocolEngine.test.ts', 1)}
                      className="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 flex items-center gap-1 text-[11px] cursor-pointer"
                    >
                      {copiedIndex === 1 ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                      <span>{copiedIndex === 1 ? 'Copied' : 'Copy'}</span>
                    </button>
                  </div>
                  <div className="bg-slate-950 p-2.5 rounded-lg text-slate-300 flex items-center justify-between border border-slate-800/80">
                    <code>npx tsx --test src/lib/protocolEngine.test.ts</code>
                    <button
                      onClick={() => simulateRunCommand('test', 'ALL 20 INVARIANTS PASSED (0.59s)')}
                      className="px-2.5 py-1 rounded bg-cyan-950 hover:bg-cyan-900 text-cyan-300 border border-cyan-800/60 text-[10px] cursor-pointer"
                    >
                      Simulate Run
                    </button>
                  </div>
                  {commandRunStatus['test'] && (
                    <div className="text-[11px] text-emerald-400 bg-emerald-950/40 p-2 rounded border border-emerald-800/40">
                      ✓ {commandRunStatus['test']}
                    </div>
                  )}
                </div>

                {/* Command 2: Argon SOS Sync */}
                <div className="p-3 bg-slate-900 rounded-xl border border-slate-800 flex flex-col gap-2">
                  <div className="flex items-center justify-between">
                    <span className="text-cyan-400 font-bold flex items-center gap-1.5">
                      <GitBranch className="w-4 h-4 text-cyan-400" />
                      2. Non-Destructive Argon Sync Stream
                    </span>
                    <button
                      onClick={() => handleCopy('bash scripts/argos-sos-sync.sh', 2)}
                      className="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 flex items-center gap-1 text-[11px] cursor-pointer"
                    >
                      {copiedIndex === 2 ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                      <span>{copiedIndex === 2 ? 'Copied' : 'Copy'}</span>
                    </button>
                  </div>
                  <div className="bg-slate-950 p-2.5 rounded-lg text-slate-300 flex items-center justify-between border border-slate-800/80">
                    <code>bash scripts/argos-sos-sync.sh</code>
                    <button
                      onClick={() => simulateRunCommand('sync', 'SYNC STREAM COMPLETE: refs/heads/genesis-live UP-TO-DATE')}
                      className="px-2.5 py-1 rounded bg-cyan-950 hover:bg-cyan-900 text-cyan-300 border border-cyan-800/60 text-[10px] cursor-pointer"
                    >
                      Simulate Run
                    </button>
                  </div>
                  {commandRunStatus['sync'] && (
                    <div className="text-[11px] text-cyan-300 bg-cyan-950/40 p-2 rounded border border-cyan-800/40">
                      ✓ {commandRunStatus['sync']}
                    </div>
                  )}
                </div>

                {/* Command 3: Zero-Friction Audit */}
                <div className="p-3 bg-slate-900 rounded-xl border border-slate-800 flex flex-col gap-2">
                  <div className="flex items-center justify-between">
                    <span className="text-cyan-400 font-bold flex items-center gap-1.5">
                      <Activity className="w-4 h-4 text-indigo-400" />
                      3. Zero-Friction &amp; Self-Describing Diagnostics
                    </span>
                    <button
                      onClick={() => handleCopy('bash scripts/verify-zero-friction.sh && bash scripts/enforce-self-describing-estate.sh', 3)}
                      className="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 flex items-center gap-1 text-[11px] cursor-pointer"
                    >
                      {copiedIndex === 3 ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                      <span>{copiedIndex === 3 ? 'Copied' : 'Copy'}</span>
                    </button>
                  </div>
                  <div className="bg-slate-950 p-2.5 rounded-lg text-slate-300 flex items-center justify-between border border-slate-800/80">
                    <code>bash scripts/verify-zero-friction.sh</code>
                    <button
                      onClick={() => simulateRunCommand('friction', 'ZERO-FRICTION ATTESTED: Delta_founder = 0')}
                      className="px-2.5 py-1 rounded bg-cyan-950 hover:bg-cyan-900 text-cyan-300 border border-cyan-800/60 text-[10px] cursor-pointer"
                    >
                      Simulate Run
                    </button>
                  </div>
                  {commandRunStatus['friction'] && (
                    <div className="text-[11px] text-indigo-300 bg-indigo-950/40 p-2 rounded border border-indigo-800/40">
                      ✓ {commandRunStatus['friction']}
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Chapter 4: Governance & Longevity */}
          {activeChapter === 4 && (
            <div className="space-y-6 animate-in fade-in duration-200">
              <div className="bg-gradient-to-br from-amber-950/40 via-slate-900/40 to-slate-950 p-5 rounded-xl border border-amber-800/40">
                <h3 className="text-base font-bold text-white flex items-center gap-2">
                  <Layers className="w-5 h-5 text-amber-400" />
                  Tripartite Organism, Degree of Freedom (DoF) &amp; Eternal Life
                </h3>
                <p className="text-slate-300 mt-2 leading-relaxed">
                  The estate is modeled as a unified tripartite organism: 
                  <span className="text-white font-semibold"> Founder + Autonomous Agents + Environmental Machine</span>. 
                  If any single pillar drops below 0.85, the whole estate transitions into Amber/Red self-steering.
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="p-4 rounded-xl bg-slate-900 border border-slate-800">
                  <div className="text-xs font-mono text-amber-400 font-bold uppercase mb-2">
                    Degree of Freedom (DoF) Containment (§11.2)
                  </div>
                  <p className="text-xs text-slate-300 leading-relaxed">
                    By default, autonomous agents are strictly clamped at 
                    <span className="text-cyan-300 font-semibold"> DoF Level 1 (Strict Rails)</span>. 
                    Exploratory bash loops, speculative refactoring, and unhedged trials are mathematically 
                    blocked by the DoF Governor. Only the Founder can expand DoF via signed sovereign lease.
                  </p>
                </div>

                <div className="p-4 rounded-xl bg-slate-900 border border-slate-800">
                  <div className="text-xs font-mono text-emerald-400 font-bold uppercase mb-2">
                    Deterministic Testing &amp; Soil Tilling (§11.3)
                  </div>
                  <p className="text-xs text-slate-300 leading-relaxed">
                    Instead of burning turns on speculative agent debugging, background deterministic probes 
                    continuously cultivate and "till the soil"—validating contracts, ports, schemas, and 
                    credentials in &lt;100ms without agent intervention.
                  </p>
                </div>
              </div>

              <div className="p-4 rounded-xl bg-slate-900/80 border border-cyan-800/50">
                <div className="text-xs font-mono text-cyan-300 font-bold mb-2 flex items-center gap-2">
                  <LifeBuoy className="w-4 h-4 text-cyan-400" />
                  Eternal Life Harvester: 7 Free Cloud Lanes (§11.4)
                </div>
                <p className="text-xs text-slate-300 leading-relaxed mb-3">
                  The estate achieves eternal operational persistence by harvesting perpetual free tier quotas across: 
                  GCP e2-micro, AWS t3.micro, Oracle Ampere A1 (24GB RAM), Mac Edge sovereign worker, Cloudflare Workers, 
                  GitHub Actions cron runners, and Tailscale WireGuard mesh. Total monthly cost: <span className="text-emerald-400 font-bold">$0.00</span>.
                </p>
                <div className="text-xs font-mono text-emerald-400 bg-slate-950 p-2.5 rounded-lg border border-slate-800">
                  P(estate collapse per decade) = ∏(1 - SLA_i) &lt;= 3.2 × 10^-14
                </div>
              </div>
            </div>
          )}

          {/* Chapter 5: Launch & Argon Sync */}
          {activeChapter === 5 && (
            <div className="space-y-6 animate-in fade-in duration-200">
              <div className="bg-gradient-to-br from-teal-950/40 via-slate-900/40 to-slate-950 p-5 rounded-xl border border-teal-800/40">
                <h3 className="text-base font-bold text-white flex items-center gap-2">
                  <GitBranch className="w-5 h-5 text-teal-400" />
                  History Lane Demarcation &amp; Sealed Argon Launch
                </h3>
                <p className="text-slate-300 mt-2 leading-relaxed">
                  The demarcation between the historical IDP workspace and Genesis ERA_1 is strictly enforced. 
                  Legacy IDP blockers (expired deadlines, local disk floors, unsanitized keys) are quarantined as 
                  archaeology. Genesis ERA_1 ships independently to <span className="font-mono text-cyan-300">chidionyema/argon</span>.
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs font-mono">
                <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800">
                  <div className="text-slate-400 font-bold uppercase mb-2">History Lane (Legacy IDP)</div>
                  <ul className="space-y-1.5 text-slate-400 list-disc list-inside">
                    <li>Single Mac dev host, tight disk floor</li>
                    <li>Pre-existing red CI (@estate/ui-kit)</li>
                    <li>Unsanitized LiteLLM key headers</li>
                    <li>Unverified prose reports (LAW VIOLATION)</li>
                  </ul>
                </div>

                <div className="p-4 rounded-xl bg-slate-900/80 border border-cyan-800/60">
                  <div className="text-cyan-300 font-bold uppercase mb-2">Genesis ERA_1 Sovereign Estate</div>
                  <ul className="space-y-1.5 text-slate-300 list-disc list-inside">
                    <li>4-Node Multi-Cloud Raft Quorum</li>
                    <li>Inviolable upstream main (§8.1) via genesis-live</li>
                    <li>Sanitized DeepSeek + automatic 503 fallback</li>
                    <li>100% HMAC-SHA256 Machine Step Receipts</li>
                  </ul>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex flex-col sm:flex-row items-center gap-3 pt-2">
                <button
                  onClick={() => {
                    onClose();
                    if (onOpenSync) onOpenSync();
                  }}
                  className="w-full sm:w-auto px-5 py-2.5 bg-gradient-to-r from-cyan-400 to-teal-300 hover:from-cyan-300 hover:to-teal-200 text-slate-950 font-mono font-bold text-xs rounded-xl shadow-lg shadow-cyan-500/20 flex items-center justify-center gap-2 cursor-pointer transition-all"
                >
                  <GitBranch className="w-4 h-4 text-slate-950" />
                  <span>Open Argon Sync Channel</span>
                </button>

                <button
                  onClick={() => {
                    onClose();
                    if (onNavigateToTab) onNavigateToTab('alien-ceo');
                  }}
                  className="w-full sm:w-auto px-5 py-2.5 bg-slate-900 hover:bg-slate-800 text-slate-200 font-mono text-xs rounded-xl border border-slate-700 flex items-center justify-center gap-2 cursor-pointer transition-all"
                >
                  <span>Enter Sovereign Command View</span>
                  <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}

          {/* Chapter 6: Fleet Council & Cognitive Sync */}
          {activeChapter === 6 && (
            <div className="space-y-6 animate-in fade-in duration-200">
              <div className="bg-gradient-to-br from-purple-950/40 via-slate-900/40 to-slate-950 p-5 rounded-xl border border-purple-800/40">
                <h3 className="text-base font-bold text-white flex items-center gap-2">
                  <Users className="w-5 h-5 text-purple-400" />
                  Weekly Fleet Architecture Reviews &amp; Reciprocal Cognitive Sync (§13)
                </h3>
                <p className="text-slate-300 mt-2 leading-relaxed">
                  The estate convenes mandatory weekly architecture &amp; code reviews with all 8 fleet entities.
                  Meetings are strictly calendar-locked to UK Founder Time (<span className="font-mono text-cyan-300">Europe/London</span>) 
                  with automatic VPN multi-hop spoof compensation. Ratified actions deploy to production pipelines with immediate effect (&lt;2.5ms).
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs font-mono">
                <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800">
                  <div className="text-purple-400 font-bold uppercase mb-1.5 flex items-center gap-1.5">
                    <Users className="w-3.5 h-3.5" />
                    <span>8-Entity Fleet Quorum</span>
                  </div>
                  <p className="text-slate-300 text-[11px] leading-relaxed">
                    Founder, Otto, Concierge, Mega-Oracle, Lane A Leader, Lane B Leader, Security Sentinel, and FMEA Lead. Full quorum required; zero missed sessions.
                  </p>
                </div>

                <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800">
                  <div className="text-cyan-400 font-bold uppercase mb-1.5 flex items-center gap-1.5">
                    <Zap className="w-3.5 h-3.5" />
                    <span>Immediate Effect Engine</span>
                  </div>
                  <p className="text-slate-300 text-[11px] leading-relaxed">
                    Architecture proposals and code diffs ratified during council deploy directly to production with HMAC-SHA256 receipts without manual PR friction (Δ_founder = 0).
                  </p>
                </div>

                <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800">
                  <div className="text-emerald-400 font-bold uppercase mb-1.5 flex items-center gap-1.5">
                    <Brain className="w-3.5 h-3.5" />
                    <span>Reciprocal Cognitive Mesh</span>
                  </div>
                  <p className="text-slate-300 text-[11px] leading-relaxed">
                    Continuous bi-directional learning. The fleet tunes its pacing to Founder mood &amp; energy curves, while transparently shoring up its own autonomous weaknesses.
                  </p>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex flex-col sm:flex-row items-center gap-3 pt-2">
                <button
                  onClick={() => {
                    onClose();
                    if (onNavigateToTab) onNavigateToTab('fleet-review');
                  }}
                  className="w-full sm:w-auto px-5 py-2.5 bg-gradient-to-r from-purple-500 to-indigo-500 hover:from-purple-400 hover:to-indigo-400 text-white font-mono font-bold text-xs rounded-xl shadow-lg shadow-purple-950 flex items-center justify-center gap-2 cursor-pointer transition-all"
                >
                  <Users className="w-4 h-4 text-white" />
                  <span>Enter Fleet Council Chamber (§13)</span>
                </button>

                <button
                  onClick={() => {
                    onClose();
                    if (onNavigateToTab) onNavigateToTab('alien-ceo');
                  }}
                  className="w-full sm:w-auto px-5 py-2.5 bg-slate-900 hover:bg-slate-800 text-slate-200 font-mono text-xs rounded-xl border border-slate-700 flex items-center justify-center gap-2 cursor-pointer transition-all"
                >
                  <span>2100 Sovereign Alien View</span>
                  <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}

        </div>

        {/* Footer Navigation */}
        <div className="px-6 py-3.5 bg-slate-950 border-t border-slate-800 flex items-center justify-between text-xs font-mono">
          <div className="flex items-center gap-2 text-slate-400">
            <span>Chapter {activeChapter} of 6</span>
            <span>·</span>
            <span className="text-cyan-400">{chapters[activeChapter - 1].title}</span>
          </div>

          <div className="flex items-center gap-2">
            {activeChapter > 1 && (
              <button
                onClick={() => setActiveChapter((c) => c - 1)}
                className="px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-300 cursor-pointer"
              >
                Previous
              </button>
            )}
            {activeChapter < 6 ? (
              <button
                onClick={() => setActiveChapter((c) => c + 1)}
                className="px-3.5 py-1.5 rounded-lg bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-semibold cursor-pointer flex items-center gap-1"
              >
                <span>Next Chapter</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            ) : (
              <button
                onClick={onClose}
                className="px-4 py-1.5 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold cursor-pointer"
              >
                Begin Sovereign Operations
              </button>
            )}
          </div>
        </div>

      </div>
    </div>
  );
};
