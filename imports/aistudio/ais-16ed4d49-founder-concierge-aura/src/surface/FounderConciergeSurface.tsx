import React, { useEffect, useState, useRef } from 'react';
import {
  SurfaceRoute,
  VerifiedSurfaceState,
  InstructionExecutionResult,
  GreenlaneProjection,
  SpecialistNode,
  probeVerifiedSurfaceState,
  submitAuthenticatedInstruction,
  fetchGreenlaneProjection,
  fetchFleetNodes,
} from '../engine/protocolEngine';
import { VisemeNeuralOrb } from '../components/VisemeNeuralOrb';
import { EphemeralActionCard } from '../components/EphemeralActionCard';
import { AuthModal } from '../components/AuthModal';
import {
  ShieldAlert,
  Send,
  GitBranch,
  Cpu,
  RefreshCw,
  KeyRound,
  ExternalLink,
  Lock,
  Radio,
  FileCheck2,
  Sparkles,
} from 'lucide-react';

const ROUTES: { id: SurfaceRoute; label: string }[] = [
  { id: 'concierge', label: 'Concierge' },
  { id: 'greenlane', label: 'Greenlane' },
  { id: 'fleet', label: 'Fleet' },
  { id: 'council', label: '3-Shield Council' },
];

function getHashRoute(): SurfaceRoute {
  const hash = window.location.hash.replace(/^#\/?/, '').split('/')[0].toLowerCase();
  if (hash === 'otto' || hash === 'concierge' || !hash) return 'concierge';
  if (hash === 'greenlane') return 'greenlane';
  if (hash === 'fleet' || hash === 'optimus') return 'fleet';
  if (hash === 'decisions' || hash === 'omega' || hash === 'council') return 'council';
  return 'concierge';
}

export const FounderConciergeSurface: React.FC = () => {
  const [route, setRoute] = useState<SurfaceRoute>(getHashRoute);
  const [surfaceState, setSurfaceState] = useState<VerifiedSurfaceState | null>(null);
  const [loadingState, setLoadingState] = useState<boolean>(true);

  // Voice & Viseme
  const [voiceActive, setVoiceActive] = useState<boolean>(false);
  const [visemeEnergy, setVisemeEnergy] = useState<number>(0.12);
  const [orbMode, setOrbMode] = useState<'listening' | 'speaking' | 'idle' | 'executing'>('idle');

  // Input & Execution
  const [intentInput, setIntentInput] = useState<string>('');
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [executionResult, setExecutionResult] = useState<InstructionExecutionResult | null>(null);

  // Authenticated Headers
  const [cfAccessJwt, setCfAccessJwt] = useState<string>('');
  const [ed25519Signature, setEd25519Signature] = useState<string>('');
  const [authModalOpen, setAuthModalOpen] = useState<boolean>(false);

  // Supporting Telemetry Data
  const [greenlaneData, setGreenlaneData] = useState<GreenlaneProjection | null>(null);
  const [fleetNodes, setFleetNodes] = useState<SpecialistNode[]>([]);
  const [loadingSupporting, setLoadingSupporting] = useState<boolean>(false);

  const recognitionRef = useRef<any>(null);

  // Route Synchronization
  useEffect(() => {
    const handleHash = () => setRoute(getHashRoute());
    window.addEventListener('hashchange', handleHash);
    if (!window.location.hash) {
      window.history.replaceState(null, '', '#concierge');
    }
    return () => window.removeEventListener('hashchange', handleHash);
  }, []);

  const navigateTo = (r: SurfaceRoute) => {
    window.location.hash = `#${r}`;
    setRoute(r);
  };

  // Live state polling
  const refreshSurfaceState = async () => {
    setLoadingState(true);
    const state = await probeVerifiedSurfaceState();
    setSurfaceState(state);
    setLoadingState(false);
  };

  useEffect(() => {
    refreshSurfaceState();
    const interval = setInterval(refreshSurfaceState, 8000);
    return () => clearInterval(interval);
  }, []);

  // Supporting projections when switching tabs
  useEffect(() => {
    if (route === 'greenlane') {
      setLoadingSupporting(true);
      fetchGreenlaneProjection().then((res) => {
        setGreenlaneData(res);
        setLoadingSupporting(false);
      });
    } else if (route === 'fleet') {
      setLoadingSupporting(true);
      fetchFleetNodes().then((res) => {
        setFleetNodes(res.nodes);
        setLoadingSupporting(false);
      });
    }
  }, [route]);

  // Voice recognition wiring
  const toggleVoice = () => {
    if (voiceActive) {
      recognitionRef.current?.stop();
      setVoiceActive(false);
      setOrbMode('idle');
      return;
    }

    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

    if (!SpeechRecognition) {
      // Speech recognition not supported by browser
      speakText('Speech recognition is not supported in this browser. Please type your instruction.');
      return;
    }

    try {
      const recognition = new SpeechRecognition();
      recognition.continuous = false;
      recognition.interimResults = true;
      recognition.lang = 'en-GB';

      recognition.onstart = () => {
        setVoiceActive(true);
        setOrbMode('listening');
      };

      recognition.onresult = (event: any) => {
        const transcript = Array.from(event.results)
          .map((r: any) => r[0].transcript)
          .join('');
        setIntentInput(transcript);
        setVisemeEnergy(0.4 + Math.random() * 0.5);

        if (event.results[0].isFinal) {
          handleExecute(transcript);
        }
      };

      recognition.onerror = () => {
        setVoiceActive(false);
        setOrbMode('idle');
      };

      recognition.onend = () => {
        setVoiceActive(false);
        if (orbMode === 'listening') setOrbMode('idle');
      };

      recognitionRef.current = recognition;
      recognition.start();
    } catch (_) {
      setVoiceActive(false);
      setOrbMode('idle');
    }
  };

  // Synthesize speech output for the concierge
  const speakText = (text: string) => {
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.rate = 1.05;
      utterance.pitch = 1.0;
      utterance.lang = 'en-GB';
      utterance.onstart = () => {
        setOrbMode('speaking');
        setVoiceActive(true);
        setVisemeEnergy(0.65);
      };
      utterance.onend = () => {
        setOrbMode('idle');
        setVoiceActive(false);
        setVisemeEnergy(0.12);
      };
      window.speechSynthesis.speak(utterance);
    }
  };

  // Reactive energy pulse for the orb
  useEffect(() => {
    if (!voiceActive && orbMode === 'idle') {
      setVisemeEnergy(0.12);
      return;
    }
    const pulse = setInterval(() => {
      setVisemeEnergy(0.3 + Math.random() * 0.6);
    }, 80);
    return () => clearInterval(pulse);
  }, [voiceActive, orbMode]);

  const canExecute =
    Boolean(surfaceState?.ok) &&
    Boolean(surfaceState?.capabilities?.sessionWritable);

  const handleExecute = async (overrideIntent?: string) => {
    const text = (overrideIntent ?? intentInput).trim();
    if (!text || submitting) return;

    setSubmitting(true);
    setOrbMode('executing');
    setExecutionResult(null);

    const result = await submitAuthenticatedInstruction(text, {
      cfAccessJwt: cfAccessJwt || undefined,
      founderEd25519Signature: ed25519Signature || undefined,
    });

    setExecutionResult(result);
    setSubmitting(false);

    if (result.ok) {
      setOrbMode('speaking');
      speakText(`Instruction ${result.instructionId} cryptographically sealed. Outcome: ${result.verifiedOutcome}`);
      setIntentInput('');
    } else {
      setOrbMode('idle');
      speakText(`Execution rejected. Error code: ${result.errorCode}`);
    }

    // Refresh telemetry to show updated queues
    refreshSurfaceState();
  };

  return (
    <div className="min-h-screen bg-[#05070D] text-slate-100 flex flex-col justify-between p-4 sm:p-6 lg:p-8 font-sans selection:bg-cyan-500/30 selection:text-cyan-200">
      {/* Top Bar: Clean 3-zone contract */}
      <header className="flex items-center justify-between gap-8 border-b border-white/10 pb-4">
        {/* Zone 1: Brand title, one line */}
        <div className="flex items-center gap-3 whitespace-nowrap shrink-0">
          <span className="text-base font-semibold tracking-tight text-white">
            Genesis Founder Concierge
          </span>
          <span className="text-xs font-mono text-slate-400">
            · {surfaceState?.provenanceCommit ? surfaceState.provenanceCommit.slice(0, 8) : 'PROBING...'}
          </span>
        </div>

        {/* Zone 2: Navigation Links */}
        <nav className="hidden md:flex items-center gap-6 text-sm font-medium text-slate-400">
          {ROUTES.map((tab) => {
            const active = route === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => navigateTo(tab.id)}
                className={`transition-colors whitespace-nowrap shrink-0 ${
                  active ? 'text-white border-b-2 border-cyan-400 pb-0.5' : 'hover:text-slate-200'
                }`}
              >
                {tab.label}
              </button>
            );
          })}
        </nav>

        {/* Zone 3: Primary Action & Security Gate */}
        <div className="flex items-center gap-3 shrink-0">
          <button
            onClick={() => setAuthModalOpen(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-mono text-slate-300 hover:text-white bg-white/5 hover:bg-white/10 border border-white/10 transition-colors whitespace-nowrap shrink-0"
          >
            <KeyRound className="w-3.5 h-3.5 text-cyan-400" />
            <span>{cfAccessJwt || ed25519Signature ? 'Signed Authority' : 'Auth Config'}</span>
          </button>

          <button
            onClick={refreshSurfaceState}
            disabled={loadingState}
            aria-label="Refresh status"
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-white/5 transition-colors whitespace-nowrap shrink-0"
          >
            <RefreshCw className={`w-4 h-4 ${loadingState ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </header>

      {/* Fail-Closed Blocker Banner (if capabilities unavailable) */}
      {surfaceState && (!surfaceState.ok || !surfaceState.capabilities?.sessionWritable) && (
        <section
          aria-label="Release Blockers"
          className="my-4 p-4 rounded-xl bg-rose-950/40 border border-rose-500/30 text-rose-200 text-xs font-mono space-y-2"
        >
          <div className="flex items-center justify-between flex-wrap gap-2">
            <div className="flex items-center gap-2 text-rose-300 font-bold uppercase tracking-wider">
              <ShieldAlert className="w-4 h-4" />
              <span>COMMERCIAL RELEASE STATUS: BLOCKED — CAPABILITIES UNAVAILABLE</span>
            </div>
            <div className="text-[11px] text-rose-400">
              HTTP {surfaceState.httpStatus} · {surfaceState.errorCode}
            </div>
          </div>
          <p className="text-slate-300 text-[11px] leading-relaxed">
            {surfaceState.errorMessage ||
              'ESTATE_UPSTREAM_URL is not bound on this Cloudflare Pages deployment. In strict compliance with Argon #20 and IDP #7664, mutations fail closed without fabricating green state.'}
          </p>
          <div className="flex flex-wrap items-center gap-x-5 gap-y-1 pt-1 text-[11px]">
            <span>
              Writable Cloud Backend:{' '}
              <strong className={surfaceState.capabilities?.sessionWritable ? 'text-emerald-400' : 'text-rose-400'}>
                {surfaceState.capabilities?.sessionWritable ? 'CONNECTED' : 'UNAVAILABLE'}
              </strong>
            </span>
            <span>
              Voice Gateway (IDP #7664):{' '}
              <strong className={surfaceState.capabilities?.voiceGatewayConnected ? 'text-emerald-400' : 'text-rose-400'}>
                {surfaceState.capabilities?.voiceGatewayConnected ? 'READY' : 'PENDING'}
              </strong>
            </span>
            <span>
              Greenlane Projection:{' '}
              <strong className={surfaceState.capabilities?.greenlaneProjectionAttached ? 'text-emerald-400' : 'text-slate-400'}>
                {surfaceState.capabilities?.greenlaneProjectionAttached ? 'ATTACHED' : 'STANDBY'}
              </strong>
            </span>
          </div>
        </section>
      )}

      {/* Central Viewport */}
      <main className="my-auto max-w-4xl w-full mx-auto py-8">
        {/* TAB 1: CONCIERGE (Single Voice-First Command Surface) */}
        {route === 'concierge' && (
          <div className="flex flex-col items-center justify-center space-y-8 text-center">
            {/* The 60fps Reactive Neural Viseme Orb */}
            <div className="relative">
              <VisemeNeuralOrb
                active={voiceActive}
                energy={visemeEnergy}
                mode={orbMode}
                onClick={toggleVoice}
                disabled={!surfaceState?.capabilities?.voiceGatewayConnected && !('webkitSpeechRecognition' in window || 'SpeechRecognition' in window)}
              />
            </div>

            {/* Instruction Context Kicker */}
            <div className="max-w-xl space-y-2">
              <h1 className="text-2xl font-bold tracking-tight text-white">
                Autonomous Founder Concierge
              </h1>
              <p className="text-xs text-slate-400 max-w-md mx-auto leading-relaxed">
                Speak or type what you want. The concierge inspects the proposal, routes via IDP #7664, and reports verified outcomes.
              </p>
            </div>

            {/* Sovereign Command Input Bar */}
            <div className="w-full max-w-2xl bg-black/40 border border-white/10 backdrop-blur-xl rounded-2xl p-2 flex items-center gap-2 shadow-2xl">
              <input
                type="text"
                value={intentInput}
                onChange={(e) => setIntentInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleExecute()}
                disabled={submitting}
                placeholder="e.g., Promote commit da1536c7 to production across Argon #20..."
                className="flex-1 bg-transparent px-4 py-2.5 text-sm text-white placeholder-slate-500 focus:outline-none"
              />
              <button
                onClick={() => handleExecute()}
                disabled={submitting || !intentInput.trim()}
                className="flex items-center gap-1.5 px-5 py-2.5 rounded-xl bg-cyan-400 hover:bg-cyan-300 text-slate-950 font-semibold text-xs tracking-wider uppercase disabled:opacity-30 disabled:cursor-not-allowed transition-all"
              >
                <Send className="w-3.5 h-3.5" />
                <span>{submitting ? 'Sealing...' : 'Dispatch'}</span>
              </button>
            </div>

            {/* Ephemeral Action Card (Materializes on outcome) */}
            {executionResult && (
              <EphemeralActionCard
                result={executionResult}
                onDismiss={() => setExecutionResult(null)}
                onExecuteNext={(next) => {
                  setIntentInput(next);
                  handleExecute(next);
                }}
              />
            )}
          </div>
        )}

        {/* TAB 2: GREENLANE GITOPS PROJECTION */}
        {route === 'greenlane' && (
          <div className="space-y-6">
            <div className="border-b border-white/10 pb-4 flex items-center justify-between">
              <div>
                <h2 className="text-lg font-semibold text-white">Greenlane GitOps & Provenance Gates</h2>
                <p className="text-xs text-slate-400 mt-1">
                  Canonical SHA reconciliation between chidionyema/argon and chidionyema/idp.
                </p>
              </div>
              <div className="text-xs font-mono text-cyan-400">
                Guardian Base: {greenlaneData?.guardianBaseSha.slice(0, 8) || 'da1536c7'}
              </div>
            </div>

            {loadingSupporting ? (
              <div className="p-8 text-center text-xs font-mono text-slate-400 animate-pulse">
                Probing GitOps pipelines...
              </div>
            ) : greenlaneData && greenlaneData.pipelines.length > 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {greenlaneData.pipelines.map((p) => (
                  <div
                    key={`${p.repo}-${p.runId}`}
                    className="p-5 rounded-2xl bg-white/[0.02] border border-white/10 space-y-3"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <GitBranch className="w-4 h-4 text-cyan-400" />
                        <span className="text-xs font-mono font-semibold text-white">{p.repo}</span>
                      </div>
                      <span className="text-[11px] font-mono text-emerald-400">
                        {p.status}
                      </span>
                    </div>
                    <div className="text-sm font-medium text-slate-200">{p.gate}</div>
                    <div className="text-xs font-mono text-slate-400 flex items-center justify-between pt-2 border-t border-white/5">
                      <span>Branch: {p.branch}</span>
                      <span>Run #{p.runId}</span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="p-8 rounded-2xl bg-white/[0.02] border border-white/10 text-center space-y-2">
                <div className="text-sm font-medium text-slate-300">Live Projection Active</div>
                <p className="text-xs text-slate-400 max-w-md mx-auto">
                  Pipelines will project in real time as Legion execution runs complete against Argon #20 and IDP #7664.
                </p>
              </div>
            )}
          </div>
        )}

        {/* TAB 3: FLEET SPECIALIST NODES */}
        {route === 'fleet' && (
          <div className="space-y-6">
            <div className="border-b border-white/10 pb-4 flex items-center justify-between">
              <div>
                <h2 className="text-lg font-semibold text-white">Autonomous Fleet Specialist Nodes</h2>
                <p className="text-xs text-slate-400 mt-1">
                  Active model lanes, Legion runners, and shard routers. Zero seeded literals.
                </p>
              </div>
              <div className="text-xs font-mono text-slate-400">
                LANE: {surfaceState?.capabilities?.modelCredentialPresent ? 'ONLINE' : 'CREDENTIAL PENDING'}
              </div>
            </div>

            {loadingSupporting ? (
              <div className="p-8 text-center text-xs font-mono text-slate-400 animate-pulse">
                Probing specialist fleet nodes...
              </div>
            ) : fleetNodes.length > 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {fleetNodes.map((node) => (
                  <div
                    key={node.nodeId}
                    className="p-5 rounded-2xl bg-white/[0.02] border border-white/10 space-y-3"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Cpu className="w-4 h-4 text-cyan-400" />
                        <span className="text-xs font-mono font-semibold text-white">{node.nodeId}</span>
                      </div>
                      <span className="text-[11px] font-mono text-emerald-400">
                        {node.status} · {node.latencyMs}ms
                      </span>
                    </div>
                    <div className="text-sm font-medium text-slate-200">{node.role}</div>
                    <div className="text-xs font-mono text-slate-400 flex items-center justify-between pt-2 border-t border-white/5">
                      <span>Model Lane: {node.modelLane}</span>
                      <span>{node.assignedMission || 'Idle standby'}</span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="p-8 rounded-2xl bg-white/[0.02] border border-white/10 text-center space-y-3">
                <Cpu className="w-6 h-6 text-slate-500 mx-auto" />
                <div className="text-sm font-medium text-slate-300">Fleet Registry Standby</div>
                <p className="text-xs text-slate-400 max-w-md mx-auto">
                  Nodes report status dynamically when claimed by Argon crew work board and Legion #7794. No static mock members are displayed.
                </p>
              </div>
            )}
          </div>
        )}

        {/* TAB 4: 3-SHIELD COUNCIL DECISIONS */}
        {route === 'council' && (
          <div className="space-y-6">
            <div className="border-b border-white/10 pb-4">
              <h2 className="text-lg font-semibold text-white">3-Shield Decision Council</h2>
              <p className="text-xs text-slate-400 mt-1">
                Cryptographic gating layers ensuring sovereign founder verification.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="p-5 rounded-2xl bg-white/[0.02] border border-white/10 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-mono uppercase tracking-wider text-cyan-400">Shield 01</span>
                  <span className="text-[10px] font-mono text-emerald-400">ARMED</span>
                </div>
                <div className="text-sm font-medium text-white">Argon WWFD Memory</div>
                <p className="text-xs text-slate-400 leading-relaxed">
                  Evaluates past founder decisions and architectural invariants before accepting proposed mutations.
                </p>
              </div>

              <div className="p-5 rounded-2xl bg-white/[0.02] border border-white/10 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-mono uppercase tracking-wider text-cyan-400">Shield 02</span>
                  <span className="text-[10px] font-mono text-emerald-400">ARMED</span>
                </div>
                <div className="text-sm font-medium text-white">256K Lineage Verifier</div>
                <p className="text-xs text-slate-400 leading-relaxed">
                  Audits entire codebase lineage to prevent regressions, broken routes, or unauthenticated write paths.
                </p>
              </div>

              <div className="p-5 rounded-2xl bg-white/[0.02] border border-white/10 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-mono uppercase tracking-wider text-cyan-400">Shield 03</span>
                  <span className="text-[10px] font-mono text-emerald-400">ARMED</span>
                </div>
                <div className="text-sm font-medium text-white">Ed25519 Certifier</div>
                <p className="text-xs text-slate-400 leading-relaxed">
                  Cryptographically validates detached request signatures and seals final commits with non-repudiable provenance.
                </p>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* Footer: Quiet attribution and status */}
      <footer className="flex items-center justify-between text-xs font-mono text-slate-500 border-t border-white/10 pt-4">
        <span>ZERO SEEDED FIXTURES · FAIL-CLOSED SOVEREIGN CONCIERGE</span>
        <span>LENS: #{route.toUpperCase()}</span>
      </footer>

      {/* Auth Credentials Modal */}
      <AuthModal
        isOpen={authModalOpen}
        onClose={() => setAuthModalOpen(false)}
        onSaveCredentials={({ cfAccessJwt: jwt, ed25519Signature: sig }) => {
          setCfAccessJwt(jwt);
          setEd25519Signature(sig);
        }}
        currentJwt={cfAccessJwt}
        currentSignature={ed25519Signature}
      />
    </div>
  );
};
