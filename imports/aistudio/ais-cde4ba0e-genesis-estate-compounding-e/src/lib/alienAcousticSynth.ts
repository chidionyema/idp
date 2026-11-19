/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 * 
 * ALIEN 2100 ACOUSTIC & VOICE SYNTHESIZER
 * Procedural Web Audio API sound design + synthetic telegraphic voice echo-back.
 * Generates resonant crystalline chimes (L1-L3), deep planetary sub-harmonics (L4),
 * biometric dual-chamber heartbeats (L5), and terminal monolithic drops (L6).
 */

class AlienAcousticSynth {
  private audioCtx: AudioContext | null = null;
  private isAudioUnlocked: boolean = false;
  private voiceEnabled: boolean = true;
  private soundEnabled: boolean = true;

  constructor() {
    // Lazy initialize on first user interaction
  }

  private initContext(): AudioContext | null {
    if (typeof window === 'undefined') return null;
    if (!this.audioCtx) {
      const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
      if (AudioContextClass) {
        this.audioCtx = new AudioContextClass();
      }
    }
    if (this.audioCtx && this.audioCtx.state === 'suspended') {
      this.audioCtx.resume();
    }
    return this.audioCtx;
  }

  public unlockAudio(): void {
    const ctx = this.initContext();
    if (ctx && ctx.state === 'running') {
      this.isAudioUnlocked = true;
    }
  }

  public setVoiceEnabled(enabled: boolean): void {
    this.voiceEnabled = enabled;
  }

  public setSoundEnabled(enabled: boolean): void {
    this.soundEnabled = enabled;
  }

