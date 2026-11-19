import React, { useState, useRef, useEffect, useCallback } from 'react';
import {
  Mic,
  Square,
  X,
  Volume2,
  VolumeX,
  Crosshair,
  RefreshCw,
  Radio,
} from 'lucide-react';
import type {
  Voice2100SpeculateResult,
  Voice2100CandidateAction,
} from '../engine/optimusAndReactor';
import type { FormationId } from '../engine/estateRules';
import {
  createBrowserSpeechRecognizer,
  playSovereignChime,
  type BrowserSpeechRecognizerHandle,
} from '../utils/sovereignAudio';

export interface VoiceStageActionPayload {
  targetNodeId: string;
  actionKind: Voice2100CandidateAction['actionKind'];
  targetTab?: 'beast' | 'academy' | 'standards' | 'catalog' | 'omega' | 'io' | 'projector' | 'synapse' | 'reactor' | 'optimus' | 'fleet' | 'legion' | 'flow' | 'greenlane' | 'chronos';
  formation?: FormationId;
  repo?: string;
  summaryText: string;
}

interface VoiceCommandDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  onExecuteVoiceAction: (payload: VoiceStageActionPayload) => Promise<string>;
  onPlayBriefing: () => Promise<void>;
  onStopBriefing: () => void;
  isPlayingBriefing: boolean;
  briefingScript: string | null;
  briefingAudioMode: string | null;
}

const CAPTAIN_VOICE_PRESETS: Array<{
  label: string;
  utterance: string;
}> = [
  {
    label: 'The Beast & Rego Dials',
    utterance: 'Open the Beast fractal proof, Rego policy dials, Bitwarden and free lanes',
  },
  {
    label: 'IO & Single Work Graph',
    utterance: 'Open IO engine work graph and persistent real-name ownership',
  },
  {
    label: 'Swarm Synapse & Reassign',
    utterance: 'Open Stigmergic Swarm Synapse and Mac offline reassignment proof',
  },
  {
    label: 'Sync Everything to Argon',
    utterance: 'Sync everything to Argon',
  },
  {
    label: 'Open Face & Fleet Movie',
    utterance: 'Open Face and Fleet register movie and isometric world',
  },
  {
    label: 'Verify Optimus Integrity',
    utterance: 'Verify Optimus signed evidence and release lock on chidionyema/idp',
  },
  {
    label: 'Adversarial Audit #2468',
    utterance: 'Run Adversarial formation on idp 2468 vault external-secret',
  },
  {
    label: 'Sweep 600s Watchdog',
    utterance: 'Sweep FLOW 600s watchdog and fence stagnant worker leases',
  },
  {
    label: 'Test <0.90 Clarify Gate',
    utterance: 'fix main',
  },
];

