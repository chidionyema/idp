import React, { useState } from 'react';
import { 
  Volume2, 
  Mic, 
  Sparkles, 
  Play, 
  Pause, 
  Settings2, 
  Sliders, 
  Layers, 
  Bot, 
  Heart, 
  Glasses, 
  Watch, 
  Check, 
  ShieldCheck,
  Zap,
  Activity
} from 'lucide-react';
import { VoiceConfig, AvatarStyle } from '../types/otto';

const PRESET_VOICES: VoiceConfig[] = [
  {
    id: 'voice-cos-01',
    name: 'Executive Chief of Staff',
    category: 'founder-executive',
    description: 'Terse, composed British executive cadence. Outcome first, zero wasted syllables.',
    pitch: 1.0,
    rate: 1.15,
    sttEngine: 'Groq Distil-Whisper (85ms)',
    sampleAudioText: 'Airlock PR-1084 merged and verified across 5 peers. All systems green. Zero founder intervention required.'
  },
  {
    id: 'voice-pastoral-02',
    name: 'Serene Pastoral (Sister Beatrice Guardian)',
    category: 'pastoral-serene',
    description: 'Gentle, comforting, unhurried cadence with reverent warmth. Perfect for scripture & daily care.',
    pitch: 0.95,
    rate: 0.88,
    sttEngine: 'Deepgram Nova-2 (140ms)',
    sampleAudioText: 'Peace be with you, Sister Beatrice. Your afternoon garden chimes are ready, and your favorite chamomile tea is brewing warm.'
  },
  {
    id: 'voice-tactical-03',
    name: 'Minimalist Tactical Core',
    category: 'tactical-minimalist',
    description: 'Low-latency military-precision voice for high-velocity hardware driving & robotics teleop.',
    pitch: 1.05,
    rate: 1.25,
    sttEngine: 'Whisper Large v3 Turbo (210ms)',
    sampleAudioText: 'Hardware driver locked on Display 0. CGEvent dispatched. Diff delta 0.00%. Next step ready.'
  },
  {
    id: 'voice-companion-04',
    name: 'Warm Family Concierge',
    category: 'warm-companion',
    description: 'Friendly, patient, deeply empathetic assistant for non-technical family members.',
    pitch: 1.1,
    rate: 0.95,
    sttEngine: 'Google Cloud Chirp 2 (165ms)',
    sampleAudioText: 'Hello! I took care of your iPad screen brightness and filtered out two robocalls today so you won\'t be bothered.'
  }
];

