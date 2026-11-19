/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 * 
 * COMMAND CODE PROTOCOL (CCP) — FOUNDER VOICE CONTROL PLANE
 * One word. One effect. One receipt. One expiry.
 * 90 Canonical Codes across 12 Domains.
 * Includes Web Speech Recognition, Web Audio 2100 Synthesizer,
 * and live active stack management.
 */

import React, { useState, useEffect, useRef } from 'react';
import {
  Mic,
  MicOff,
  Volume2,
  VolumeX,
  Zap,
  ShieldCheck,
  ShieldAlert,
  AlertTriangle,
  Clock,
  Sparkles,
  Search,
  Radio,
  Fingerprint,
  RefreshCw,
  X,
  CheckCircle2,
  Lock,
  Layers,
  Send,
  Sliders,
  Activity,
  Flame,
  ArrowRight,
  Info
} from 'lucide-react';
import {
  COMMAND_CODE_CATALOG,
  INITIAL_ACTIVE_COMMAND_STACK,
  NEVER_DELEGABLE_CODES,
  executeCommandCode,
  revokeActiveCommand,
  CommandCodeMetadata,
  ActiveCommandEntry,
  CommandExecutionResult
} from '../lib/protocolEngine.ts';
import { alienAudio } from '../lib/alienAcousticSynth.ts';

