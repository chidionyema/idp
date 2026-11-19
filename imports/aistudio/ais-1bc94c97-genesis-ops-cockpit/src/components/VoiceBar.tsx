import React, { useEffect, useState } from 'react';
import {
  Play,
  Pause,
  RotateCcw,
  FastForward,
  Rewind,
  Volume2,
  VolumeX,
  ShieldCheck,
  Cpu,
  Sparkles,
  Maximize2,
  Sliders,
} from 'lucide-react';
import { SpokenBrief } from '../types';
import { audioEngine, AudioPlaybackState } from '../utils/audioEngine';

interface VoiceBarProps {
  currentBrief: SpokenBrief | null;
  onOpenReceiptModal: (brief: SpokenBrief) => void;
  onOpenTriageDrawer?: (brief: SpokenBrief) => void;
  geminiEnrichmentActive: boolean;
}

export const VoiceBar: React.FC<VoiceBarProps> = ({
  currentBrief,
  onOpenReceiptModal,
  onOpenTriageDrawer,
  geminiEnrichmentActive,
}) => {
  const [audioState, setAudioState] = useState<AudioPlaybackState>(audioEngine.getState());
  const [isMuted, setIsMuted] = useState(false);
  const [showVoiceSettings, setShowVoiceSettings] = useState(false);
  const [selectedVoice, setSelectedVoice] = useState('en_US-ryan-medium');

  useEffect(() => {
    const unsubscribe = audioEngine.subscribe((state) => {
      setAudioState(state);
    });
    return () => unsubscribe();
  }, []);

  if (!currentBrief) {
    return (
      <div className="fixed bottom-0 left-0 right-0 z-30 border-t border-zinc-800 bg-zinc-950/95 backdrop-blur-lg px-4 py-3 flex items-center justify-between text-xs text-zinc-500 font-mono">
        <div className="flex items-center gap-2">
          <span className="inline-block h-2 w-2 rounded-full bg-zinc-600" />
          <span>VOICE BAR READY • SELECT ANY LEGION TO HEAR ITS 60–90S BRIEF</span>
        </div>
        <div className="flex items-center gap-3 text-zinc-400">
          <span>PIPER ARM64 LANE: READY</span>
          <span>SPEECHSYNTHESIS: ZERO-INFRA FALLBACK</span>
        </div>
      </div>
    );
  }

  const togglePlay = () => {
    if (audioState.isPlaying && !audioState.isPaused) {
      audioEngine.pause();
    } else if (audioState.isPlaying && audioState.isPaused) {
      audioEngine.resume();
    } else {
      audioEngine.playBrief(
        currentBrief.spokenScript,
        currentBrief.recordedDurationSec,
        currentBrief.karaokeLines
      );
    }
  };

  const handleSeek = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = parseFloat(e.target.value);
    audioEngine.seek(val);
  };

  const toggleMute = () => {
    if (isMuted) {
      audioEngine.setVolume(1.0);
      setIsMuted(false);
    } else {
      audioEngine.setVolume(0.0);
      setIsMuted(true);
    }
  };

  const cycleRate = () => {
    const rates = [1.0, 1.25, 1.5, 2.0];
    const currentIdx = rates.indexOf(audioState.playbackRate);
    const nextRate = rates[(currentIdx + 1) % rates.length];
    audioEngine.setPlaybackRate(nextRate);
  };

  const formatTime = (sec: number) => {
    const m = Math.floor(sec / 60);
    const s = Math.floor(sec % 60);
    return `${m}:${s < 10 ? '0' : ''}${s}`;
  };

  const activeKaraokeText =
    currentBrief.karaokeLines[audioState.activeLineIndex]?.text || currentBrief.spokenScript.slice(0, 90) + '...';

  return (
    <div className="fixed bottom-0 left-0 right-0 z-40 border-t border-zinc-800/90 bg-zinc-950/95 backdrop-blur-xl shadow-2xl px-4 py-2.5 transition-all">
      {/* Karaoke / Live Transcript Banner */}
      <div className="max-w-7xl mx-auto flex items-center justify-between text-xs pb-2 border-b border-zinc-900 gap-4">
        <div className="flex items-center gap-2 overflow-hidden">
          <div className="flex items-center gap-1.5 px-2 py-0.5 rounded bg-sky-950/60 border border-sky-800/60 text-sky-300 font-mono text-[11px] shrink-0">
            <span className="inline-block h-2 w-2 rounded-full bg-sky-400 animate-pulse" />
            <span>{currentBrief.legionName}</span>
          </div>

          {/* Currently Spoken Line with Karaoke Glow */}
          <div className="text-zinc-300 font-medium truncate flex items-center gap-2">
            <span className="text-zinc-500 font-mono text-[11px] shrink-0">SPKT:</span>
            <span className="text-sky-200 transition-colors duration-200">
              "{activeKaraokeText}"
            </span>
          </div>
        </div>

        {/* SHA-256 Verifiable Receipt Chip */}
        <button
          onClick={() => onOpenReceiptModal(currentBrief)}
          className="shrink-0 flex items-center gap-1.5 px-2 py-0.5 rounded bg-zinc-900 border border-zinc-700 hover:border-zinc-500 text-zinc-300 font-mono text-[11px] transition-colors"
          title="Click to verify cryptographic SHA-256 receipt & raw transcript diff"
        >
          <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
          <span>sha256:{currentBrief.sha256Receipt.slice(0, 10)}...</span>
        </button>
      </div>

      {/* Main Player Controls Bar */}
      <div className="max-w-7xl mx-auto pt-2 flex flex-wrap items-center justify-between gap-3">
        {/* Left: Brief Metadata & Piper Voice */}
        <div className="flex items-center gap-3 min-w-[220px]">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-zinc-100 hover:text-sky-300 cursor-pointer" onClick={() => onOpenTriageDrawer?.(currentBrief)}>
                {currentBrief.title}
              </span>
              {geminiEnrichmentActive && (
                <span className="flex items-center gap-0.5 text-[9px] px-1 py-0.2 rounded bg-purple-950 border border-purple-800/80 text-purple-300 font-mono">
                  <Sparkles className="w-2.5 h-2.5" />
                  Gemini Enriched
                </span>
              )}
            </div>
            <div className="flex items-center gap-2 text-[11px] text-zinc-400 font-mono">
              <span className="flex items-center gap-1">
                <Cpu className="w-3 h-3 text-cyan-400" />
                Piper {selectedVoice.split('-')[1]}
              </span>
              <span>•</span>
              <span>{currentBrief.rawLogLineCount} raw logs → {currentBrief.recordedDurationSec}s brief</span>
            </div>
          </div>
        </div>

        {/* Center: Audio Transport Controls & Waveform Scrub */}
        <div className="flex-1 max-w-2xl flex flex-col items-center gap-1 px-2">
          <div className="flex items-center gap-3">
            <button
              onClick={() => audioEngine.seek(audioState.currentTime - 15)}
              className="p-1.5 rounded-full hover:bg-zinc-800 text-zinc-400 hover:text-zinc-200 transition-colors"
              title="Rewind 15 seconds"
            >
              <Rewind className="w-4 h-4" />
            </button>

            <button
              onClick={togglePlay}
              className="h-10 w-10 rounded-full bg-gradient-to-tr from-sky-600 to-indigo-500 hover:from-sky-500 hover:to-indigo-400 text-white flex items-center justify-center shadow-lg shadow-sky-500/25 transition-transform active:scale-95"
              title={audioState.isPlaying && !audioState.isPaused ? 'Pause' : 'Play Brief'}
            >
              {audioState.isPlaying && !audioState.isPaused ? (
                <Pause className="w-5 h-5 fill-current" />
              ) : (
                <Play className="w-5 h-5 fill-current ml-0.5" />
              )}
            </button>

            <button
              onClick={() => audioEngine.seek(audioState.currentTime + 15)}
              className="p-1.5 rounded-full hover:bg-zinc-800 text-zinc-400 hover:text-zinc-200 transition-colors"
              title="Fast Forward 15 seconds"
            >
              <FastForward className="w-4 h-4" />
            </button>

            <button
              onClick={() => {
                audioEngine.seek(0);
                audioEngine.playBrief(currentBrief.spokenScript, currentBrief.recordedDurationSec, currentBrief.karaokeLines);
              }}
              className="p-1.5 rounded-full hover:bg-zinc-800 text-zinc-400 hover:text-zinc-200 transition-colors"
              title="Replay from start"
            >
              <RotateCcw className="w-3.5 h-3.5" />
            </button>
          </div>

          {/* Scrub Track with Live Dynamic Waveform visualizer */}
          <div className="w-full flex items-center gap-2">
            <span className="text-[11px] font-mono text-zinc-400 w-9 text-right">
              {formatTime(audioState.currentTime)}
            </span>

            <div className="relative flex-1 flex items-center group">
              {/* Background simulated mini waveform bars */}
              <div className="absolute inset-0 flex items-center justify-between pointer-events-none opacity-30 gap-0.5 px-1">
                {Array.from({ length: 40 }).map((_, i) => {
                  const isPast = (i / 40) <= (audioState.currentTime / (audioState.duration || 1));
                  const isSpeaking = audioState.isPlaying && !audioState.isPaused;
                  // Dynamic wave height
                  const baseH = (Math.sin(i * 0.4) * 6 + 10);
                  const h = isSpeaking ? (baseH + (i % 3) * 4) : 6;
                  return (
                    <div
                      key={i}
                      className={`w-1 rounded-full transition-all duration-150 ${
                        isPast ? 'bg-sky-400 opacity-90' : 'bg-zinc-700'
                      }`}
                      style={{ height: `${h}px` }}
                    />
                  );
                })}
              </div>

              <input
                type="range"
                min="0"
                max={audioState.duration || 60}
                step="0.5"
                value={audioState.currentTime}
                onChange={handleSeek}
                className="w-full h-2 bg-transparent appearance-none cursor-pointer z-10 accent-sky-400"
              />
            </div>

            <span className="text-[11px] font-mono text-zinc-500 w-9">
              {formatTime(audioState.duration || currentBrief.recordedDurationSec)}
            </span>
          </div>
        </div>

        {/* Right: Playback Speed, Mute, and Triage Drawer link */}
        <div className="flex items-center gap-2 min-w-[200px] justify-end">
          {/* Rate Button */}
          <button
            onClick={cycleRate}
            className="px-2 py-1 rounded bg-zinc-900 border border-zinc-700 hover:border-zinc-500 font-mono text-xs text-zinc-200 transition-colors"
            title="Cycle Playback Rate"
          >
            {audioState.playbackRate}x
          </button>

          {/* Mute Button */}
          <button
            onClick={toggleMute}
            className="p-1.5 rounded bg-zinc-900 border border-zinc-700 hover:border-zinc-500 text-zinc-300 transition-colors"
            title={isMuted ? 'Unmute' : 'Mute'}
          >
            {isMuted ? <VolumeX className="w-4 h-4 text-rose-400" /> : <Volume2 className="w-4 h-4" />}
          </button>

          {/* Open Triage Drawer Button */}
          {onOpenTriageDrawer && (
            <button
              onClick={() => onOpenTriageDrawer(currentBrief)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-sky-950/70 border border-sky-700/60 hover:bg-sky-900 text-sky-200 text-xs font-medium transition-colors"
            >
              <Maximize2 className="w-3.5 h-3.5" />
              <span>Founder Triage</span>
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
