import React, { useState } from 'react';
import {
  Radio,
  ShieldAlert,
  Vote,
  Globe,
  Terminal,
  Copy,
  Check,
  PlusCircle,
  Zap,
  FileCode2,
} from 'lucide-react';
import {
  OneBrainFederationState,
  AgentSurfaceCategory,
  AgentTransportMechanism,
  CreditDependencyMode,
} from '../engine/oneBrainEngine';

interface OneBrainFederationPanelProps {
  brainState: OneBrainFederationState;
  sseConnected: boolean;
  onSendFounderSteer: (directiveText: string, targetSurfaces?: string) => void;
  onCastCouncilVote: (input: {
    motionId: string;
    surfaceId: string;
    decision: 'APPROVE' | 'AMEND' | 'VETO';
    rationale: string;
  }) => void;
  onToggleZeroCreditLifeboat: (enable?: boolean) => void;
  onPlugInNewSurface: (input: {
    surfaceName: string;
    modelBackbone: string;
    category: AgentSurfaceCategory;
    transport: AgentTransportMechanism;
    creditMode: CreditDependencyMode;
  }) => void;
}

export const OneBrainFederationPanel: React.FC<OneBrainFederationPanelProps> = ({
  brainState,
  sseConnected,
  onSendFounderSteer,
  onCastCouncilVote,
  onToggleZeroCreditLifeboat,
  onPlugInNewSurface,
}) => {
  const [steerInput, setSteerInput] = useState(
    'Lock Direct MiniMax-M2.7 on Otto first, ban Python LiteLLM across all checkouts, and keep DeepSeek/Kimi/Grok Web Lifeboats on hot standby.'
  );
  const [steerTarget, setSteerTarget] = useState<string>('ALL_SURFACES');
  const [voteSurfaceId, setVoteSurfaceId] = useState<string>('surf-claude-code-desktop');
  const [voteDecision, setVoteDecision] = useState<'APPROVE' | 'AMEND' | 'VETO'>('APPROVE');
  const [voteRationale, setVoteRationale] = useState<string>(
    'Verified polyglot CLAUDE.md/AGENTS.md sync & zero-credit DeepSeek/Kimi Web lifeboat relay.'
  );

  // Plug-in new model/website/app state
  const [newSurfaceName, setNewSurfaceName] = useState('Meta Muse / Grok-3 Web Agent');
  const [newBackbone, setNewBackbone] = useState('Meta Muse + Grok-3 Real-Time Web');
  const [newCategory, setNewCategory] = useState<AgentSurfaceCategory>('web_zero_credit_lifeboat');
  const [newTransport, setNewTransport] = useState<AgentTransportMechanism>('BROWSER_USERSCRIPT_SIDECAR');
  const [newCreditMode, setNewCreditMode] = useState<CreditDependencyMode>('ZERO_API_CREDIT_FREE_WEB');

  const [showPolyglotModal, setShowPolyglotModal] = useState<boolean>(false);
  const [copiedCapsule, setCopiedCapsule] = useState<boolean>(false);
  const [copiedMd, setCopiedMd] = useState<boolean>(false);
  const [steerBanner, setSteerBanner] = useState<string | null>(null);

  const activeMotion = brainState.councilMotions[0];
  const freeLifeboatCount = brainState.surfaces.filter(
    (s) => s.canServeAsZeroCreditLifeboat
  ).length;

  const handleSteerSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!steerInput.trim()) return;
    onSendFounderSteer(steerInput, steerTarget);
    setSteerBanner(
      `Broadcasted Founder Steering Override to ${
        steerTarget === 'ALL_SURFACES'
          ? `all ${brainState.surfaces.length} connected surfaces`
          : steerTarget
      } via /api/brain/steer.`
    );
  };

  const handleVoteSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeMotion) return;
    onCastCouncilVote({
      motionId: activeMotion.motionId,
      surfaceId: voteSurfaceId,
      decision: voteDecision,
      rationale: voteRationale,
    });
  };

  const handleAddSurfaceSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newSurfaceName.trim()) return;
    onPlugInNewSurface({
      surfaceName: newSurfaceName,
      modelBackbone: newBackbone,
      category: newCategory,
      transport: newTransport,
      creditMode: newCreditMode,
    });
  };

  return (
    <section
      aria-label="Asymmetric One-Brain Federation & Live Founder Steering"
      className="bg-white border-2 border-slate-900 rounded-xl p-6 shadow-xs space-y-6"
    >
      {/* Top Header & Zero-Credit Lifeboat Toggle */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 border-b border-slate-200 pb-4">
        <div className="space-y-1">
          <div className="flex flex-wrap items-center gap-2 text-xs font-mono">
            <span className="font-bold text-slate-900 flex items-center gap-1.5">
              <Radio className="w-3.5 h-3.5 text-emerald-600" />
              ASYMMETRIC ONE-BRAIN FEDERATION BUS · PROTOCOL GEN-NET-006
            </span>
            <span aria-hidden="true" className="text-slate-300">·</span>
            <span className="text-emerald-700 font-semibold">
              {sseConnected ? '● LIVE SSE STREAM (/api/brain/stream)' : '● HTTP SYNC ACTIVE'}
            </span>
            <span aria-hidden="true" className="text-slate-300">·</span>
            <span className="text-slate-600">
              Epoch: <strong>{brainState.federationEpochId}</strong> (Legacy IDP Banned)
            </span>
            <span aria-hidden="true" className="text-slate-300">·</span>
            <span className="text-slate-600">
              Rev: <strong>{brainState.canonicalRevisionHash.slice(0, 12)}</strong>
            </span>
          </div>
          <h2 className="text-xl font-bold text-slate-900">
            One-Brain Cross-Surface Mesh, Real-Time Council Quorum &amp; Zero-Credit Web/App Lifeboat
          </h2>
          <p className="text-xs text-slate-600 leading-relaxed">
            Connects <strong>AI Studio</strong>, <strong>Codex Desktop</strong>, <strong>Claude Code Desktop</strong>, <strong>Kimi</strong>, <strong>Otto Mac Daemon</strong>, and <strong>Free Web/App Models (DeepSeek Web, Grok, Meta Muse, Z.ai)</strong> into a single shared brain via polyglot{' '}
            <code className="font-mono bg-slate-100 px-1 py-0.5 rounded">AGENTS.md / CLAUDE.md / .agent.md</code>, live{' '}
            <code className="font-mono bg-slate-100 px-1 py-0.5 rounded">/api/brain/*</code> heartbeats, and Browser Userscript Sidecars—eliminating manual Founder relay and providing a{' '}
            <strong>£0-API-Credit Web Lifeboat</strong> if metered API wallets ever run dry.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2.5 shrink-0">
          <button
            type="button"
            onClick={() => setShowPolyglotModal(true)}
            className="px-3.5 py-2 text-xs font-semibold text-slate-800 bg-slate-100 hover:bg-slate-200 border border-slate-300 rounded-lg transition-colors cursor-pointer inline-flex items-center gap-1.5"
          >
            <FileCode2 className="w-3.5 h-3.5" />
            Inspect Polyglot AGENTS.md &amp; Web Capsule
          </button>

          <button
            type="button"
            onClick={() => onToggleZeroCreditLifeboat()}
            className={`px-4 py-2 text-xs font-semibold rounded-lg transition-colors cursor-pointer inline-flex items-center gap-1.5 ${
              brainState.zeroCreditLifeboatModeActive
                ? 'bg-amber-600 hover:bg-amber-700 text-white'
                : 'bg-slate-900 hover:bg-slate-800 text-white'
            }`}
          >
            <Zap className="w-3.5 h-3.5" />
            {brainState.zeroCreditLifeboatModeActive
              ? 'Zero-Credit Web Lifeboat: ACTIVE (£0 API Spend)'
              : `Activate Zero-Credit Web Lifeboat (${freeLifeboatCount} Free Web Models Ready)`}
          </button>
        </div>
      </div>

      {/* Live Founder Steering Override Bar (Instant Cross-Surface Alignment) */}
      <form
        onSubmit={handleSteerSubmit}
        className="bg-slate-900 text-white rounded-xl p-4 space-y-3"
      >
        <div className="flex flex-wrap items-center justify-between gap-2 text-xs font-mono">
          <span className="text-emerald-400 font-bold flex items-center gap-1.5">
            <ShieldAlert className="w-4 h-4" />
            REAL-TIME FOUNDER STEERING OVERRIDE (/api/brain/steer) · ZERO COPY-PASTE RELAY
          </span>
          <span className="text-slate-300">
            Last Steer Receipt: {brainState.steeringHistory[0]?.receiptHash} ({brainState.steeringHistory[0]?.acknowledgedByCount}/{brainState.steeringHistory[0]?.totalSurfacesCount} Surfaces ACK)
          </span>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-2.5">
          <div className="lg:col-span-7">
            <input
              type="text"
              value={steerInput}
              onChange={(e) => setSteerInput(e.target.value)}
              placeholder="Broadcast a steering directive to immediately align all confused or drifted agents..."
              className="w-full px-3 py-2 text-xs bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-400"
            />
          </div>
          <div className="lg:col-span-3">
            <select
              value={steerTarget}
              onChange={(e) => setSteerTarget(e.target.value)}
              className="w-full px-3 py-2 text-xs bg-slate-800 border border-slate-700 rounded-lg text-white"
            >
              <option value="ALL_SURFACES">Broadcast to All {brainState.surfaces.length} Surfaces</option>
              {brainState.surfaces.map((s) => (
                <option key={s.surfaceId} value={s.surfaceId}>
                  Steer Only: {s.surfaceName}
                </option>
              ))}
            </select>
          </div>
          <div className="lg:col-span-2">
            <button
              type="submit"
              className="w-full px-3 py-2 text-xs font-bold text-slate-950 bg-emerald-400 hover:bg-emerald-300 rounded-lg transition-colors cursor-pointer"
            >
              Broadcast Steer
            </button>
          </div>
        </div>

        {steerBanner && (
          <div className="text-xs font-mono text-emerald-300 bg-slate-800/90 border border-emerald-500/40 rounded-lg px-3 py-1.5">
            ✓ {steerBanner}
          </div>
        )}
      </form>

      {/* Connected Agent Surfaces Heartbeat Matrix (Desktop, CLI, Cloud & Free Web Lifeboats) */}
      <div className="space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
          <span className="font-bold uppercase tracking-wider text-slate-900">
            Connected One-Brain Agent Surfaces ({brainState.surfaces.length} Active Heartbeats Across Cloud, Mac Desktop, CLI &amp; Web)
          </span>
          <span className="font-mono text-emerald-700 font-semibold">
            100% Epoch Demarcated (t &gt;= 2026-11-03) · {freeLifeboatCount} Zero-Credit Web/App Lifeboats Bound
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
          {brainState.surfaces.map((surf) => {
            const isWebLifeboat = surf.category === 'web_zero_credit_lifeboat';
            return (
              <div
                key={surf.surfaceId}
                className={`border rounded-xl p-3.5 flex flex-col justify-between space-y-2.5 ${
                  brainState.zeroCreditLifeboatModeActive && isWebLifeboat
                    ? 'bg-amber-50/70 border-amber-400'
                    : 'bg-slate-50/70 border-slate-200'
                }`}
              >
                <div className="space-y-1">
                  <div className="flex items-center justify-between text-[11px] font-mono">
                    <span className="text-slate-500 flex items-center gap-1">
                      {isWebLifeboat ? (
                        <Globe className="w-3 h-3 text-slate-600" />
                      ) : (
                        <Terminal className="w-3 h-3 text-slate-600" />
                      )}
                      {surf.configFileRead}
                    </span>
                    <span
                      className={`font-bold ${
                        surf.status === 'ONLINE_SYNCED'
                          ? 'text-emerald-700'
                          : 'text-amber-700'
                      }`}
                    >
                      {surf.status}
                    </span>
                  </div>
                  <div className="text-xs font-bold text-slate-900 leading-snug">
                    {surf.surfaceName}
                  </div>
                  <div className="text-[11px] font-mono text-slate-600">
                    {surf.modelBackbone}
                  </div>
                  <p className="text-[11px] text-slate-600 leading-relaxed pt-0.5">
                    {surf.currentActivity}
                  </p>
                </div>

                <div className="pt-2 border-t border-slate-200/80 space-y-1 text-[10px] font-mono">
                  <div className="flex items-center justify-between">
                    <span className="text-slate-500">Transport:</span>
                    <span className="text-slate-900 font-semibold">{surf.transport}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-slate-500">Credit Mode:</span>
                    <span
                      className={`font-semibold ${
                        surf.creditMode === 'ZERO_API_CREDIT_FREE_WEB'
                          ? 'text-emerald-700'
                          : 'text-slate-900'
                      }`}
                    >
                      {surf.creditMode}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-slate-500">Synced Rev / Ping:</span>
                    <span className="text-slate-900">
                      {surf.SyncedRevisionHash.slice(0, 8)} · {surf.heartbeatLatencyMs}ms
                    </span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Bottom 2-Column Grid: Live Multi-Agent Council Voting Room + Plug-In Any New Model/Web Surface */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 pt-2 border-t border-slate-200">
        {/* Left 7 cols: Real-Time Multi-Agent Council Quorum & Shared Review Room */}
        <div className="lg:col-span-7 space-y-3">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-xs font-mono uppercase tracking-wider text-slate-500">
                REAL-TIME MULTI-AGENT COUNCIL PARLIAMENT · /api/brain/council/vote
              </div>
              <h3 className="text-sm font-bold text-slate-900 flex items-center gap-1.5 mt-0.5">
                <Vote className="w-4 h-4 text-slate-700" />
                Active Shared Review &amp; Quorum Motion ({activeMotion?.motionId})
              </h3>
            </div>
            <span className="text-xs font-mono font-bold text-emerald-700 bg-emerald-50 border border-emerald-200 px-2.5 py-1 rounded-lg">
              {activeMotion?.status} · {activeMotion?.approvalPct}% Quorum
            </span>
          </div>

          {activeMotion && (
            <div className="border border-slate-200 rounded-xl p-3.5 bg-slate-50/70 space-y-3">
              <div className="text-xs font-bold text-slate-900">
                {activeMotion.title}
              </div>
              <div className="text-[11px] text-slate-600 font-mono">
                {activeMotion.resolutionSummary}
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {activeMotion.ballots.map((b) => (
                  <div
                    key={b.surfaceId}
                    className="bg-white border border-slate-200 rounded-lg p-2.5 text-[11px] space-y-1"
                  >
                    <div className="flex items-center justify-between font-mono">
                      <span className="font-bold text-slate-900">{b.surfaceName}</span>
                      <span
                        className={`font-bold ${
                          b.decision === 'APPROVE'
                            ? 'text-emerald-700'
                            : b.decision === 'AMEND'
                            ? 'text-amber-700'
                            : 'text-rose-700'
                        }`}
                      >
                        {b.decision}
                      </span>
                    </div>
                    <p className="text-slate-600 leading-snug">{b.rationale}</p>
                    <div className="text-[10px] font-mono text-slate-400">
                      Sig: {b.signatureHash}
                    </div>
                  </div>
                ))}
              </div>

              {/* Cast Live Council Vote from Any Surface */}
              <form
                onSubmit={handleVoteSubmit}
                className="pt-2 border-t border-slate-200 grid grid-cols-1 sm:grid-cols-12 gap-2"
              >
                <div className="sm:col-span-4">
                  <select
                    value={voteSurfaceId}
                    onChange={(e) => setVoteSurfaceId(e.target.value)}
                    className="w-full px-2.5 py-1.5 text-xs bg-white border border-slate-300 rounded-lg"
                  >
                    {brainState.surfaces.map((s) => (
                      <option key={s.surfaceId} value={s.surfaceId}>
                        {s.surfaceName}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="sm:col-span-2">
                  <select
                    value={voteDecision}
                    onChange={(e) =>
                      setVoteDecision(e.target.value as 'APPROVE' | 'AMEND' | 'VETO')
                    }
                    className="w-full px-2 py-1.5 text-xs font-mono bg-white border border-slate-300 rounded-lg"
                  >
                    <option value="APPROVE">APPROVE</option>
                    <option value="AMEND">AMEND</option>
                    <option value="VETO">VETO</option>
                  </select>
                </div>
                <div className="sm:col-span-4">
                  <input
                    type="text"
                    value={voteRationale}
                    onChange={(e) => setVoteRationale(e.target.value)}
                    placeholder="Vote rationale..."
                    className="w-full px-2.5 py-1.5 text-xs bg-white border border-slate-300 rounded-lg"
                  />
                </div>
                <div className="sm:col-span-2">
                  <button
                    type="submit"
                    className="w-full px-2.5 py-1.5 text-xs font-semibold text-white bg-slate-900 hover:bg-slate-800 rounded-lg cursor-pointer"
                  >
                    Cast Vote
                  </button>
                </div>
              </form>
            </div>
          )}
        </div>

        {/* Right 5 cols: Plug-In Any New Model Website, App, or CLI Harness */}
        <div className="lg:col-span-5 bg-slate-50 border border-slate-200 rounded-xl p-4 space-y-3">
          <div>
            <div className="text-xs font-mono uppercase tracking-wider text-slate-500">
              ASYMMETRIC EXTENSIBILITY · /api/brain/heartbeat
            </div>
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-1.5 mt-0.5">
              <PlusCircle className="w-4 h-4 text-slate-700" />
              Plug In Any New Model Website, Desktop App or Bot (Grok, Meta Muse, Z.ai, etc.)
            </h3>
            <p className="text-xs text-slate-600 mt-0.5">
              Register any new web model, mobile app, or CLI harness into the One-Brain Federation so it receives live heartbeats, votes in Council, and serves as a zero-credit lifeboat.
            </p>
          </div>

          <form onSubmit={handleAddSurfaceSubmit} className="space-y-2.5">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              <div>
                <label className="block text-[11px] font-semibold text-slate-700 mb-0.5">
                  Surface / App Name
                </label>
                <input
                  type="text"
                  value={newSurfaceName}
                  onChange={(e) => setNewSurfaceName(e.target.value)}
                  className="w-full px-2.5 py-1.5 text-xs bg-white border border-slate-300 rounded-lg"
                />
              </div>
              <div>
                <label className="block text-[11px] font-semibold text-slate-700 mb-0.5">
                  Model Backbone
                </label>
                <input
                  type="text"
                  value={newBackbone}
                  onChange={(e) => setNewBackbone(e.target.value)}
                  className="w-full px-2.5 py-1.5 text-xs bg-white border border-slate-300 rounded-lg"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
              <div>
                <label className="block text-[11px] font-semibold text-slate-700 mb-0.5">
                  Surface Class
                </label>
                <select
                  value={newCategory}
                  onChange={(e) => setNewCategory(e.target.value as AgentSurfaceCategory)}
                  className="w-full px-2 py-1.5 text-xs bg-white border border-slate-300 rounded-lg"
                >
                  <option value="web_zero_credit_lifeboat">Free Web / App Lifeboat</option>
                  <option value="mac_desktop_app">Mac Desktop App</option>
                  <option value="mac_cli_daemon">Mac CLI / Harness</option>
                  <option value="cloud_sandbox_ide">Cloud Sandbox</option>
                </select>
              </div>
              <div>
                <label className="block text-[11px] font-semibold text-slate-700 mb-0.5">
                  Transport Bridge
                </label>
                <select
                  value={newTransport}
                  onChange={(e) => setNewTransport(e.target.value as AgentTransportMechanism)}
                  className="w-full px-2 py-1.5 text-xs bg-white border border-slate-300 rounded-lg"
                >
                  <option value="BROWSER_USERSCRIPT_SIDECAR">Browser Userscript Sidecar</option>
                  <option value="URL_FETCH_CAPSULE">URL Fetch / Capsule</option>
                  <option value="LOCAL_DAEMON_SYNC_MD">Local AGENTS.md Sync</option>
                  <option value="HTTP_SSE_DIRECT">Direct HTTP + SSE</option>
                </select>
              </div>
              <div>
                <label className="block text-[11px] font-semibold text-slate-700 mb-0.5">
                  Credit Dependency
                </label>
                <select
                  value={newCreditMode}
                  onChange={(e) => setNewCreditMode(e.target.value as CreditDependencyMode)}
                  className="w-full px-2 py-1.5 text-xs bg-white border border-slate-300 rounded-lg"
                >
                  <option value="ZERO_API_CREDIT_FREE_WEB">£0 Free Web Session</option>
                  <option value="FLAT_RATE_SUBSCRIPTION">Flat-Rate Subscription</option>
                  <option value="METERED_API_WALLET">Metered API Wallet</option>
                </select>
              </div>
            </div>

            <button
              type="submit"
              className="w-full px-4 py-2 text-xs font-semibold text-white bg-slate-900 hover:bg-slate-800 rounded-lg transition-colors cursor-pointer"
            >
              Connect Surface to One-Brain Mesh &amp; Start Heartbeat
            </button>
          </form>
        </div>
      </div>

      {/* Modal: Polyglot AGENTS.md / CLAUDE.md / .agent.md + Compact Web Capsule */}
      {showPolyglotModal && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="polyglot-modal-title"
          className="fixed inset-0 z-50 bg-slate-900/50 flex items-center justify-center p-4"
        >
          <div className="bg-white border border-slate-200 rounded-xl max-w-4xl w-full p-6 shadow-xl space-y-4 max-h-[88vh] flex flex-col">
            <div className="flex items-center justify-between border-b border-slate-200 pb-3">
              <div>
                <div className="text-xs font-mono text-slate-500">
                  POLYGLOT CONSTITUTION &amp; WEB CAPSULE · /api/brain/AGENTS.md &amp; /api/brain/capsule.txt
                </div>
                <h3 id="polyglot-modal-title" className="text-base font-bold text-slate-900">
                  Universal One-Brain Bootstrap (Works Across Codex, Claude Code, Kimi, Otto, DeepSeek Web, Grok &amp; Meta Muse)
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setShowPolyglotModal(false)}
                className="px-2.5 py-1 text-xs font-medium text-slate-600 hover:text-slate-900 border border-slate-200 rounded-md cursor-pointer"
              >
                Close
              </button>
            </div>

            <div className="space-y-3 overflow-y-auto pr-1">
              <div className="space-y-1.5">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-bold text-slate-900">
                    1. Compact Web/App Context Capsule (For DeepSeek Web, Claude Web, Kimi App, Grok, Meta Muse)
                  </span>
                  <button
                    type="button"
                    onClick={() => {
                      navigator.clipboard?.writeText(brainState.universalCapsuleText);
                      setCopiedCapsule(true);
                      setTimeout(() => setCopiedCapsule(false), 2000);
                    }}
                    className="px-2.5 py-1 text-xs font-semibold text-white bg-slate-900 hover:bg-slate-800 rounded-md inline-flex items-center gap-1 cursor-pointer"
                  >
                    {copiedCapsule ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
                    {copiedCapsule ? 'Copied Capsule' : 'Copy [GENESIS-CAPSULE-v6]'}
                  </button>
                </div>
                <pre className="p-3 bg-slate-950 text-emerald-300 rounded-lg text-[11px] font-mono overflow-x-auto whitespace-pre-wrap">
                  {brainState.universalCapsuleText}
                </pre>
              </div>

              <div className="space-y-1.5">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-bold text-slate-900">
                    2. Polyglot Repo Constitution (AGENTS.md / CLAUDE.md / GEMINI.md / .agent.md)
                  </span>
                  <button
                    type="button"
                    onClick={() => {
                      navigator.clipboard?.writeText(brainState.polyglotAgentMdContent);
                      setCopiedMd(true);
                      setTimeout(() => setCopiedMd(false), 2000);
                    }}
                    className="px-2.5 py-1 text-xs font-semibold text-slate-800 bg-slate-100 hover:bg-slate-200 border border-slate-300 rounded-md inline-flex items-center gap-1 cursor-pointer"
                  >
                    {copiedMd ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
                    {copiedMd ? 'Copied AGENTS.md' : 'Copy Full AGENTS.md'}
                  </button>
                </div>
                <pre className="p-3 bg-slate-900 text-slate-100 rounded-lg text-[11px] font-mono overflow-x-auto whitespace-pre-wrap max-h-64">
                  {brainState.polyglotAgentMdContent}
                </pre>
              </div>
            </div>
          </div>
        </div>
      )}
    </section>
  );
};