export const CommandCodeSurface: React.FC = () => {
  const [activeStack, setActiveStack] = useState<ActiveCommandEntry[]>(INITIAL_ACTIVE_COMMAND_STACK);
  const [textInput, setTextInput] = useState<string>('');
  const [selectedDomain, setSelectedDomain] = useState<number | 'ALL'>('ALL');
  const [searchFilter, setSearchFilter] = useState<string>('');
  const [lastResult, setLastResult] = useState<CommandExecutionResult | null>(null);

  // Audio / Speech State
  const [isListening, setIsListening] = useState<boolean>(false);
  const [speechSupported, setSpeechSupported] = useState<boolean>(false);
  const [audioEnabled, setAudioEnabled] = useState<boolean>(true);
  const [voiceEchoEnabled, setVoiceEchoEnabled] = useState<boolean>(true);
  const [lastSpokenTranscript, setLastSpokenTranscript] = useState<string>('');
  const recognitionRef = useRef<any>(null);

  // Active stack remaining seconds timer
  useEffect(() => {
    const timer = setInterval(() => {
      setActiveStack(prev =>
        prev
          .map(entry => {
            if (entry.status !== 'ACTIVE') return entry;
            const remaining = Math.max(0, entry.remainingSeconds - 1);
            return {
              ...entry,
              remainingSeconds: remaining,
              status: remaining === 0 ? ('EXPIRED' as const) : ('ACTIVE' as const)
            };
          })
      );
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  // Web Speech Recognition Initialization
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
      if (SpeechRecognition) {
        setSpeechSupported(true);
        const recog = new SpeechRecognition();
        recog.continuous = false;
        recog.interimResults = false;
        recog.lang = 'en-US';

        recog.onresult = (event: any) => {
          const transcript = event.results[0][0].transcript;
          setLastSpokenTranscript(transcript);
          setIsListening(false);
          handleExecute(transcript);
        };

        recog.onerror = () => {
          setIsListening(false);
        };

        recog.onend = () => {
          setIsListening(false);
        };

        recognitionRef.current = recog;
      }
    }
  }, []);

  const toggleMic = () => {
    if (!speechSupported || !recognitionRef.current) return;
    alienAudio.unlockAudio();
    if (isListening) {
      recognitionRef.current.stop();
      setIsListening(false);
    } else {
      try {
        recognitionRef.current.start();
        setIsListening(true);
      } catch (err) {
        setIsListening(false);
      }
    }
  };

  const handleExecute = (raw: string) => {
    alienAudio.unlockAudio();
    const result = executeCommandCode(raw, 'Founder (Chidi)', activeStack);
    setLastResult(result);
    setActiveStack(result.activeStack);
    setTextInput('');

    if (result.success) {
      const meta = COMMAND_CODE_CATALOG.find(c => c.code === result.code);
      const level = meta ? meta.level : 'L1';
      alienAudio.playCommandPulse(level);
      if (voiceEchoEnabled) {
        alienAudio.speakEchoBack(
          result.code,
          'estate',
          meta?.ttlDisplay || '1 hour',
          result.receiptId || 'CMD-001'
        );
      }
    } else {
      alienAudio.speakRefusal(result.code, result.refusalReason || 'Ambiguous code');
    }
  };

  const handleFormSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!textInput.trim()) return;
    handleExecute(textInput.trim());
  };

  const handleRevoke = (receiptId: string) => {
    alienAudio.unlockAudio();
    alienAudio.playCommandPulse('L1');
    const updated = revokeActiveCommand(receiptId, activeStack);
    setActiveStack(updated);
  };

  const activeCount = activeStack.filter(c => c.status === 'ACTIVE').length;

  // Filter 90 codes
  const filteredCodes = COMMAND_CODE_CATALOG.filter(c => {
    const matchesDomain = selectedDomain === 'ALL' || c.domainNumber === selectedDomain;
    const matchesSearch =
      !searchFilter.trim() ||
      c.code.toLowerCase().includes(searchFilter.toLowerCase()) ||
      c.domain.toLowerCase().includes(searchFilter.toLowerCase()) ||
      c.effect.toLowerCase().includes(searchFilter.toLowerCase());
    return matchesDomain && matchesSearch;
  });

  const domains = [
    { num: 1, name: 'Focus & Priority' },
    { num: 2, name: 'Emergency & Posture' },
    { num: 3, name: 'Security & Integrity' },
    { num: 4, name: 'Resilience & Continuity' },
    { num: 5, name: 'Presence & Welfare' },
    { num: 6, name: 'Flow & Throughput' },
    { num: 7, name: 'Compounding & Doctrine' },
    { num: 8, name: 'Evidence & Ledger' },
    { num: 9, name: 'Learning & Agents' },
    { num: 10, name: 'Science & Research' },
    { num: 11, name: 'Diagnosis & Truth' },
    { num: 12, name: 'Governance & Terminal' },
  ];

  return (
    <div className="space-y-6">
      
      {/* Header Banner: 2100 Sovereign Voice Control Plane */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-2xl relative overflow-hidden">
        <div className="absolute top-0 right-0 w-96 h-96 bg-gradient-to-bl from-cyan-500/10 via-purple-500/5 to-transparent blur-3xl pointer-events-none" />

        <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-6 relative z-10">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <span className="px-2.5 py-0.5 rounded-full text-xs font-mono font-bold bg-cyan-950 text-cyan-300 border border-cyan-800 flex items-center gap-1.5">
                <Radio className="w-3.5 h-3.5 animate-pulse text-cyan-400" />
                CONSTITUTIONAL CANON §15
              </span>
              <span className="px-2.5 py-0.5 rounded-full text-xs font-mono bg-purple-950 text-purple-300 border border-purple-800">
                COMMAND CODE PROTOCOL (CCP)
              </span>
              <span className="px-2.5 py-0.5 rounded-full text-xs font-mono bg-indigo-950 text-indigo-300 border border-indigo-800">
                90 CODES · 12 DOMAINS
              </span>
            </div>

            <h1 className="text-2xl sm:text-3xl font-black tracking-tight text-white flex items-center gap-3">
              <span>Founder Voice as System Control Plane</span>
              <Sparkles className="w-6 h-6 text-cyan-400" />
            </h1>
            <p className="text-sm text-slate-400 mt-1 max-w-3xl">
              One word. One effect. One receipt. One expiry. Deterministically shifts the state, priority, and posture of the entire estate in &lt;2.5ms with acoustic synthesis echo-back.
            </p>
          </div>

          {/* Audio Controls & Voice Status */}
          <div className="flex flex-wrap items-center gap-3 shrink-0">
            <button
              onClick={() => {
                const next = !audioEnabled;
                setAudioEnabled(next);
                alienAudio.setSoundEnabled(next);
              }}
              className={`px-3 py-2 rounded-xl text-xs font-mono flex items-center gap-2 border transition-all cursor-pointer ${
                audioEnabled
                  ? 'bg-cyan-950/80 text-cyan-300 border-cyan-700'
                  : 'bg-slate-850 text-slate-400 border-slate-700'
              }`}
              title="Toggle Web Audio 2100 Synthesizer (FM Chimes, Sub-Bass, Heartbeats)"
            >
              {audioEnabled ? <Volume2 className="w-4 h-4 text-cyan-400" /> : <VolumeX className="w-4 h-4 text-slate-500" />}
              <span>{audioEnabled ? '2100 Acoustic Chime' : 'Muted'}</span>
            </button>

            <button
              onClick={() => {
                const next = !voiceEchoEnabled;
                setVoiceEchoEnabled(next);
                alienAudio.setVoiceEnabled(next);
              }}
              className={`px-3 py-2 rounded-xl text-xs font-mono flex items-center gap-2 border transition-all cursor-pointer ${
                voiceEchoEnabled
                  ? 'bg-purple-950/80 text-purple-300 border-purple-700'
                  : 'bg-slate-850 text-slate-400 border-slate-700'
              }`}
              title="Toggle Synthetic Voice Echo-back (<2s contract)"
            >
              <Radio className="w-4 h-4 text-purple-400" />
              <span>{voiceEchoEnabled ? 'Voice Echo: Active' : 'Echo: Off'}</span>
            </button>
          </div>
        </div>

        {/* Live Voice Input & Execution Bar */}
        <div className="mt-6 pt-5 border-t border-slate-800/80">
          <form onSubmit={handleFormSubmit} className="flex flex-col sm:flex-row items-center gap-3">
            
            {/* Microphone Button */}
            <button
              type="button"
              onClick={toggleMic}
              disabled={!speechSupported}
              className={`w-full sm:w-auto px-5 py-3 rounded-xl font-mono text-xs font-bold flex items-center justify-center gap-2 transition-all cursor-pointer shadow-lg ${
                isListening
                  ? 'bg-rose-600 text-white animate-pulse shadow-rose-900/50'
                  : speechSupported
                  ? 'bg-cyan-500 hover:bg-cyan-400 text-slate-950 shadow-cyan-950/40'
                  : 'bg-slate-800 text-slate-500 cursor-not-allowed border border-slate-700'
              }`}
              title={speechSupported ? 'Click and speak: e.g. "FOCUS", "BREACH", "ETERNAL"' : 'Web Speech API not supported in this browser'}
            >
              {isListening ? <Mic className="w-4 h-4 text-white animate-bounce" /> : <Mic className="w-4 h-4" />}
              <span>{isListening ? 'Listening (Speak Now)...' : 'Voice Input'}</span>
            </button>

            {/* Command Text Input Bar */}
            <div className="relative flex-1 w-full">
              <input
                type="text"
                value={textInput}
                onChange={(e) => setTextInput(e.target.value)}
                placeholder="Speak or type a Command Code (e.g. FOCUS, BREACH, WAR, HOLD, ATTEST, ETERNAL)..."
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-xs sm:text-sm font-mono text-white uppercase placeholder:normal-case placeholder:text-slate-500 focus:outline-none focus:border-cyan-500 transition-colors shadow-inner"
              />
            </div>

            {/* Fire Button */}
            <button
              type="submit"
              className="w-full sm:w-auto px-6 py-3 rounded-xl bg-gradient-to-r from-cyan-400 to-indigo-500 hover:from-cyan-300 hover:to-indigo-400 text-slate-950 font-mono text-xs font-black flex items-center justify-center gap-2 transition-all cursor-pointer shadow-lg shadow-cyan-950 active:scale-95"
            >
              <Zap className="w-4 h-4 text-slate-950" />
              <span>EXECUTE CODE</span>
            </button>

          </form>

          {/* Last Spoken Speech Transcript Indicator */}
          {lastSpokenTranscript && (
            <div className="mt-2 text-[11px] font-mono text-slate-400 flex items-center gap-2">
              <span className="text-cyan-400">Heard Voice:</span>
              <span className="text-slate-200 font-bold uppercase">&ldquo;{lastSpokenTranscript}&rdquo;</span>
            </div>
          )}

          {/* Quick 1-Tap Sovereign Command Trigger Pills */}
          <div className="mt-4 flex flex-wrap items-center gap-2">
            <span className="text-[10px] font-mono text-slate-500 uppercase tracking-wider mr-1">Frequent:</span>
            {['FOCUS', 'HOLD', 'GO', 'RESUME', 'QUIET', 'SPEAK', 'BREACH', 'WAR', 'PEACE', 'ATTEST', 'UNBLOCK', 'ETERNAL'].map((code) => (
              <button
                key={code}
                onClick={() => handleExecute(code)}
                className="px-2.5 py-1 rounded-lg bg-slate-950/80 hover:bg-slate-800 border border-slate-800 hover:border-cyan-500/60 font-mono text-[11px] font-bold text-slate-300 hover:text-cyan-300 transition-all cursor-pointer active:scale-95"
              >
                {code}
              </button>
            ))}
          </div>

        </div>

        {/* Live Execution Echo Result Banner */}
        {lastResult && (
          <div className={`mt-5 p-4 rounded-xl border font-mono text-xs animate-in fade-in duration-200 ${
            lastResult.success
              ? 'bg-cyan-950/40 border-cyan-800/80 text-cyan-200'
              : 'bg-rose-950/40 border-rose-800/80 text-rose-200'
          }`}>
            <div className="flex items-center justify-between mb-1">
              <div className="flex items-center gap-2">
                {lastResult.success ? (
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                ) : (
                  <ShieldAlert className="w-4 h-4 text-rose-400 shrink-0" />
                )}
                <span className="font-bold uppercase tracking-wider">
                  {lastResult.success ? `ECHO-BACK CONFIRMED (${lastResult.latencyMs}ms)` : 'COMMAND CODE REFUSED (§1.7 / §15.1)'}
                </span>
              </div>
              {lastResult.receiptId && (
                <span className="text-[10px] text-slate-400">{lastResult.receiptId}</span>
              )}
            </div>

            <div className="text-xs text-slate-100 font-sans mt-1">
              {lastResult.echoText}
            </div>

            {lastResult.refusalReason && (
              <div className="mt-2 pt-2 border-t border-rose-900/50 text-[11px] text-rose-300 flex items-center justify-between">
                <span>Reason: {lastResult.refusalReason}</span>
                {lastResult.recognizedCodes && (
                  <span className="text-slate-400">Did you mean: {lastResult.recognizedCodes.join(', ')}?</span>
                )}
              </div>
            )}
          </div>
        )}

      </div>

      {/* ========================================================================= */}
      {/* SECTION 2: ACTIVE COMMAND STACK OVERLAY (§2.2, §7) */}
      {/* ========================================================================= */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-xl">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-4">
          <div>
            <div className="flex items-center gap-2">
              <Activity className="w-5 h-5 text-cyan-400 animate-pulse" />
              <h3 className="text-base font-mono font-bold text-white uppercase tracking-wider">
                Active Command Stack ({activeCount} / 7 Concurrency Ceiling)
              </h3>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Active command codes alter estate priority and posture everywhere simultaneously. Every code has a hard expiry.
            </p>
          </div>

          {/* Concurrency Meter */}
          <div className="flex items-center gap-2 bg-slate-950 px-3 py-1.5 rounded-xl border border-slate-800 text-xs font-mono">
            <span className="text-slate-400">Concurrency Load:</span>
            <div className="flex items-center gap-1">
              {[1, 2, 3, 4, 5, 6, 7].map((num) => (
                <span
                  key={num}
                  className={`w-2.5 h-2.5 rounded-sm transition-all ${
                    num <= activeCount
                      ? activeCount >= 6 ? 'bg-amber-400' : 'bg-cyan-400'
                      : 'bg-slate-800'
                  }`}
                />
              ))}
            </div>
            <span className="font-bold text-white ml-1">{activeCount}/7</span>
          </div>
        </div>

        {/* Stack Items Grid */}
        {activeStack.length === 0 ? (
          <div className="p-8 text-center bg-slate-950/60 rounded-xl border border-slate-800/80 font-mono text-xs text-slate-500">
            No active command codes. Estate running in baseline autonomous posture.
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {activeStack.map((entry) => {
              const isExpired = entry.status === 'EXPIRED';
              const isRevoked = entry.status === 'REVOKED';
              const isTerminal = entry.level === 'L6';
              const isEmergency = entry.level === 'L4';
              const isHeartbeat = entry.level === 'L5';

              return (
                <div
                  key={entry.receiptId}
                  className={`p-4 rounded-xl border transition-all relative overflow-hidden ${
                    isRevoked || isExpired
                      ? 'bg-slate-950/40 border-slate-900 text-slate-500 opacity-60'
                      : isTerminal
                      ? 'bg-rose-950/30 border-rose-600/80 shadow-lg shadow-rose-950/50'
                      : isEmergency
                      ? 'bg-red-950/30 border-red-600/70 shadow-lg shadow-red-950/50'
                      : isHeartbeat
                      ? 'bg-purple-950/30 border-purple-600/70 shadow-lg shadow-purple-950/50'
                      : entry.level === 'L3'
                      ? 'bg-amber-950/30 border-amber-600/70'
                      : 'bg-slate-950/80 border-slate-800 hover:border-cyan-700/60'
                  }`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-1.5">
                      <span className={`text-[10px] font-mono px-2 py-0.5 rounded font-bold ${
                        entry.level === 'L6' ? 'bg-rose-950 text-rose-300 border border-rose-800' :
                        entry.level === 'L5' ? 'bg-purple-950 text-purple-300 border border-purple-800 animate-pulse' :
                        entry.level === 'L4' ? 'bg-red-950 text-red-300 border border-red-800' :
                        entry.level === 'L3' ? 'bg-amber-950 text-amber-300 border border-amber-800' :
                        'bg-cyan-950 text-cyan-300 border border-cyan-800'
                      }`}>
                        {entry.level}
                      </span>
                      <span className="text-xs font-mono font-bold text-white tracking-wider">{entry.code}</span>
                    </div>

                    <span className={`text-[10px] font-mono px-2 py-0.5 rounded ${
                      entry.status === 'ACTIVE'
                        ? 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                        : 'bg-slate-900 text-slate-500'
                    }`}>
                      {entry.status}
                    </span>
                  </div>

                  <div className="text-[11px] font-mono text-slate-400 mb-2">
                    Scope: <strong className="text-slate-200">{entry.scope}</strong>
                  </div>

                  <div className="space-y-1 bg-slate-900/60 p-2.5 rounded-lg border border-slate-800/80 text-[10px] font-mono mb-3">
                    <div className="flex justify-between">
                      <span className="text-slate-500">Remaining TTL:</span>
                      <span className="text-cyan-400 font-bold">
                        {Math.floor(entry.remainingSeconds / 3600)}h {Math.floor((entry.remainingSeconds % 3600) / 60)}m {entry.remainingSeconds % 60}s
                      </span>
                    </div>
                    <div className="flex justify-between truncate">
                      <span className="text-slate-500">Receipt:</span>
                      <span className="text-slate-400 truncate max-w-[170px]">{entry.receiptId}</span>
                    </div>
                    {entry.debtLedgerId && (
                      <div className="flex justify-between">
                        <span className="text-amber-500">Debt Ledger:</span>
                        <span className="text-amber-400 font-bold">{entry.debtLedgerId}</span>
                      </div>
                    )}
                  </div>

                  {entry.status === 'ACTIVE' && (
                    <button
                      onClick={() => handleRevoke(entry.receiptId)}
                      className="w-full py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-400 hover:text-rose-400 border border-slate-800 hover:border-rose-800 text-[11px] font-mono font-bold flex items-center justify-center gap-1 transition-all cursor-pointer"
                    >
                      <X className="w-3.5 h-3.5" />
                      <span>REVOKE CODE</span>
                    </button>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* ========================================================================= */}
      {/* SECTION 3: THE EXHAUSTIVE 90-CODE DIRECTORY ACROSS 12 DOMAINS */}
      {/* ========================================================================= */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-xl">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-6">
          <div>
            <h3 className="text-lg font-bold text-white flex items-center gap-2">
              <Layers className="w-5 h-5 text-indigo-400" />
              <span>The Exhaustive Catalog · 90 Codes across 12 Domains</span>
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Strict grammar and semantics. Every code has a machine-enforced receipt, default TTL, confirmation tier, delegation rules, and falsifier proof.
            </p>
          </div>

          {/* Search Filter Bar */}
          <div className="relative w-full sm:w-72">
            <Search className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
            <input
              type="text"
              value={searchFilter}
              onChange={(e) => setSearchFilter(e.target.value)}
              placeholder="Search 90 codes..."
              className="w-full bg-slate-950 border border-slate-800 rounded-xl pl-9 pr-3 py-1.5 text-xs font-mono text-white focus:outline-none focus:border-cyan-500"
            />
          </div>
        </div>

        {/* Domain Filter Pills */}
        <div className="flex flex-wrap items-center gap-1.5 mb-6 pb-3 border-b border-slate-800">
          <button
            onClick={() => setSelectedDomain('ALL')}
            className={`px-2.5 py-1 rounded-lg text-xs font-mono font-bold transition-all cursor-pointer ${
              selectedDomain === 'ALL'
                ? 'bg-cyan-500 text-slate-950 shadow-sm'
                : 'bg-slate-950 text-slate-400 hover:bg-slate-800'
            }`}
          >
            All 90 Codes
          </button>
          {domains.map((d) => (
            <button
              key={d.num}
              onClick={() => setSelectedDomain(d.num)}
              className={`px-2.5 py-1 rounded-lg text-xs font-mono transition-all cursor-pointer ${
                selectedDomain === d.num
                  ? 'bg-cyan-950 text-cyan-300 border border-cyan-700 font-bold'
                  : 'bg-slate-950/60 text-slate-400 hover:bg-slate-800 border border-slate-800/80'
              }`}
            >
              {d.num}. {d.name}
            </button>
          ))}
        </div>

        {/* Codes Catalog Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredCodes.map((c) => {
            const isNeverDelegable = NEVER_DELEGABLE_CODES.has(c.code);
            return (
              <div
                key={c.code}
                className="p-4 rounded-xl bg-slate-950/80 border border-slate-800/80 hover:border-slate-700 transition-all flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="font-mono font-black text-sm text-white tracking-wider">
                      {c.code}
                    </span>
                    <div className="flex items-center gap-1">
                      <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded font-bold ${
                        c.level === 'L6' ? 'bg-rose-950 text-rose-300' :
                        c.level === 'L5' ? 'bg-purple-950 text-purple-300' :
                        c.level === 'L4' ? 'bg-red-950 text-red-300' :
                        c.level === 'L3' ? 'bg-amber-950 text-amber-300' :
                        'bg-cyan-950 text-cyan-300'
                      }`}>
                        {c.level}
                      </span>
                      <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-900 text-slate-400">
                        {c.confirmTier}
                      </span>
                      <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded font-bold ${
                        isNeverDelegable ? 'bg-rose-950 text-rose-400 border border-rose-800' : 'bg-slate-900 text-slate-400'
                      }`}>
                        {c.delegation}
                      </span>
                    </div>
                  </div>

                  <div className="text-[10px] font-mono text-cyan-400/90 mb-1">
                    Domain {c.domainNumber} · {c.domain}
                  </div>

                  <p className="text-xs text-slate-300 font-sans mb-3 leading-relaxed">
                    {c.effect}
                  </p>

                  <div className="p-2 rounded bg-slate-900/60 border border-slate-800/80 text-[10px] font-mono space-y-0.5 text-slate-400 mb-3">
                    <div className="flex justify-between">
                      <span>Default TTL:</span>
                      <span className="text-slate-200">{c.ttlDisplay}</span>
                    </div>
                    <div className="truncate">
                      <span>Falsifier:</span> <span className="text-slate-500">{c.falsifierProof}</span>
                    </div>
                  </div>
                </div>

                <button
                  onClick={() => handleExecute(c.code)}
                  className="w-full py-1.5 rounded-lg bg-slate-900 hover:bg-cyan-950 text-slate-300 hover:text-cyan-300 border border-slate-800 hover:border-cyan-700 text-xs font-mono font-bold flex items-center justify-center gap-1.5 transition-all cursor-pointer active:scale-95"
                >
                  <Zap className="w-3.5 h-3.5 text-cyan-400" />
                  <span>FIRE {c.code}</span>
                </button>
              </div>
            );
          })}
        </div>

      </div>

    </div>
  );
};