export const VoiceCommandDrawer: React.FC<VoiceCommandDrawerProps> = ({
  isOpen,
  onClose,
  onExecuteVoiceAction,
  onPlayBriefing,
  onStopBriefing,
  isPlayingBriefing,
  briefingScript,
  briefingAudioMode,
}) => {
  const [directiveText, setDirectiveText] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [isDispatching, setIsDispatching] = useState(false);
  const [statusNotice, setStatusNotice] = useState<string | null>(null);
  const [statusError, setStatusError] = useState<string | null>(null);
  const [speculation, setSpeculation] = useState<Voice2100SpeculateResult | null>(null);
  const [chimesEnabled, setChimesEnabled] = useState(true);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const recognizerRef = useRef<BrowserSpeechRecognizerHandle | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const audioCtxRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const spectrumCanvasRef = useRef<HTMLCanvasElement | null>(null);

  const cleanupAudioCapture = useCallback(() => {
    if (recognizerRef.current) {
      recognizerRef.current.stop();
      recognizerRef.current = null;
    }
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      try {
        mediaRecorderRef.current.stop();
      } catch {
        // Ignore
      }
    }
    mediaRecorderRef.current = null;
    if (audioCtxRef.current) {
      audioCtxRef.current.close().catch(() => {});
      audioCtxRef.current = null;
    }
    analyserRef.current = null;
  }, []);

  useEffect(() => {
    if (!isOpen) {
      cleanupAudioCapture();
      setIsRecording(false);
      return;
    }
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        cleanupAudioCapture();
        onClose();
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [isOpen, cleanupAudioCapture, onClose]);

  // Live 28-bar Web Audio API + Acoustic Telemetry Spectrum Visualizer
  useEffect(() => {
    if (!isOpen) return;
    const canvas = spectrumCanvasRef.current;
    if (!canvas) return;
    const ctx2d = canvas.getContext('2d');
    if (!ctx2d) return;

    let rafId = 0;
    const freqData = new Uint8Array(64);

    const renderBars = (nowMs: number) => {
      const w = canvas.width;
      const h = canvas.height;
      ctx2d.clearRect(0, 0, w, h);

      const barCount = 28;
      const gap = 4;
      const barWidth = Math.max(4, (w - gap * (barCount - 1)) / barCount);

      const analyser = analyserRef.current;
      if (analyser && isRecording) {
        analyser.getByteFrequencyData(freqData);
      }

      for (let i = 0; i < barCount; i++) {
        let norm = 0.12;
        if (analyser && isRecording) {
          norm = Math.max(0.12, (freqData[i] || 0) / 255);
        } else if (isPlayingBriefing || isTranscribing) {
          const wave =
            Math.sin(nowMs * 0.008 + i * 0.45) * 0.35 +
            Math.cos(nowMs * 0.013 - i * 0.25) * 0.22 +
            0.45;
          norm = Math.max(0.14, Math.min(0.95, wave));
        } else if (speculation && speculation.ok) {
          norm = 0.16 + Math.sin(nowMs * 0.003 + i * 0.3) * 0.06;
        }

        const barHeight = Math.max(4, norm * (h - 6));
        const x = i * (barWidth + gap);
        const y = (h - barHeight) / 2;

        if (isRecording) {
          ctx2d.fillStyle = '#f43f5e';
        } else if (isPlayingBriefing) {
          ctx2d.fillStyle = '#f59e0b';
        } else if (speculation && speculation.ok && !speculation.clarificationNeeded) {
          ctx2d.fillStyle = '#06b6d4';
        } else {
          ctx2d.fillStyle = '#475569';
        }

        ctx2d.beginPath();
        ctx2d.roundRect(x, y, barWidth, barHeight, 2);
        ctx2d.fill();
      }

      rafId = window.requestAnimationFrame(renderBars);
    };

    rafId = window.requestAnimationFrame(renderBars);
    return () => window.cancelAnimationFrame(rafId);
  }, [isOpen, isRecording, isPlayingBriefing, isTranscribing, speculation]);

  // Live Speculative Compiler (`POST /api/voice/speculate` — `voice-intent.v2`)
  useEffect(() => {
    if (!isOpen) return;
    const trimmed = directiveText.trim();
    if (trimmed.length < 2) {
      setSpeculation(null);
      return;
    }

    const ctrl = new AbortController();
    const timer = window.setTimeout(async () => {
      try {
        const res = await fetch('/api/voice/speculate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ transcript: trimmed, sessionId: 'founder-voice-stage-01' }),
          signal: ctrl.signal,
        });
        const data = await res.json();
        if (!res.ok) {
          setSpeculation(null);
          setStatusError(data.message || 'Schema v2 armor rejected untrusted directive.');
          playSovereignChime('refuse', chimesEnabled);
          return;
        }
        setStatusError(null);
        const parsed = data as Voice2100SpeculateResult;
        setSpeculation(parsed);
        if (parsed.ok) {
          playSovereignChime(parsed.clarificationNeeded ? 'clarify' : 'lock', chimesEnabled);
        }
      } catch {
        // Ignore aborted intermediate keystrokes
      }
    }, 95);

    return () => {
      ctrl.abort();
      window.clearTimeout(timer);
    };
  }, [directiveText, isOpen, chimesEnabled]);

  if (!isOpen) return null;

  const startRecording = async () => {
    setStatusError(null);
    setStatusNotice(null);
    let capturedViaBrowserSpeech = false;

    // 1. Start native low-latency Browser SpeechRecognition when available
    const speechRec = createBrowserSpeechRecognizer({
      onTranscript: (text) => {
        capturedViaBrowserSpeech = true;
        setDirectiveText(text);
      },
      onError: () => {
        // Handled cleanly by MediaRecorder / manual input fallback
      },
      onEnd: () => {},
    });
    if (speechRec.supported) {
      recognizerRef.current = speechRec;
      speechRec.start();
    }

    // 2. Capture live microphone stream for Web Audio spectrum + server Gemini 3.5 Transcribe
    try {
      if (!navigator.mediaDevices?.getUserMedia) {
        throw new Error('MediaDevices unavailable in this browser context');
      }
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

      const AudioCtx =
        window.AudioContext ||
        (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
      if (AudioCtx) {
        const actx = new AudioCtx();
        const source = actx.createMediaStreamSource(stream);
        const analyser = actx.createAnalyser();
        analyser.fftSize = 128;
        source.connect(analyser);
        audioCtxRef.current = actx;
        analyserRef.current = analyser;
      }

      const recorder = new MediaRecorder(stream);
      chunksRef.current = [];
      recorder.ondataavailable = (ev) => {
        if (ev.data.size > 0) chunksRef.current.push(ev.data);
      };
      recorder.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        if (audioCtxRef.current) {
          audioCtxRef.current.close().catch(() => {});
          audioCtxRef.current = null;
        }
        analyserRef.current = null;

        const blob = new Blob(chunksRef.current, { type: recorder.mimeType || 'audio/webm' });
        if (blob.size === 0) return;

        setIsTranscribing(true);
        try {
          const arrayBuf = await blob.arrayBuffer();
          const bytes = new Uint8Array(arrayBuf);
          let binary = '';
          for (let i = 0; i < bytes.byteLength; i++) {
            binary += String.fromCharCode(bytes[i]);
          }
          const audioBase64 = btoa(binary);
          const res = await fetch('/api/voice/transcribe', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ audioBase64, mimeType: blob.type || 'audio/webm' }),
          });
          const data = await res.json();
          if (data.ok && data.transcript) {
            setDirectiveText(data.transcript);
            setStatusNotice('Transcribed via Gemini 3.5 Transcribe (E1).');
          } else if (!capturedViaBrowserSpeech) {
            setStatusNotice(
              data.notice ||
                'Cloud ASR unprovisioned (Authority U); select a Captain Vocalized Utterance or type directly.'
            );
          }
        } catch {
          if (!capturedViaBrowserSpeech) {
            setStatusNotice('Select a Captain Vocalized Utterance below or dictate directly.');
          }
        } finally {
          setIsTranscribing(false);
        }
      };

      mediaRecorderRef.current = recorder;
      recorder.start();
      setIsRecording(true);
    } catch {
      if (speechRec.supported) {
        setIsRecording(true);
        setStatusNotice('Browser SpeechRecognition active — speak your Captain directive.');
      } else {
        setStatusNotice(
          'Hardware microphone not attached in this environment — click any Captain Vocalized Utterance below or type directly.'
        );
      }
    }
  };

  const stopRecording = () => {
    if (recognizerRef.current) {
      recognizerRef.current.stop();
      recognizerRef.current = null;
    }
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
    }
    setIsRecording(false);
  };

  const runAction = async (payload: VoiceStageActionPayload) => {
    setIsDispatching(true);
    setStatusError(null);
    playSovereignChime('execute', chimesEnabled);
    try {
      const msg = await onExecuteVoiceAction(payload);
      setStatusNotice(msg);
      setDirectiveText('');
      setSpeculation(null);
      if (payload.actionKind === 'NAVIGATE_TAB' || payload.actionKind === 'EXECUTE_LEGION') {
        onClose();
      }
    } catch (err) {
      setStatusError(err instanceof Error ? err.message : 'Failed to execute sovereign directive');
    } finally {
      setIsDispatching(false);
    }
  };

  const handleDispatch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!speculation || !speculation.ok) {
      setStatusError('Speak, click a Captain preset, or enter a valid directive first.');
      return;
    }
    if (speculation.clarificationNeeded) {
      setStatusError('Confidence < 0.90 floor: choose one of the clarified sovereign intents below.');
      return;
    }
    await runAction({
      targetNodeId: speculation.targetNodeId,
      actionKind: speculation.actionKind,
      targetTab: speculation.targetTab,
      formation: speculation.formation,
      repo: speculation.repo,
      summaryText: directiveText.trim() || speculation.summary,
    });
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="voice-modal-title"
      onClick={(e) => {
        if (e.target === e.currentTarget) {
          cleanupAudioCapture();
          onClose();
        }
      }}
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/75"
    >
      <div className="w-full max-w-2xl bg-white dark:bg-[#080D1A] border border-slate-200 dark:border-slate-800 rounded-2xl shadow-2xl overflow-hidden">
        {/* Modal Header */}
        <div className="px-5 py-4 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between gap-3">
          <div>
            <div className="text-[11px] font-mono text-amber-600 dark:text-amber-400">
              VOICE 2100 · SPECULATIVE INTENT COMPILER (voice-intent.v2)
            </div>
            <h2 id="voice-modal-title" className="text-base font-semibold text-slate-900 dark:text-slate-100">
              Sovereign Fleet Captain Voice Stage
            </h2>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setChimesEnabled((v) => !v)}
              aria-label={chimesEnabled ? 'Mute telemetry chimes' : 'Enable telemetry chimes'}
              className="px-2.5 py-1.5 text-[11px] font-mono text-slate-600 dark:text-slate-300 bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg"
            >
              {chimesEnabled ? 'SFX ON' : 'SFX MUTE'}
            </button>
            <button
              type="button"
              onClick={() => {
                cleanupAudioCapture();
                onClose();
              }}
              aria-label="Close voice command stage"
              className="p-1.5 text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 rounded-lg"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        <div className="p-5 space-y-4 max-h-[82vh] overflow-y-auto">
          {/* Acoustic Spectrum Bar + Mic / Captain Sitrep Controls */}
          <div className="p-3.5 bg-slate-50 dark:bg-[#0B101D] border border-slate-200 dark:border-slate-800 rounded-xl space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex flex-wrap items-center gap-2">
                {!isRecording ? (
                  <button
                    type="button"
                    onClick={startRecording}
                    disabled={isTranscribing}
                    className="inline-flex items-center gap-2 px-3.5 py-2 text-xs font-semibold text-slate-950 bg-amber-400 hover:bg-amber-300 rounded-lg transition-colors whitespace-nowrap shrink-0"
                  >
                    <Mic className="w-3.5 h-3.5" aria-hidden="true" />
                    {isTranscribing ? 'Transcribing…' : 'Engage Live Mic'}
                  </button>
                ) : (
                  <button
                    type="button"
                    onClick={stopRecording}
                    className="inline-flex items-center gap-2 px-3.5 py-2 text-xs font-semibold text-white bg-rose-600 hover:bg-rose-500 rounded-lg transition-colors whitespace-nowrap shrink-0"
                  >
                    <Square className="w-3.5 h-3.5" aria-hidden="true" />
                    Stop &amp; Lock Utterance
                  </button>
                )}

                {!isPlayingBriefing ? (
                  <button
                    type="button"
                    onClick={onPlayBriefing}
                    className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-medium text-slate-700 dark:text-slate-200 bg-white dark:bg-slate-900 hover:bg-slate-100 dark:hover:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg transition-colors whitespace-nowrap shrink-0"
                  >
                    <Volume2 className="w-3.5 h-3.5 text-cyan-600 dark:text-cyan-400" aria-hidden="true" />
                    Play Sitrep
                  </button>
                ) : (
                  <button
                    type="button"
                    onClick={onStopBriefing}
                    className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-semibold text-white bg-rose-600 hover:bg-rose-500 rounded-lg transition-colors whitespace-nowrap shrink-0"
                  >
                    <VolumeX className="w-3.5 h-3.5" aria-hidden="true" />
                    Stop Audio
                  </button>
                )}
              </div>

              <span className="text-[11px] font-mono text-slate-500 dark:text-slate-400">
                {isRecording
                  ? 'LISTENING · ACOUSTIC STREAM'
                  : isPlayingBriefing
                    ? `VOCALIZING · ${briefingAudioMode || 'SPEECH'}`
                    : 'FLOOR >= 0.90 · SCHEMA v2 ARMORED'}
              </span>
            </div>

            <canvas
              ref={spectrumCanvasRef}
              width={560}
              height={38}
              aria-hidden="true"
              className="w-full h-9 rounded-lg bg-slate-900/90 px-2"
            />

            {briefingScript && (
              <div className="pt-2 border-t border-slate-200 dark:border-slate-800 text-xs text-slate-700 dark:text-slate-300 leading-relaxed">
                <span className="font-mono text-amber-600 dark:text-amber-400 mr-1.5">
                  CAPTAIN SITREP:
                </span>
                {briefingScript}
              </div>
            )}
          </div>

          {/* 1-Click Captain Vocalized Utterance Presets (Zero-Mic Deterministic QA) */}
          <div className="space-y-1.5">
            <div className="flex items-center gap-1.5 text-xs font-medium text-slate-600 dark:text-slate-400">
              <Radio className="w-3.5 h-3.5 text-cyan-600 dark:text-cyan-400" aria-hidden="true" />
              <span>Instant Captain Utterances (Simulate Spoken Command):</span>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {CAPTAIN_VOICE_PRESETS.map((p) => (
                <button
                  key={p.label}
                  type="button"
                  onClick={() => {
                    setStatusNotice(null);
                    setStatusError(null);
                    setDirectiveText(p.utterance);
                  }}
                  className="px-2.5 py-1.5 text-xs font-medium text-slate-700 dark:text-slate-200 bg-slate-100 dark:bg-slate-900 hover:bg-amber-400/20 dark:hover:bg-amber-400/15 border border-slate-200 dark:border-slate-800 hover:border-amber-500/50 rounded-lg transition-colors whitespace-nowrap"
                >
                  {p.label}
                </button>
              ))}
            </div>
          </div>

          {/* Speculative Directive Form */}
          <form onSubmit={handleDispatch} className="space-y-3">
            <div>
              <label
                htmlFor="founder-directive-input"
                className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1"
              >
                Spoken or Typed Sovereign Utterance
              </label>
              <textarea
                id="founder-directive-input"
                rows={2}
                value={directiveText}
                onChange={(e) => setDirectiveText(e.target.value)}
                placeholder="Speak or type e.g. 'Verify Optimus signed evidence', 'Run Adversarial on idp 2468 vault', or 'fix main'…"
                className="w-full px-3.5 py-2.5 text-xs bg-white dark:bg-[#050811] border border-slate-300 dark:border-slate-700 rounded-xl text-slate-900 dark:text-slate-100 leading-relaxed focus:outline-none focus:border-amber-400"
              />
            </div>

            {/* Live Speculative Compiler Readout */}
            {speculation && speculation.ok && (
              <div className="p-3.5 rounded-xl bg-slate-50 dark:bg-[#0B101D] border border-slate-200 dark:border-slate-800 space-y-2">
                <div className="flex flex-wrap items-center justify-between gap-2 text-xs font-mono tabular-nums">
                  <span className="text-cyan-700 dark:text-cyan-400 font-semibold">
                    INTENT: {speculation.intent} → {speculation.targetNodeId}
                  </span>
                  <span
                    className={
                      speculation.clarificationNeeded
                        ? 'text-amber-600 dark:text-amber-400 font-semibold'
                        : 'text-emerald-600 dark:text-emerald-400 font-semibold'
                    }
                  >
                    CONFIDENCE {(speculation.confidence * 100).toFixed(0)}%{' '}
                    {speculation.clarificationNeeded ? '(<90% CLARIFY)' : '(LOCKED >=90%)'}
                  </span>
                </div>
                <p className="text-xs text-slate-600 dark:text-slate-300">{speculation.summary}</p>

                {/* 0.90 Clarification Handshake Buttons */}
                {speculation.clarificationNeeded && speculation.clarifyRow && (
                  <div className="pt-2 border-t border-slate-200 dark:border-slate-800 space-y-2">
                    <div className="text-[11px] font-mono text-amber-600 dark:text-amber-300">
                      {speculation.clarifyRow.subject} · kind=clarify — {speculation.clarifyRow.question}
                    </div>
                    <div className="flex flex-col sm:flex-row flex-wrap gap-2">
                      {speculation.clarifyRow.candidateActions.map((cand) => (
                        <button
                          key={cand.label}
                          type="button"
                          disabled={isDispatching}
                          onClick={() =>
                            runAction({
                              targetNodeId: cand.targetNodeId,
                              actionKind: cand.actionKind,
                              targetTab: cand.targetTab,
                              formation: cand.formation,
                              repo: cand.repo,
                              summaryText: cand.utterance,
                            })
                          }
                          className="px-3 py-2 text-xs font-medium text-left text-slate-900 dark:text-amber-100 bg-amber-50 dark:bg-slate-900 hover:bg-amber-400 hover:text-slate-950 border border-amber-300 dark:border-amber-500/40 rounded-lg transition-colors"
                        >
                          {cand.label}
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {statusError && (
              <div
                role="alert"
                className="p-3 text-xs font-mono text-rose-700 dark:text-rose-300 bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800 rounded-lg"
              >
                {statusError}
              </div>
            )}

            {statusNotice && (
              <div
                role="status"
                className="p-3 text-xs font-mono text-cyan-800 dark:text-cyan-300 bg-cyan-50 dark:bg-cyan-950/30 border border-cyan-200 dark:border-cyan-800/70 rounded-lg"
              >
                {statusNotice}
              </div>
            )}

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-200 dark:border-slate-800">
              <button
                type="button"
                onClick={() => {
                  cleanupAudioCapture();
                  onClose();
                }}
                className="px-3.5 py-2 text-xs font-medium text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 rounded-lg"
              >
                Close Stage
              </button>
              <button
                type="submit"
                disabled={
                  isDispatching ||
                  isTranscribing ||
                  !speculation ||
                  !speculation.ok ||
                  speculation.clarificationNeeded
                }
                className="inline-flex items-center gap-2 px-4 py-2 text-xs font-semibold text-slate-950 bg-amber-400 hover:bg-amber-300 disabled:opacity-40 rounded-lg transition-colors whitespace-nowrap shrink-0"
              >
                {isDispatching ? (
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" aria-hidden="true" />
                ) : (
                  <Crosshair className="w-3.5 h-3.5" aria-hidden="true" />
                )}
                {isDispatching ? 'Executing Intent…' : 'Execute Locked Intent'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};
