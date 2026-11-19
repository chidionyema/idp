/**
 * Rosicrucian Acoustic Harmonics Synthesizer (WebAudio API).
 * Strictly silent/off until explicitly enabled by user interaction.
 * Maps Middle Pillar equilibrium, Path 19 Lydian/Tritone contention,
 * and Key-C Malkuth Cathedral Bell harmonics.
 */

export interface AcousticState {
  active: boolean;
  omega: number;
  duelActive: boolean;
  malkuthSealed: boolean;
}

class CrescendoHarmonicsEngine {
  private ctx: AudioContext | null = null;
  private masterGain: GainNode | null = null;
  private oscillators: OscillatorNode[] = [];
  private active = false;

  public startOrUpdate(state: AcousticState): boolean {
    if (typeof window === 'undefined') return false;
    const AudioCtx =
      window.AudioContext ||
      (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
    if (!AudioCtx) return false;

    if (!this.ctx) {
      this.ctx = new AudioCtx();
    }
    if (this.ctx.state === 'suspended') {
      void this.ctx.resume();
    }

    // Clear previous voices cleanly before retuning
    this.clearVoices();

    const master = this.ctx.createGain();
    master.gain.setValueAtTime(0.035, this.ctx.currentTime); // Gentle ambient drone
    master.connect(this.ctx.destination);
    this.masterGain = master;

    // Middle Pillar Just-Intonation Fifth & Octave Drone (64 -> 128 -> 192 -> 256 Hz)
    // Detunes subtly if |Omega| deviates from equilibrium
    const detuneCents = Math.max(-45, Math.min(45, state.omega * 60));
    const freqs = state.duelActive
      ? [64, 128, 270, 384] // Path 19 Chesed/Geburah Tritone/Lydian tension
      : state.malkuthSealed
        ? [64, 128, 192, 256, 320, 528] // Resolved Major Third + 528 Hz Witness Bell
        : [64, 128, 192, 256];

    for (let i = 0; i < freqs.length; i++) {
      const osc = this.ctx.createOscillator();
      const gain = this.ctx.createGain();
      osc.type = i === 0 ? 'sine' : freqs[i] === 528 ? 'triangle' : 'sine';
      osc.frequency.setValueAtTime(freqs[i], this.ctx.currentTime);
      if (i > 0) {
        osc.detune.setValueAtTime(detuneCents, this.ctx.currentTime);
      }
      gain.gain.setValueAtTime(i === 0 ? 0.45 : freqs[i] === 528 ? 0.22 : 0.25, this.ctx.currentTime);
      osc.connect(gain);
      gain.connect(master);
      osc.start();
      this.oscillators.push(osc);
    }

    this.active = true;
    return true;
  }

  public strikeMalkuthWitnessBell(): void {
    if (!this.ctx || !this.active) return;
    const now = this.ctx.currentTime;
    for (const freq of [32, 528]) {
      const osc = this.ctx.createOscillator();
      const env = this.ctx.createGain();
      osc.type = freq === 32 ? 'sine' : 'triangle';
      osc.frequency.setValueAtTime(freq, now);
      env.gain.setValueAtTime(0.06, now);
      env.gain.exponentialRampToValueAtTime(0.0001, now + 1.8);
      osc.connect(env);
      env.connect(this.ctx.destination);
      osc.start(now);
      osc.stop(now + 1.85);
    }
  }

  public stop(): void {
    this.clearVoices();
    this.active = false;
  }

  public isRunning(): boolean {
    return this.active;
  }

  private clearVoices(): void {
    for (const osc of this.oscillators) {
      try {
        osc.stop();
        osc.disconnect();
      } catch {
        // Ignore already stopped oscillators
      }
    }
    this.oscillators = [];
    if (this.masterGain) {
      try {
        this.masterGain.disconnect();
      } catch {
        // Ignore
      }
      this.masterGain = null;
    }
  }
}

export const crescendoAudio = new CrescendoHarmonicsEngine();
