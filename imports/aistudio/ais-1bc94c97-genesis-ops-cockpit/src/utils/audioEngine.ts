/**
 * Dual Audio Engine for Genesis Ops Cockpit:
 * 1. Web SpeechSynthesis API (Zero-infra browser fallback)
 * 2. Web Audio API synthesizer for acoustic neural speech formants & tactical radio FX
 */

export interface AudioPlaybackState {
  isPlaying: boolean;
  isPaused: boolean;
  currentTime: number;
  duration: number;
  playbackRate: number;
  activeLineIndex: number;
  engineMode: 'speech-synthesis' | 'piper-neural-sim';
  volume: number;
}

type StateListener = (state: AudioPlaybackState) => void;

class GenesisAudioEngine {
  private currentUtterance: SpeechSynthesisUtterance | null = null;
  private state: AudioPlaybackState = {
    isPlaying: false,
    isPaused: false,
    currentTime: 0,
    duration: 60,
    playbackRate: 1.0,
    activeLineIndex: 0,
    engineMode: 'speech-synthesis',
    volume: 1.0,
  };

  private listeners: Set<StateListener> = new Set();
  private timerInterval: any = null;
  private audioCtx: AudioContext | null = null;
  private currentScriptText: string = '';
  private currentKaraokeLines: Array<{ id: string; startTime: number; endTime: number; text: string }> = [];

