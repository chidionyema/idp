import React, { useState, useEffect, useRef } from 'react';
import { Mic, MicOff, Volume2, VolumeX, Send, Sparkles, ArrowRight, ShieldCheck, AlertCircle, Play, CheckCircle2 } from 'lucide-react';
import { EstateState, executeFounderInterrogation, InterrogationResult } from '../utils/estateLogic';

interface VoiceConciergeOrbProps {
  estateState: EstateState;
  onNavigateToPillar: (pillarId: string) => void;
  onExecuteAction: (actionType: 'remediate_legion' | 'verify_greenlane') => void;
}

export const VoiceConciergeOrb: React.FC<VoiceConciergeOrbProps> = ({
  estateState,
  onNavigateToPillar,
  onExecuteAction,
}) => {
  const [queryInput, setQueryInput] = useState('');
  const [isListening, setIsListening] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [soundEnabled, setSoundEnabled] = useState(true);
  const [currentResult, setCurrentResult] = useState<InterrogationResult | null>(null);
  const [pulseSpeed, setPulseSpeed] = useState(1);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  // Futuristic audio synthesizer using Web Audio API
  const playSynthesizerPing = (frequency = 520, type: OscillatorType = 'sine', duration = 0.25) => {
    if (!soundEnabled) return;
    try {
      const AudioCtx = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
      if (!AudioCtx) return;
      const ctx = new AudioCtx();
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();

      osc.type = type;
      osc.frequency.setValueAtTime(frequency, ctx.currentTime);
      osc.frequency.exponentialRampToValueAtTime(frequency * 1.5, ctx.currentTime + duration);

      gain.gain.setValueAtTime(0.08, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + duration);

      osc.connect(gain);
      gain.connect(ctx.destination);

      osc.start();
      osc.stop(ctx.currentTime + duration);
    } catch {
      // AudioContext may be blocked before gesture
    }
  };

  // Browser speech synthesis for founder voice response
  const speakSynthesis = (text: string) => {
    if (!soundEnabled || typeof window === 'undefined' || !window.speechSynthesis) return;
    try {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.rate = 1.05;
      utterance.pitch = 0.95;
      utterance.onstart = () => setIsSpeaking(true);
      utterance.onend = () => setIsSpeaking(false);
      utterance.onerror = () => setIsSpeaking(false);
      window.speechSynthesis.speak(utterance);
    } catch {
      setIsSpeaking(false);
    }
  };

  const handleInterrogate = (textToQuery: string) => {
    if (!textToQuery.trim()) return;
    playSynthesizerPing(640, 'triangle', 0.2);
    setPulseSpeed(2.5);

    const result = executeFounderInterrogation(textToQuery, estateState);
    setCurrentResult(result);
    setQueryInput('');

    if (estateState.operationalParameters.voiceConciergeSynthesis) {
      speakSynthesis(result.synthesis);
    }

    setTimeout(() => {
      setPulseSpeed(1);
    }, 1200);
  };

  // Interactive Voice Mic simulation or Web Speech API if supported
  const toggleListening = () => {
    if (isListening) {
      setIsListening(false);
      return;
    }

    const SpeechRecognition = (window as unknown as { SpeechRecognition?: any; webkitSpeechRecognition?: any }).SpeechRecognition ||
      (window as unknown as { SpeechRecognition?: any; webkitSpeechRecognition?: any }).webkitSpeechRecognition;

    if (SpeechRecognition) {
      try {
        const recognition = new SpeechRecognition();
        recognition.continuous = false;
        recognition.interimResults = false;
        recognition.lang = 'en-US';

        recognition.onstart = () => {
          setIsListening(true);
          playSynthesizerPing(880, 'sine', 0.15);
        };

        recognition.onresult = (event: any) => {
          const transcript = event.results[0][0].transcript;
          handleInterrogate(transcript);
          setIsListening(false);
        };

        recognition.onerror = () => {
          setIsListening(false);
        };

        recognition.onend = () => {
          setIsListening(false);
        };

        recognition.start();
        return;
      } catch {
        // Fall back to toggle
      }
    }

    // Default simulation for testing without physical mic permissions
    setIsListening(true);
    playSynthesizerPing(760, 'sine', 0.15);
    setTimeout(() => {
      setIsListening(false);
      handleInterrogate('Interrogate Legion recovery run #42412348112');
    }, 1800);
  };

  // 2100 Holographic Particle Orb Canvas animation
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animFrame: number;
    let angle = 0;

    const render = () => {
      const width = canvas.width;
      const height = canvas.height;
      const centerX = width / 2;
      const centerY = height / 2;

      ctx.clearRect(0, 0, width, height);

      angle += 0.015 * pulseSpeed;

      // Outer concentric aura ring
      const radiusBase = isSpeaking ? 68 + Math.sin(angle * 4) * 8 : isListening ? 72 + Math.cos(angle * 6) * 6 : 60 + Math.sin(angle * 2) * 4;

      // Glow gradient
      const grad = ctx.createRadialGradient(centerX, centerY, 10, centerX, centerY, radiusBase * 1.5);
      grad.addColorStop(0, isSpeaking ? 'rgba(56, 189, 248, 0.45)' : isListening ? 'rgba(239, 68, 68, 0.5)' : 'rgba(56, 189, 248, 0.25)');
      grad.addColorStop(0.5, 'rgba(14, 165, 233, 0.1)');
      grad.addColorStop(1, 'transparent');
      ctx.fillStyle = grad;
      ctx.beginPath();
      ctx.arc(centerX, centerY, radiusBase * 1.5, 0, Math.PI * 2);
      ctx.fill();

      // Dynamic orbital rings
      for (let r = 0; r < 3; r++) {
        ctx.save();
        ctx.translate(centerX, centerY);
        ctx.rotate(angle * (r % 2 === 0 ? 1 : -1) + (r * Math.PI) / 3);
        ctx.beginPath();
        ctx.ellipse(0, 0, radiusBase + r * 12, (radiusBase + r * 12) * 0.45, 0, 0, Math.PI * 2);
        ctx.strokeStyle = r === 0 ? 'rgba(56, 189, 248, 0.65)' : r === 1 ? 'rgba(125, 211, 252, 0.35)' : 'rgba(14, 165, 233, 0.2)';
        ctx.lineWidth = 1.5;
        ctx.stroke();
        ctx.restore();
      }

      // Core neural sphere
      const coreGrad = ctx.createRadialGradient(centerX - 10, centerY - 10, 2, centerX, centerY, 38);
      coreGrad.addColorStop(0, '#ffffff');
      coreGrad.addColorStop(0.3, '#38bdf8');
      coreGrad.addColorStop(0.7, '#0284c7');
      coreGrad.addColorStop(1, '#0c4a6e');

      ctx.fillStyle = coreGrad;
      ctx.beginPath();
      ctx.arc(centerX, centerY, 36, 0, Math.PI * 2);
      ctx.fill();

      // Internal synapsing particles
      for (let i = 0; i < 8; i++) {
        const pAngle = angle * 2 + (i * Math.PI) / 4;
        const px = centerX + Math.cos(pAngle) * (20 + Math.sin(angle * 3 + i) * 8);
        const py = centerY + Math.sin(pAngle) * (20 + Math.cos(angle * 3 + i) * 8);
        ctx.fillStyle = '#ffffff';
        ctx.beginPath();
        ctx.arc(px, py, 2.2, 0, Math.PI * 2);
        ctx.fill();
      }

      animFrame = requestAnimationFrame(render);
    };

    render();

    return () => {
      cancelAnimationFrame(animFrame);
    };
  }, [isSpeaking, isListening, pulseSpeed]);

  const quickInterrogations = [
    { label: 'Legion Recovery #42412348112', query: 'What is the status of Legion recovery run #42412348112?' },
    { label: 'Genesis Spine Topology', query: 'Audit Genesis neural spine node latency and packet throughput' },
    { label: 'Parity Regression Gate', query: 'Run capability-parity regression gate verification' },
    { label: 'Greenlane Diagnostics', query: 'Inspect estate diagnostics and Greenlane invariant state' },
    { label: 'Argon Active ML Checkpoint', query: 'What is the status of Research and ML model training?' },
  ];

  return (
    <div className="relative rounded-2xl border border-sky-500/20 bg-slate-900/60 backdrop-blur-xl p-6 shadow-2xl spatial-grid overflow-hidden">
      {/* Background ambient lighting */}
      <div className="absolute top-0 right-1/4 w-96 h-96 bg-sky-500/10 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-0 left-1/4 w-80 h-80 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none" />

      {/* Header bar of the Concierge layer */}
      <div className="relative z-10 flex flex-wrap items-center justify-between gap-4 pb-6 border-b border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold tracking-wider text-sky-400 uppercase">2100 Spatial Access Layer</span>
            <span className="text-xs text-slate-500">·</span>
            <span className="text-xs text-slate-400">Founder Surface Concierge</span>
          </div>
          <h2 className="text-xl font-bold tracking-tight text-white mt-1">
            Universal Estate Interrogation &amp; Orchestration
          </h2>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setSoundEnabled(!soundEnabled)}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
              soundEnabled
                ? 'bg-sky-950/50 border-sky-500/40 text-sky-300 hover:bg-sky-900/50'
                : 'bg-slate-800/60 border-slate-700 text-slate-400 hover:text-slate-200'
            }`}
            title="Toggle audio feedback"
          >
            {soundEnabled ? <Volume2 className="w-3.5 h-3.5" /> : <VolumeX className="w-3.5 h-3.5" />}
            <span>{soundEnabled ? 'Synthesizer Active' : 'Muted'}</span>
          </button>

          <button
            onClick={() => onNavigateToPillar('evaluations')}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 hover:bg-emerald-500/20 transition-colors"
          >
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>Parity Gate: Active</span>
          </button>
        </div>
      </div>

      {/* Main interactive stage */}
      <div className="relative z-10 grid grid-cols-1 lg:grid-cols-12 gap-8 items-center pt-6">
        {/* Left: The 2100 Voice Orb */}
        <div className="lg:col-span-5 flex flex-col items-center justify-center text-center p-4">
          <div className="relative flex items-center justify-center w-64 h-64">
            <canvas
              ref={canvasRef}
              width={256}
              height={256}
              className="w-64 h-64 cursor-pointer"
              onClick={toggleListening}
              title="Click to engage Voice Concierge"
            />
            {/* Center icon indicator */}
            <button
              onClick={toggleListening}
              aria-label={isListening ? 'Stop listening' : 'Start voice interrogation'}
              className="absolute w-14 h-14 rounded-full flex items-center justify-center bg-sky-500/20 hover:bg-sky-500/30 border border-sky-400/50 text-white transition-transform active:scale-95 shadow-lg"
            >
              {isListening ? (
                <MicOff className="w-6 h-6 text-red-400 animate-pulse" />
              ) : (
                <Mic className="w-6 h-6 text-sky-300" />
              )}
            </button>
          </div>

          <div className="mt-2">
            <span className="text-xs font-mono text-sky-400">
              {isSpeaking ? 'Voice Concierge Synthesizing Response...' : isListening ? 'Listening for Founder Directive...' : 'Orb Ready · Neural Spine Synced'}
            </span>
            <p className="text-xs text-slate-400 max-w-xs mt-1">
              Speak or query directly to discover, interrogate, or execute across all estate intelligence subsystems.
            </p>
          </div>
        </div>

        {/* Right: Command Input & Contextual Intelligence Projection */}
        <div className="lg:col-span-7 flex flex-col gap-4">
          {/* Natural language query bar */}
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleInterrogate(queryInput);
            }}
            className="flex items-center gap-2 bg-slate-950/80 border border-slate-700/80 focus-within:border-sky-500 rounded-xl p-1.5 shadow-inner"
          >
            <div className="pl-3 text-sky-400">
              <Sparkles className="w-4 h-4" />
            </div>
            <input
              type="text"
              value={queryInput}
              onChange={(e) => setQueryInput(e.target.value)}
              placeholder="Interrogate estate intelligence or issue founder directive..."
              className="flex-1 bg-transparent px-2 py-2 text-sm text-white placeholder-slate-500 focus:outline-none"
            />
            <button
              type="submit"
              disabled={!queryInput.trim()}
              className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-semibold text-white bg-sky-600 hover:bg-sky-500 disabled:opacity-40 disabled:hover:bg-sky-600 transition-colors shrink-0"
            >
              <span>Interrogate</span>
              <Send className="w-3.5 h-3.5" />
            </button>
          </form>

          {/* Preset fast interrogation buttons */}
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs text-slate-400">Quick Interrogations:</span>
            {quickInterrogations.map((item, idx) => (
              <button
                key={idx}
                onClick={() => handleInterrogate(item.query)}
                className="px-2.5 py-1 text-xs rounded-md bg-slate-800/80 hover:bg-slate-700/80 border border-slate-700 text-slate-300 hover:text-white transition-colors"
              >
                {item.label}
              </button>
            ))}
          </div>

          {/* Contextual Intelligence Card (Populates dynamically on interrogation) */}
          {currentResult ? (
            <div className="rounded-xl border border-sky-500/30 bg-slate-950/90 p-5 shadow-xl transition-all">
              <div className="flex items-start justify-between gap-4 border-b border-slate-800 pb-3">
                <div>
                  <span className="text-xs font-mono text-sky-400">Interrogation Result · Confidence {(currentResult.confidence * 100).toFixed(0)}%</span>
                  <h3 className="text-sm font-semibold text-white mt-0.5">
                    "{currentResult.query}"
                  </h3>
                </div>
                <button
                  onClick={() => onNavigateToPillar(currentResult.recommendedView)}
                  className="flex items-center gap-1 text-xs font-medium text-sky-400 hover:text-sky-300 hover:underline shrink-0"
                >
                  <span>Open Deep Specialist View</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>

              <div className="mt-3">
                <p className="text-sm text-slate-200 leading-relaxed font-sans">
                  {currentResult.synthesis}
                </p>
              </div>

              {/* Contextual telemetry badges */}
              <div className="mt-4 pt-3 border-t border-slate-800/80 flex flex-wrap items-center justify-between gap-3">
                <div className="flex flex-wrap items-center gap-3 text-xs text-slate-400 font-mono">
                  {Object.entries(currentResult.contextData).map(([key, val]) => (
                    <span key={key}>
                      <span className="text-slate-500">{key}:</span> <span className="text-slate-200">{String(val)}</span>
                    </span>
                  ))}
                </div>

                {/* Direct Action Buttons for high-priority incidents */}
                {currentResult.category === 'legion_recovery' && (
                  <button
                    onClick={() => onExecuteAction('remediate_legion')}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-sky-600 hover:bg-sky-500 text-white transition-colors shadow-md"
                  >
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    <span>Apply Legion Remediation &amp; Verify Push</span>
                  </button>
                )}

                {currentResult.category === 'estate_diagnostics' && estateState.greenlaneStatus !== 'verified' && (
                  <button
                    onClick={() => onExecuteAction('verify_greenlane')}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white transition-colors shadow-md"
                  >
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    <span>Run Greenlane Invariant Verification</span>
                  </button>
                )}
              </div>
            </div>
          ) : (
            /* Default baseline intelligence summary */
            <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-5">
              <div className="flex items-center justify-between">
                <span className="text-xs font-mono text-slate-400">Estate Core Baseline · Real-Time Telemetry</span>
                <span className="text-xs text-emerald-400 flex items-center gap-1">
                  <CheckCircle2 className="w-3 h-3" /> All 10 Specialist Pillars Active
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-2 leading-relaxed">
                The 2100 surface maintains non-destructive access over all underlying Argon capabilities: Research &amp; ML loss trajectories, Genesis Spine topology, agent fleets, Greenlane invariants, One-Brain memory, execution history, and Omega overrides.
              </p>
              <div className="grid grid-cols-3 gap-3 mt-4 pt-3 border-t border-slate-800/80 text-center">
                <div className="p-2 rounded bg-slate-900/80 border border-slate-800">
                  <span className="text-xs text-slate-400">Total Throughput</span>
                  <div className="text-base font-bold font-mono text-white tabular-nums mt-0.5">
                    {estateState.totalInferenceThroughput.toLocaleString()} /s
                  </div>
                </div>
                <div className="p-2 rounded bg-slate-900/80 border border-slate-800">
                  <span className="text-xs text-slate-400">Active Fleet</span>
                  <div className="text-base font-bold font-mono text-white tabular-nums mt-0.5">
                    {estateState.agents.length} Agents
                  </div>
                </div>
                <div className="p-2 rounded bg-slate-900/80 border border-slate-800">
                  <span className="text-xs text-slate-400">Parity Retention</span>
                  <div className="text-base font-bold font-mono text-emerald-400 tabular-nums mt-0.5">
                    100% Verified
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