export const VoiceAndAvatarStudio: React.FC = () => {
  const [selectedVoice, setSelectedVoice] = useState<VoiceConfig>(PRESET_VOICES[0]);
  const [selectedAvatar, setSelectedAvatar] = useState<AvatarStyle>('executive-monolith');
  const [pitch, setPitch] = useState<number>(selectedVoice.pitch);
  const [rate, setRate] = useState<number>(selectedVoice.rate);
  const [sttEngine, setSttEngine] = useState<string>(selectedVoice.sttEngine);
  const [isPlayingAudio, setIsPlayingAudio] = useState(false);

  const STT_ENGINES = [
    'Groq Distil-Whisper (85ms LPU)',
    'Deepgram Nova-2 (140ms)',
    'Google Cloud Chirp 2 (165ms)',
    'Whisper Large v3 Turbo (210ms)',
    'ElevenLabs Scribe (240ms)',
    'AssemblyAI Conformer (220ms)',
    'RevAI Express (290ms)',
    'Azure Cognitive Speech (180ms)'
  ];

  const handleSelectVoice = (v: VoiceConfig) => {
    setSelectedVoice(v);
    setPitch(v.pitch);
    setRate(v.rate);
    setSttEngine(v.sttEngine);
  };

  const handleTestVoice = (customText?: string) => {
    if (isPlayingAudio) {
      if (typeof window !== 'undefined' && window.speechSynthesis) {
        window.speechSynthesis.cancel();
      }
      setIsPlayingAudio(false);
      return;
    }

    const textToSpeak = customText || selectedVoice.sampleAudioText;

    if (typeof window !== 'undefined' && window.speechSynthesis) {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(textToSpeak);
      utterance.pitch = pitch;
      utterance.rate = rate;
      utterance.onend = () => setIsPlayingAudio(false);
      utterance.onerror = () => setIsPlayingAudio(false);
      setIsPlayingAudio(true);
      window.speechSynthesis.speak(utterance);
    }
  };

  return (
    <div className="space-y-6">
      {/* Banner */}
      <div className="rounded-2xl border border-indigo-500/30 bg-gradient-to-b from-slate-900 to-slate-950 p-6 shadow-2xl relative overflow-hidden">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4 relative z-10">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-300 text-xs font-mono mb-2">
              <Sparkles className="w-3.5 h-3.5" />
              <span>MULTIMODAL EXPRESSION: VOICE CONFIGURATION &amp; VISUAL AVATARS</span>
            </div>
            <h2 className="text-2xl font-bold text-white font-display">
              Voice Architecture &amp; Adaptive Visual Presence
            </h2>
            <p className="text-sm text-slate-400 max-w-2xl mt-1">
              Otto can speak in <span className="text-cyan-400 font-semibold">11 distinct voices</span> across 8 speech-to-text engines, from an ultra-terse Chief of Staff for the founder to a serene pastoral guardian for Elder Sister Beatrice. Select or customize avatars for spatial, mobile, and desktop surfaces.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-xs font-mono px-3 py-1.5 rounded-lg bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 flex items-center gap-1.5 font-bold">
              <Activity className="w-3.5 h-3.5" />
              <span>LIVE AUDIO SYNTHESIS READY</span>
            </span>
          </div>
        </div>
      </div>

      {/* Main Grid: Avatar Engine vs Voice Studio */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Visual Avatar Engine */}
        <div className="lg:col-span-5 space-y-4">
          <div className="rounded-xl border border-slate-800 bg-slate-950 p-5 shadow-xl space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <span className="font-display font-bold text-sm text-white flex items-center gap-1.5">
                <Bot className="w-4 h-4 text-cyan-400" />
                Visual Avatar Presence
              </span>
              <span className="text-[10px] font-mono text-slate-400 uppercase">
                {selectedAvatar.replace('-', ' ')}
              </span>
            </div>

            {/* Live Interactive Avatar Viewport with Audio Reactivity */}
            <div className="h-64 rounded-xl bg-slate-900 border border-slate-800 flex flex-col items-center justify-center p-6 relative overflow-hidden">
              {/* Audio Reactive Glow */}
              <div className={`absolute w-44 h-44 rounded-full blur-3xl transition-all duration-300 pointer-events-none ${
                isPlayingAudio ? 'opacity-90 scale-125' : 'opacity-30 scale-100'
              } ${
                selectedAvatar === 'executive-monolith' ? 'bg-cyan-500/30' :
                selectedAvatar === 'compassionate-orb' ? 'bg-rose-500/30' :
                selectedAvatar === 'neural-hud' ? 'bg-indigo-500/30' : 'bg-amber-500/30'
              }`} />

              {/* 1. EXECUTIVE MONOLITH AVATAR */}
              {selectedAvatar === 'executive-monolith' && (
                <div className="relative flex flex-col items-center">
                  <div className={`w-24 h-24 rounded-2xl bg-gradient-to-tr from-slate-950 via-slate-900 to-slate-800 border-2 border-cyan-400/80 shadow-2xl flex items-center justify-center transition-all ${
                    isPlayingAudio ? 'scale-110 shadow-cyan-500/40 ring-4 ring-cyan-500/20' : ''
                  }`}>
                    <div className={`w-10 h-10 rounded-lg bg-cyan-400 flex items-center justify-center transition-all ${
                      isPlayingAudio ? 'scale-125 bg-cyan-300' : ''
                    }`}>
                      <Zap className="w-6 h-6 text-slate-950 fill-current" />
                    </div>
                  </div>
                  <span className="text-[11px] font-mono font-bold text-cyan-300 mt-4 tracking-wider">
                    SOVEREIGN MONOLITH · FOUNDER CORE
                  </span>
                </div>
              )}

              {/* 2. COMPASSIONATE ORB AVATAR (Elder Nun) */}
              {selectedAvatar === 'compassionate-orb' && (
                <div className="relative flex flex-col items-center">
                  <div className={`w-28 h-28 rounded-full bg-gradient-to-tr from-stone-900 via-rose-950/60 to-rose-900/40 border-2 border-rose-300/80 shadow-2xl flex items-center justify-center transition-all ${
                    isPlayingAudio ? 'scale-110 shadow-rose-500/40 ring-4 ring-rose-500/20' : 'animate-pulse'
                  }`}>
                    <Heart className="w-10 h-10 text-rose-300 fill-current" />
                  </div>
                  <span className="text-[11px] font-serif font-bold text-rose-200 mt-4 tracking-wider">
                    COMPASSIONATE GUARDIAN · SISTER BEATRICE
                  </span>
                </div>
              )}

              {/* 3. NEURAL HUD AVATAR (AR Glasses) */}
              {selectedAvatar === 'neural-hud' && (
                <div className="relative flex flex-col items-center font-mono">
                  <div className={`w-28 h-28 border-2 border-dashed border-indigo-400 rounded-full flex items-center justify-center relative transition-all ${
                    isPlayingAudio ? 'rotate-45 scale-110 border-indigo-300' : 'animate-spin'
                  }`} style={{ animationDuration: '12s' }}>
                    <div className="w-12 h-12 border border-indigo-500 rounded flex items-center justify-center">
                      <Glasses className="w-6 h-6 text-indigo-300" />
                    </div>
                  </div>
                  <span className="text-[10px] font-mono text-indigo-300 mt-4 uppercase">
                    ORION NEURAL HUD · RETINAL RAYCAST
                  </span>
                </div>
              )}

              {/* 4. HAPTIC GLYPH AVATAR (Watch) */}
              {selectedAvatar === 'haptic-glyph' && (
                <div className="relative flex flex-col items-center font-mono">
                  <div className={`w-24 h-24 rounded-[32px] bg-slate-950 border-2 border-amber-400 p-2 shadow-2xl flex items-center justify-center ${
                    isPlayingAudio ? 'scale-110 shadow-amber-500/30' : ''
                  }`}>
                    <Watch className="w-8 h-8 text-amber-400" />
                  </div>
                  <span className="text-[10px] font-mono text-amber-300 mt-4 uppercase">
                    APPLE WATCH ULTRA · HAPTIC GLYPH
                  </span>
                </div>
              )}

              {/* Audio Waveform Indicator */}
              {isPlayingAudio && (
                <div className="absolute bottom-2 flex items-center gap-1">
                  {[4, 12, 24, 16, 28, 14, 8, 20, 10].map((h, i) => (
                    <div
                      key={i}
                      className="w-1 bg-cyan-400 rounded-full animate-bounce"
                      style={{ height: `${h}px`, animationDelay: `${i * 0.1}s` }}
                    />
                  ))}
                </div>
              )}
            </div>

            {/* Avatar Selector Buttons */}
            <div className="grid grid-cols-2 gap-2">
              {[
                { id: 'executive-monolith', label: 'Executive Monolith', icon: Bot },
                { id: 'compassionate-orb', label: 'Compassionate Orb', icon: Heart },
                { id: 'neural-hud', label: 'Neural HUD (Glasses)', icon: Glasses },
                { id: 'haptic-glyph', label: 'Haptic Glyph (Watch)', icon: Watch }
              ].map(av => {
                const Icon = av.icon;
                const isSelected = selectedAvatar === av.id;
                return (
                  <button
                    key={av.id}
                    onClick={() => setSelectedAvatar(av.id as any)}
                    className={`p-2.5 rounded-lg border text-left text-xs font-mono flex items-center gap-2 transition-all ${
                      isSelected
                        ? 'border-cyan-400 bg-cyan-950/40 text-white font-bold'
                        : 'border-slate-800 bg-slate-900/60 text-slate-400 hover:text-white'
                    }`}
                  >
                    <Icon className="w-3.5 h-3.5 shrink-0" />
                    <span className="truncate">{av.label}</span>
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        {/* Right Column: Voice Configuration Studio */}
        <div className="lg:col-span-7 space-y-4">
          <div className="rounded-xl border border-slate-800 bg-slate-950 p-5 shadow-xl space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <span className="font-display font-bold text-sm text-white flex items-center gap-1.5">
                <Volume2 className="w-4 h-4 text-cyan-400" />
                Voice Presets &amp; Acoustic Parameters
              </span>
              <button
                onClick={() => handleTestVoice()}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-mono font-bold transition-all ${
                  isPlayingAudio
                    ? 'bg-rose-600 text-white animate-pulse'
                    : 'bg-cyan-500 hover:bg-cyan-400 text-slate-950'
                }`}
              >
                {isPlayingAudio ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5 fill-current" />}
                <span>{isPlayingAudio ? 'Halt Audio' : 'Preview Voice'}</span>
              </button>
            </div>

            {/* 4 Voice Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {PRESET_VOICES.map(v => {
                const isSelected = selectedVoice.id === v.id;
                return (
                  <div
                    key={v.id}
                    onClick={() => handleSelectVoice(v)}
                    className={`p-3.5 rounded-xl border transition-all cursor-pointer text-xs ${
                      isSelected
                        ? 'border-indigo-400 bg-indigo-950/30 text-white shadow-md'
                        : 'border-slate-800 bg-slate-900/40 text-slate-300 hover:bg-slate-900 hover:border-slate-700'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-bold text-white text-xs">{v.name}</span>
                      {isSelected && <Check className="w-3.5 h-3.5 text-cyan-400" />}
                    </div>
                    <p className="text-[11px] text-slate-400 leading-snug">{v.description}</p>
                    <div className="mt-2 text-[10px] font-mono text-cyan-300">
                      STT: {v.sttEngine}
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Sliders for Pitch and Rate */}
            <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 space-y-3 font-mono text-xs">
              <div className="space-y-1">
                <div className="flex justify-between text-slate-400 text-[11px]">
                  <span>Speaking Rate (Cadence): {rate.toFixed(2)}x</span>
                  <span className="text-slate-500">0.7x (Pastoral) ➔ 1.4x (Tactical)</span>
                </div>
                <input
                  type="range"
                  min="0.7"
                  max="1.4"
                  step="0.05"
                  value={rate}
                  onChange={e => setRate(parseFloat(e.target.value))}
                  className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-cyan-400"
                />
              </div>

              <div className="space-y-1">
                <div className="flex justify-between text-slate-400 text-[11px]">
                  <span>Vocal Pitch: {pitch.toFixed(2)}</span>
                  <span className="text-slate-500">0.8 (Deep Sovereign) ➔ 1.2 (Bright Kin)</span>
                </div>
                <input
                  type="range"
                  min="0.8"
                  max="1.2"
                  step="0.05"
                  value={pitch}
                  onChange={e => setPitch(parseFloat(e.target.value))}
                  className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-cyan-400"
                />
              </div>

              {/* STT Engine Dropdown */}
              <div className="pt-2 border-t border-slate-800/80">
                <label className="text-[11px] text-slate-400 block mb-1">
                  Active Speech-to-Text (STT) Provider:
                </label>
                <select
                  value={sttEngine}
                  onChange={e => setSttEngine(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-xs text-white focus:outline-none focus:border-cyan-500"
                >
                  {STT_ENGINES.map((engine, idx) => (
                    <option key={idx} value={engine}>{engine}</option>
                  ))}
                </select>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