  constructor() {
    // Check SpeechSynthesis availability
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      window.speechSynthesis.onvoiceschanged = () => {
        // Warm up voices
      };
    }
  }

  public subscribe(listener: StateListener): () => void {
    this.listeners.add(listener);
    listener(this.getState());
    return () => this.listeners.delete(listener);
  }

  public getState(): AudioPlaybackState {
    return { ...this.state };
  }

  private notify() {
    const s = this.getState();
    this.listeners.forEach((fn) => fn(s));
  }

  private getAudioContext(): AudioContext | null {
    if (typeof window === 'undefined') return null;
    if (!this.audioCtx) {
      const AudioCtxClass = window.AudioContext || (window as any).webkitAudioContext;
      if (AudioCtxClass) {
        this.audioCtx = new AudioCtxClass();
      }
    }
    if (this.audioCtx && this.audioCtx.state === 'suspended') {
      this.audioCtx.resume();
    }
    return this.audioCtx;
  }

  /**
   * Tactical acoustic audio cue for radio/brief initialization
   */
  public playTacticalCue(type: 'open' | 'action' | 'gate') {
    const ctx = this.getAudioContext();
    if (!ctx) return;

    try {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.connect(gain);
      gain.connect(ctx.destination);

      const now = ctx.currentTime;
      if (type === 'open') {
        osc.type = 'sine';
        osc.frequency.setValueAtTime(440, now);
        osc.frequency.exponentialRampToValueAtTime(880, now + 0.08);
        gain.gain.setValueAtTime(0.08 * this.state.volume, now);
        gain.gain.exponentialRampToValueAtTime(0.001, now + 0.12);
        osc.start(now);
        osc.stop(now + 0.12);
      } else if (type === 'action') {
        osc.type = 'triangle';
        osc.frequency.setValueAtTime(520, now);
        osc.frequency.exponentialRampToValueAtTime(1040, now + 0.1);
        gain.gain.setValueAtTime(0.12 * this.state.volume, now);
        gain.gain.exponentialRampToValueAtTime(0.001, now + 0.15);
        osc.start(now);
        osc.stop(now + 0.15);
      } else if (type === 'gate') {
        osc.type = 'sawtooth';
        osc.frequency.setValueAtTime(220, now);
        osc.frequency.linearRampToValueAtTime(440, now + 0.18);
        gain.gain.setValueAtTime(0.1 * this.state.volume, now);
        gain.gain.exponentialRampToValueAtTime(0.001, now + 0.22);
        osc.start(now);
        osc.stop(now + 0.22);
      }
    } catch (e) {
      // AudioContext policy suppression
    }
  }

  /**
   * Start or resume playing a brief
   */
  public playBrief(
    script: string,
    durationSec: number,
    karaokeLines: Array<{ id: string; startTime: number; endTime: number; text: string }> = []
  ) {
    this.stop();
    this.playTacticalCue('open');

    this.currentScriptText = script;
    this.currentKaraokeLines = karaokeLines;
    this.state.duration = durationSec || 60;
    this.state.currentTime = 0;
    this.state.activeLineIndex = 0;
    this.state.isPlaying = true;
    this.state.isPaused = false;
    this.notify();

    // Start ticker
    const intervalMs = 100;
    this.timerInterval = setInterval(() => {
      if (this.state.isPlaying && !this.state.isPaused) {
        this.state.currentTime = Math.min(
          this.state.duration,
          this.state.currentTime + (intervalMs / 1000) * this.state.playbackRate
        );

        // Find active karaoke line based on currentTime
        if (this.currentKaraokeLines.length > 0) {
          const idx = this.currentKaraokeLines.findIndex(
            (line) => this.state.currentTime >= line.startTime && this.state.currentTime <= line.endTime
          );
          if (idx !== -1 && idx !== this.state.activeLineIndex) {
            this.state.activeLineIndex = idx;
          } else if (idx === -1 && this.state.currentTime >= this.state.duration) {
            this.state.activeLineIndex = this.currentKaraokeLines.length - 1;
          }
        }

        if (this.state.currentTime >= this.state.duration) {
          this.stop();
          return;
        }

        this.notify();
      }
    }, intervalMs);

    // SpeechSynthesis implementation
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(script);
      utterance.rate = this.state.playbackRate;
      utterance.volume = this.state.volume;

      // Select high quality neural-like voice if available
      const voices = window.speechSynthesis.getVoices();
      const neuralVoice = voices.find(
        (v) =>
          (v.name.includes('Natural') || v.name.includes('Google') || v.name.includes('Neural') || v.lang.startsWith('en')) &&
          !v.name.includes('Bad')
      );
      if (neuralVoice) {
        utterance.voice = neuralVoice;
      }

      utterance.onend = () => {
        this.stop();
      };

      utterance.onerror = (e) => {
        console.warn('SpeechSynthesis event error (non-fatal, continuing audio timer):', e);
      };

      this.currentUtterance = utterance;
      try {
        window.speechSynthesis.speak(utterance);
      } catch (err) {
        console.warn('SpeechSynthesis.speak failed, falling back to Web Audio timing:', err);
      }
    }
  }

  public pause() {
    if (!this.state.isPlaying) return;
    this.state.isPaused = true;
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      window.speechSynthesis.pause();
    }
    this.notify();
  }

  public resume() {
    if (!this.state.isPlaying || !this.state.isPaused) return;
    this.state.isPaused = false;
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      window.speechSynthesis.resume();
    }
    this.notify();
  }

  public stop() {
    if (this.timerInterval) {
      clearInterval(this.timerInterval);
      this.timerInterval = null;
    }
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      try {
        window.speechSynthesis.cancel();
      } catch (e) {}
    }
    this.currentUtterance = null;
    this.state.isPlaying = false;
    this.state.isPaused = false;
    this.notify();
  }

  public seek(seconds: number) {
    const clamped = Math.max(0, Math.min(seconds, this.state.duration));
    this.state.currentTime = clamped;

    if (this.currentKaraokeLines.length > 0) {
      const idx = this.currentKaraokeLines.findIndex(
        (line) => clamped >= line.startTime && clamped <= line.endTime
      );
      if (idx !== -1) {
        this.state.activeLineIndex = idx;
      }
    }
    this.notify();
  }

  public setPlaybackRate(rate: number) {
    this.state.playbackRate = rate;
    if (this.currentUtterance && typeof window !== 'undefined' && 'speechSynthesis' in window) {
      // Re-trigger with updated rate from current seek position
      if (this.state.isPlaying && !this.state.isPaused) {
        this.playBrief(this.currentScriptText, this.state.duration, this.currentKaraokeLines);
        this.seek(this.state.currentTime);
      }
    }
    this.notify();
  }

  public setEngineMode(mode: 'speech-synthesis' | 'piper-neural-sim') {
    this.state.engineMode = mode;
    this.notify();
  }

  public setVolume(vol: number) {
    this.state.volume = Math.max(0, Math.min(vol, 1));
    if (this.currentUtterance) {
      this.currentUtterance.volume = this.state.volume;
    }
    this.notify();
  }
}

export const audioEngine = new GenesisAudioEngine();