  /**
   * Procedural Alien 2100 Pulse Chime / Drone
   */
  public playCommandPulse(level: 'L1' | 'L2' | 'L3' | 'L4' | 'L5' | 'L6'): void {
    if (!this.soundEnabled) return;
    const ctx = this.initContext();
    if (!ctx) return;

    const now = ctx.currentTime;

    if (level === 'L1' || level === 'L2') {
      // Crystalline Dual-Tone FM Chime (432Hz + 648Hz)
      const osc1 = ctx.createOscillator();
      const osc2 = ctx.createOscillator();
      const gainNode = ctx.createGain();
      const filter = ctx.createBiquadFilter();

      osc1.type = 'sine';
      osc2.type = 'triangle';
      osc1.frequency.setValueAtTime(432, now);
      osc1.frequency.exponentialRampToValueAtTime(864, now + 0.35);

      osc2.frequency.setValueAtTime(level === 'L1' ? 648 : 576, now);
      osc2.frequency.exponentialRampToValueAtTime(1296, now + 0.4);

      filter.type = 'bandpass';
      filter.frequency.setValueAtTime(level === 'L1' ? 1200 : 900, now);
      filter.Q.setValueAtTime(4, now);

      gainNode.gain.setValueAtTime(0.001, now);
      gainNode.gain.linearRampToValueAtTime(0.18, now + 0.04);
      gainNode.gain.exponentialRampToValueAtTime(0.0001, now + 0.6);

      osc1.connect(filter);
      osc2.connect(filter);
      filter.connect(gainNode);
      gainNode.connect(ctx.destination);

      osc1.start(now);
      osc2.start(now);
      osc1.stop(now + 0.65);
      osc2.stop(now + 0.65);

    } else if (level === 'L3') {
      // Resonant Dampener Pulse (Amber Warning)
      const osc = ctx.createOscillator();
      const filter = ctx.createBiquadFilter();
      const gain = ctx.createGain();

      osc.type = 'sawtooth';
      osc.frequency.setValueAtTime(220, now);
      osc.frequency.exponentialRampToValueAtTime(110, now + 0.4);

      filter.type = 'lowpass';
      filter.frequency.setValueAtTime(600, now);
      filter.Q.setValueAtTime(8, now);

      gain.gain.setValueAtTime(0.001, now);
      gain.gain.linearRampToValueAtTime(0.22, now + 0.05);
      gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.7);

      osc.connect(filter);
      filter.connect(gain);
      gain.connect(ctx.destination);

      osc.start(now);
      osc.stop(now + 0.75);

    } else if (level === 'L4') {
      // Emergency Posture: Deep Planetary Sub-Bass Pulse (55Hz / 82Hz)
      const sub = ctx.createOscillator();
      const drone = ctx.createOscillator();
      const gain = ctx.createGain();

      sub.type = 'sawtooth';
      sub.frequency.setValueAtTime(55, now);
      sub.frequency.linearRampToValueAtTime(45, now + 0.8);

      drone.type = 'sine';
      drone.frequency.setValueAtTime(110, now);

      gain.gain.setValueAtTime(0.001, now);
      gain.gain.linearRampToValueAtTime(0.28, now + 0.08);
      gain.gain.exponentialRampToValueAtTime(0.0001, now + 1.2);

      sub.connect(gain);
      drone.connect(gain);
      gain.connect(ctx.destination);

      sub.start(now);
      drone.start(now);
      sub.stop(now + 1.25);
      drone.stop(now + 1.25);

    } else if (level === 'L5') {
      // Continuity: Dual-Chamber Biometric Heartbeat
      // Lub... dub...
      const lubOsc = ctx.createOscillator();
      const lubGain = ctx.createGain();
      lubOsc.type = 'sine';
      lubOsc.frequency.setValueAtTime(70, now);
      lubOsc.frequency.exponentialRampToValueAtTime(35, now + 0.2);
      lubGain.gain.setValueAtTime(0.001, now);
      lubGain.gain.linearRampToValueAtTime(0.3, now + 0.03);
      lubGain.gain.exponentialRampToValueAtTime(0.0001, now + 0.25);
      lubOsc.connect(lubGain);
      lubGain.connect(ctx.destination);
      lubOsc.start(now);
      lubOsc.stop(now + 0.25);

      const dubOsc = ctx.createOscillator();
      const dubGain = ctx.createGain();
      dubOsc.type = 'sine';
      dubOsc.frequency.setValueAtTime(85, now + 0.28);
      dubOsc.frequency.exponentialRampToValueAtTime(40, now + 0.5);
      dubGain.gain.setValueAtTime(0.001, now + 0.28);
      dubGain.gain.linearRampToValueAtTime(0.25, now + 0.31);
      dubGain.gain.exponentialRampToValueAtTime(0.0001, now + 0.55);
      dubOsc.connect(dubGain);
      dubGain.connect(ctx.destination);
      dubOsc.start(now + 0.28);
      dubOsc.stop(now + 0.55);

    } else {
      // L6 Terminal Descent
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = 'sawtooth';
      osc.frequency.setValueAtTime(140, now);
      osc.frequency.exponentialRampToValueAtTime(25, now + 1.5);
      gain.gain.setValueAtTime(0.001, now);
      gain.gain.linearRampToValueAtTime(0.35, now + 0.05);
      gain.gain.exponentialRampToValueAtTime(0.0001, now + 1.6);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start(now);
      osc.stop(now + 1.65);
    }
  }

  /**
   * Speaks the exact Echo-Back Contract within 2 seconds
   * Format: "CODE · scope=X · expires Y · receipt CMD-..."
   */
  public speakEchoBack(code: string, scope: string, ttlLabel: string, receiptId: string): void {
    if (!this.voiceEnabled) return;
    if (typeof window === 'undefined' || !('speechSynthesis' in window)) return;

    window.speechSynthesis.cancel(); // cancel any pending

    const cleanReceipt = receiptId.replace(/^CMD-/, '').slice(-6);
    const spokenText = `${code}. Scope: ${scope}. Expires in ${ttlLabel}. Receipt: ${cleanReceipt}.`;

    const utterance = new SpeechSynthesisUtterance(spokenText);
    utterance.rate = 1.05; // telegraphic, confident
    utterance.pitch = 0.92; // authoritative resonant alien tone
    utterance.volume = 0.85;

    // Pick a smooth voice if available
    const voices = window.speechSynthesis.getVoices();
    const preferredVoice = voices.find(
      v => v.name.includes('Google UK English Male') || v.name.includes('Daniel') || v.name.includes('Natural') || v.lang.startsWith('en')
    );
    if (preferredVoice) {
      utterance.voice = preferredVoice;
    }

    window.speechSynthesis.speak(utterance);
  }

  public speakRefusal(code: string, reason: string): void {
    if (!this.voiceEnabled) return;
    if (typeof window === 'undefined' || !('speechSynthesis' in window)) return;

    window.speechSynthesis.cancel();
    const text = `Refused. Command ${code}. ${reason.replace(/_/g, ' ').toLowerCase()}.`;
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 1.05;
    utterance.pitch = 0.88;
    utterance.volume = 0.85;
    window.speechSynthesis.speak(utterance);
  }
}

export const alienAudio = new AlienAcousticSynth();
