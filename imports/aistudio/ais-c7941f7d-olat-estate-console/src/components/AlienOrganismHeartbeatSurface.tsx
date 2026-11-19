import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Volume2,
  VolumeX,
  Play,
  RotateCcw,
  Shield,
  Activity,
  Radio,
  Eye,
  Sliders,
  Sparkles,
  Zap,
  Clock,
  Compass,
  AlertTriangle,
  CheckCircle2,
  Lock,
  Layers,
  MapPin,
  Smartphone,
  Watch,
  Satellite,
} from 'lucide-react';
import {
  OrganismOrgan,
  VesselPath,
  OrganismHarmonicState,
  INITIAL_ORGANISM_ORGANS,
  INITIAL_VESSEL_PATHS,
  evaluateOrganismHarmonics,
  simulateOrganismCounterfactual,
  INITIAL_FOUNDER_PRESENCE_STATE,
  FounderPresenceState,
  executeFounderDisappearanceDrill,
  FinalBossDrillResult,
} from '../lib/protocolEngine';

type FractalZoom = 'WHOLE_ORGANISM' | 'ORGAN_ANATOMY' | 'CELL_MODULE' | 'CILIA_SCRIPT';

export const AlienOrganismHeartbeatSurface: React.FC = () => {
  // State
  const [organs, setOrgans] = useState<OrganismOrgan[]>(INITIAL_ORGANISM_ORGANS);
  const [vessels] = useState<VesselPath[]>(INITIAL_VESSEL_PATHS);
  const [selectedOrganId, setSelectedOrganId] = useState<string>('ORACLE_CORE');
  const [zoomLevel, setZoomLevel] = useState<FractalZoom>('WHOLE_ORGANISM');
  const [activePreset, setActivePreset] = useState<
    'NORMAL_RESTING_HARMONY' | 'CI_FLAKE_IRREGULAR_TAP' | 'SPLIT_BRAIN_ZOMBIE_TREMOR' | 'ASYMMETRIC_COMPOUNDING_CURE'
  >('NORMAL_RESTING_HARMONY');

  // Sonification (Web Audio API)
  const [audioEnabled, setAudioEnabled] = useState<boolean>(false);
  const [audioVolume, setAudioVolume] = useState<number>(0.25);
  const audioCtxRef = useRef<AudioContext | null>(null);
  const oscBaseRef = useRef<OscillatorNode | null>(null);
  const oscHarmonicRef = useRef<OscillatorNode | null>(null);
  const oscSubRef = useRef<OscillatorNode | null>(null);
  const gainNodeRef = useRef<GainNode | null>(null);

  // Time Scrubbing ("Blood Memory")
  const [timeScrubSecondsAgo, setTimeScrubSecondsAgo] = useState<number>(0);
  const [isPlayingHistorical, setIsPlayingHistorical] = useState<boolean>(false);

  // Founder Presence Protocol & Final Boss Drill
  const [founderPresence, setFounderPresence] = useState<FounderPresenceState>(INITIAL_FOUNDER_PRESENCE_STATE);
  const [drillResult, setDrillResult] = useState<FinalBossDrillResult | null>(null);
  const [isDrillRunning, setIsDrillRunning] = useState<boolean>(false);

  // Harmonics
  const harmonics: OrganismHarmonicState = evaluateOrganismHarmonics(organs);
  const selectedOrgan = organs.find((o) => o.id === selectedOrganId) || organs[0];

  // Canvas Ref
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const animFrameRef = useRef<number | null>(null);
  const pulseParticlesRef = useRef<
    Array<{
      vesselId: string;
      progress: number;
      speed: number;
      size: number;
      hue: string;
    }>
  >([]);

  // Initialize Particles
  useEffect(() => {
    const particles: Array<{
      vesselId: string;
      progress: number;
      speed: number;
      size: number;
      hue: string;
    }> = [];
    vessels.forEach((vessel) => {
      for (let i = 0; i < 4; i++) {
        particles.push({
          vesselId: vessel.id,
          progress: Math.random(),
          speed: 0.004 * vessel.pulseVelocity,
          size: Math.random() * 2 + 2,
          hue: '#10b981',
        });
      }
    });
    pulseParticlesRef.current = particles;
  }, [vessels]);

  // Audio Engine Lifecycle
  const initAudio = useCallback(() => {
    if (audioCtxRef.current) return;
    try {
      const AudioCtx = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
      const ctx = new AudioCtx();
      audioCtxRef.current = ctx;

      const masterGain = ctx.createGain();
      masterGain.gain.setValueAtTime(audioVolume, ctx.currentTime);
      masterGain.connect(ctx.destination);
      gainNodeRef.current = masterGain;

      // Base Carrier 432 Hz
      const oscBase = ctx.createOscillator();
      oscBase.type = 'sine';
      oscBase.frequency.setValueAtTime(432, ctx.currentTime);

      // Fifth (648 Hz)
      const oscHarmonic = ctx.createOscillator();
      oscHarmonic.type = 'triangle';
      oscHarmonic.frequency.setValueAtTime(648, ctx.currentTime);

      // Sub Bass (108 Hz)
      const oscSub = ctx.createOscillator();
      oscSub.type = 'sine';
      oscSub.frequency.setValueAtTime(108, ctx.currentTime);

      const subGain = ctx.createGain();
      subGain.gain.setValueAtTime(0.4, ctx.currentTime);

      oscBase.connect(masterGain);
      oscHarmonic.connect(masterGain);
      oscSub.connect(subGain);
      subGain.connect(masterGain);

      oscBase.start();
      oscHarmonic.start();
      oscSub.start();

      oscBaseRef.current = oscBase;
      oscHarmonicRef.current = oscHarmonic;
      oscSubRef.current = oscSub;
    } catch {
      // Web Audio unavailable
    }
  }, [audioVolume]);

  const toggleAudio = () => {
    if (!audioEnabled) {
      initAudio();
      if (audioCtxRef.current?.state === 'suspended') {
        audioCtxRef.current.resume();
      }
      setAudioEnabled(true);
    } else {
      if (audioCtxRef.current && gainNodeRef.current) {
        gainNodeRef.current.gain.setValueAtTime(0, audioCtxRef.current.currentTime);
      }
      setAudioEnabled(false);
    }
  };

  useEffect(() => {
    if (gainNodeRef.current && audioCtxRef.current && audioEnabled) {
      gainNodeRef.current.gain.setTargetAtTime(audioVolume, audioCtxRef.current.currentTime, 0.05);
    }
  }, [audioVolume, audioEnabled]);

  // Adjust audio chords when harmonics change
  useEffect(() => {
    if (!audioCtxRef.current || !oscBaseRef.current || !oscHarmonicRef.current || !audioEnabled) return;
    const ctx = audioCtxRef.current;
    if (harmonics.harmonicChord === 'DIMINISHED_TRITONE_DISSONANCE') {
      // Dissonant tritone (432 Hz & 610 Hz)
      oscBaseRef.current.frequency.setTargetAtTime(432, ctx.currentTime, 0.1);
      oscHarmonicRef.current.frequency.setTargetAtTime(610.9, ctx.currentTime, 0.1);
    } else if (harmonics.harmonicChord === 'SUSPENDED_FOURTH_TENSION') {
      // Suspended 4th (432 Hz & 576 Hz)
      oscBaseRef.current.frequency.setTargetAtTime(432, ctx.currentTime, 0.1);
      oscHarmonicRef.current.frequency.setTargetAtTime(576, ctx.currentTime, 0.1);
    } else {
      // Natural 432 Hz Perfect Fifth (432 Hz & 648 Hz)
      oscBaseRef.current.frequency.setTargetAtTime(432, ctx.currentTime, 0.1);
      oscHarmonicRef.current.frequency.setTargetAtTime(648, ctx.currentTime, 0.1);
    }
  }, [harmonics.harmonicChord, audioEnabled]);

  // Handle Preset Simulation
  const handleApplyPreset = (preset: typeof activePreset) => {
    setActivePreset(preset);
    const sim = simulateOrganismCounterfactual(preset);
    setOrgans(sim.updatedOrgans);
  };

  // Run Final Boss Disappearance Drill
  const handleRunFinalBossDrill = () => {
    setIsDrillRunning(true);
    setFounderPresence((prev) => ({
      ...prev,
      heartbeatStatus: 'GRACE_PERIOD_COUNTDOWN',
      lastHeartbeatSecondsAgo: 940,
    }));

    setTimeout(() => {
      const result = executeFounderDisappearanceDrill('LOST_PHONE_DEAD_LAPTOP', founderPresence);
      setDrillResult(result);
      setFounderPresence((prev) => ({
        ...prev,
        heartbeatStatus: 'AUTONOMOUS_CONTINUITY_MODE',
        estateContinuityStatus: {
          ...prev.estateContinuityStatus,
          isAutonomous: true,
          raftQuorumMaintained: true,
          zeroFounderInterruption: true,
        },
      }));
      setIsDrillRunning(false);
    }, 600);
  };

  // 60 FPS Living Organism Canvas Animation
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let startTime = performance.now();

    // Map organ node coordinates in an organic ellipsoid
    const organPositions: Record<string, { x: number; y: number }> = {
      ORACLE_CORE: { x: 0.5, y: 0.28 },
      OTTO_SYNAPSE: { x: 0.32, y: 0.45 },
      AURA_CONCIERGE: { x: 0.68, y: 0.45 },
      NATS_VASCULAR: { x: 0.24, y: 0.68 },
      BATTATION_METABOLISM: { x: 0.44, y: 0.8 },
      CAMEL_IMMUNE: { x: 0.76, y: 0.68 },
      COMPOUND_ENGINE: { x: 0.62, y: 0.8 },
      GITOPS_LITESTREAM: { x: 0.5, y: 0.55 },
    };

    const render = (time: number) => {
      const elapsed = (time - startTime) * 0.001;
      const width = canvas.width;
      const height = canvas.height;

      ctx.clearRect(0, 0, width, height);

      // 1. Cosmic / Biological Background Mesh
      const gradient = ctx.createRadialGradient(
        width * 0.5,
        height * 0.52,
        40,
        width * 0.5,
        height * 0.52,
        width * 0.55
      );
      gradient.addColorStop(0, '#090d16');
      gradient.addColorStop(0.7, '#04070d');
      gradient.addColorStop(1, '#020408');
      ctx.fillStyle = gradient;
      ctx.fillRect(0, 0, width, height);

      // Subtle breathing diaphragm motion
      const breathingPulse = Math.sin(elapsed * harmonics.breathingCycleHz * Math.PI * 2) * 0.04 + 1.0;

      // 2. Render Vascular Splines (Vessels)
      vessels.forEach((vessel) => {
        const srcPos = organPositions[vessel.sourceOrganId];
        const tgtPos = organPositions[vessel.targetOrganId];
        if (!srcPos || !tgtPos) return;

        const x1 = srcPos.x * width;
        const y1 = srcPos.y * height * breathingPulse;
        const x2 = tgtPos.x * width;
        const y2 = tgtPos.y * height * breathingPulse;

        // Control point for curved organic vascular flow
        const cx = (x1 + x2) * 0.5 + Math.sin(elapsed * 1.5 + (x1 % 10)) * 12;
        const cy = (y1 + y2) * 0.5 - 20;

        const isHighlighted =
          selectedOrganId === vessel.sourceOrganId || selectedOrganId === vessel.targetOrganId;

        ctx.beginPath();
        ctx.moveTo(x1, y1);
        ctx.quadraticCurveTo(cx, cy, x2, y2);
        ctx.lineWidth = vessel.thickness * (isHighlighted ? 1.8 : 1.2);
        ctx.strokeStyle = vessel.isBruised
          ? 'rgba(239, 68, 68, 0.45)'
          : isHighlighted
          ? 'rgba(16, 185, 129, 0.65)'
          : 'rgba(59, 130, 246, 0.22)';
        ctx.stroke();

        // Outer bioluminescent halo
        if (isHighlighted) {
          ctx.beginPath();
          ctx.moveTo(x1, y1);
          ctx.quadraticCurveTo(cx, cy, x2, y2);
          ctx.lineWidth = vessel.thickness * 3.5;
          ctx.strokeStyle = 'rgba(16, 185, 129, 0.12)';
          ctx.stroke();
        }
      });

      // 3. Render Hemoglobin / Bio-Photon Pulses Traveling Through Vessels
      pulseParticlesRef.current.forEach((p) => {
        const vessel = vessels.find((v) => v.id === p.vesselId);
        if (!vessel) return;
        const srcPos = organPositions[vessel.sourceOrganId];
        const tgtPos = organPositions[vessel.targetOrganId];
        if (!srcPos || !tgtPos) return;

        p.progress += p.speed;
        if (p.progress > 1) p.progress = 0;

        const x1 = srcPos.x * width;
        const y1 = srcPos.y * height * breathingPulse;
        const x2 = tgtPos.x * width;
        const y2 = tgtPos.y * height * breathingPulse;
        const cx = (x1 + x2) * 0.5 + Math.sin(elapsed * 1.5 + (x1 % 10)) * 12;
        const cy = (y1 + y2) * 0.5 - 20;

        // Quadratic bezier interpolation
        const t = p.progress;
        const px = (1 - t) * (1 - t) * x1 + 2 * (1 - t) * t * cx + t * t * x2;
        const py = (1 - t) * (1 - t) * y1 + 2 * (1 - t) * t * cy + t * t * y2;

        ctx.beginPath();
        ctx.arc(px, py, p.size, 0, Math.PI * 2);
        ctx.fillStyle = vessel.isBruised ? '#ef4444' : '#34d399';
        ctx.shadowColor = vessel.isBruised ? '#ef4444' : '#10b981';
        ctx.shadowBlur = 8;
        ctx.fill();
        ctx.shadowBlur = 0;
      });

      // 4. Render Living Organ Nodes (Cellular Membrane + Nucleus + Cilia)
      organs.forEach((organ) => {
        const pos = organPositions[organ.id];
        if (!pos) return;

        const cx = pos.x * width;
        const cy = pos.y * height * breathingPulse;

        // Systolic cardiac pulse for this organ
        const organBpmHz = organ.bpm / 60;
        const organHeartbeat = Math.sin(elapsed * organBpmHz * Math.PI * 2);
        const arrhythmiaJitter = organ.arrhythmiaIndex > 0.1 ? (Math.random() - 0.5) * organ.arrhythmiaIndex * 8 : 0;

        const baseRadius = 26 + (organ.cellCount / 12);
        const currentRadius = baseRadius + organHeartbeat * 4 + arrhythmiaJitter;
        const isSelected = organ.id === selectedOrganId;

        // Cilia / Microvilli Filaments radiating from cell membrane
        const ciliaCount = 24;
        ctx.save();
        ctx.translate(cx, cy);
        for (let i = 0; i < ciliaCount; i++) {
          const angle = (i / ciliaCount) * Math.PI * 2;
          const ciliaWiggle = Math.sin(elapsed * 8 + i * 2) * 4;
          const len = currentRadius + 8 + ciliaWiggle;
          const xCilia = Math.cos(angle) * len;
          const yCilia = Math.sin(angle) * len;

          ctx.beginPath();
          ctx.moveTo(Math.cos(angle) * currentRadius, Math.sin(angle) * currentRadius);
          ctx.lineTo(xCilia, yCilia);
          ctx.lineWidth = 1;
          ctx.strokeStyle = organ.membraneHue + '33';
          ctx.stroke();
        }
        ctx.restore();

        // Outer Bio-Luminescent Membrane
        ctx.beginPath();
        ctx.arc(cx, cy, currentRadius + 6, 0, Math.PI * 2);
        ctx.fillStyle = organ.membraneHue + (isSelected ? '33' : '18');
        ctx.fill();

        // Organ Nucleus
        ctx.beginPath();
        ctx.arc(cx, cy, currentRadius, 0, Math.PI * 2);
        const organGradient = ctx.createRadialGradient(cx, cy, 2, cx, cy, currentRadius);
        organGradient.addColorStop(0, organ.membraneHue);
        organGradient.addColorStop(0.85, organ.membraneHue + 'aa');
        organGradient.addColorStop(1, '#090d16');
        ctx.fillStyle = organGradient;
        ctx.shadowColor = organ.membraneHue;
        ctx.shadowBlur = isSelected ? 22 : 10;
        ctx.fill();
        ctx.shadowBlur = 0;

        // Node Label
        ctx.font = '10px ui-monospace, SFMono-Regular, monospace';
        ctx.fillStyle = '#ffffff';
        ctx.textAlign = 'center';
        ctx.fillText(organ.label, cx, cy + currentRadius + 18);

        ctx.font = '9px ui-sans-serif, system-ui';
        ctx.fillStyle = 'rgba(255, 255, 255, 0.6)';
        ctx.fillText(`${organ.bpm} BPM · ${organ.vascularFlowRate} p/s`, cx, cy + currentRadius + 30);
      });

      animFrameRef.current = requestAnimationFrame(render);
    };

    animFrameRef.current = requestAnimationFrame(render);

    return () => {
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
    };
  }, [organs, vessels, selectedOrganId, harmonics]);

  return (
    <div className="space-y-6 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 font-sans">
      {/* 2100 Alien Vision Masthead */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-5 rounded-2xl bg-slate-900 border border-slate-800 text-slate-100 shadow-xl">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1.5 text-xs font-mono font-semibold tracking-wider uppercase text-emerald-400">
              <Activity className="w-3.5 h-3.5 animate-pulse" />
              Living Organism Twin · Alien 2100
            </span>
            <span className="text-slate-500">·</span>
            <span className="text-xs text-slate-400">Real-Time Biological Topology & Event Flow</span>
          </div>
          <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-white font-display">
            The Estate Heartbeat & Founder Presence
          </h1>
          <p className="text-xs sm:text-sm text-slate-400 max-w-2xl">
            A continuous living stream replacing dead dashboards with breathing biological topology, Web Audio harmonic chords,
            fractal zoom, and the 7-stage Founder Disappearance Survival Protocol.
          </p>
        </div>

        {/* Global Acoustic & Ambient Controls */}
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={toggleAudio}
            className={`flex items-center gap-2 px-3.5 py-2 text-xs font-medium rounded-xl border transition-all cursor-pointer ${
              audioEnabled
                ? 'bg-emerald-500/20 border-emerald-500/40 text-emerald-300 shadow-lg shadow-emerald-500/10'
                : 'bg-slate-800/80 border-slate-700 text-slate-400 hover:text-slate-200'
            }`}
          >
            {audioEnabled ? <Volume2 className="w-4 h-4 text-emerald-400" /> : <VolumeX className="w-4 h-4" />}
            <span>{audioEnabled ? 'Sonification Active (432Hz)' : 'Enable Living Audio'}</span>
          </button>

          {audioEnabled && (
            <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 bg-slate-800/80 rounded-xl border border-slate-700">
              <Sliders className="w-3.5 h-3.5 text-slate-400" />
              <input
                type="range"
                min="0"
                max="0.8"
                step="0.05"
                value={audioVolume}
                onChange={(e) => setAudioVolume(parseFloat(e.target.value))}
                className="w-16 accent-emerald-500 cursor-pointer"
                title="Acoustic Volume"
              />
            </div>
          )}
        </div>
      </div>

      {/* Main Living Canvas & Control Surface Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: 60FPS Living Organism Canvas (8 Cols) */}
        <div className="lg:col-span-8 flex flex-col space-y-3">
          <div className="relative rounded-2xl overflow-hidden border border-slate-800 bg-slate-950 shadow-2xl">
            {/* Ambient HUD Bar */}
            <div className="absolute top-3 left-4 right-4 z-10 flex flex-wrap items-center justify-between gap-2 text-xs font-mono">
              <div className="flex items-center gap-3 px-3 py-1.5 bg-slate-900/90 backdrop-blur-md rounded-xl border border-slate-800/80 text-slate-300">
                <span className="flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
                  {harmonics.globalBpm} BPM
                </span>
                <span className="text-slate-600">|</span>
                <span>{harmonics.breathingCycleHz} Hz Diaphragm</span>
                <span className="text-slate-600">|</span>
                <span className={harmonics.isSonificationHarmonic ? 'text-emerald-400' : 'text-amber-400'}>
                  {harmonics.harmonicChord}
                </span>
              </div>

              {/* Fractal Zoom Selector */}
              <div className="flex items-center gap-1 p-1 bg-slate-900/90 backdrop-blur-md rounded-xl border border-slate-800/80">
                <button
                  type="button"
                  onClick={() => setZoomLevel('WHOLE_ORGANISM')}
                  className={`px-2.5 py-1 text-xs rounded-lg transition-colors cursor-pointer ${
                    zoomLevel === 'WHOLE_ORGANISM'
                      ? 'bg-emerald-500/20 text-emerald-300 font-semibold'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  Macro
                </button>
                <button
                  type="button"
                  onClick={() => setZoomLevel('ORGAN_ANATOMY')}
                  className={`px-2.5 py-1 text-xs rounded-lg transition-colors cursor-pointer ${
                    zoomLevel === 'ORGAN_ANATOMY'
                      ? 'bg-emerald-500/20 text-emerald-300 font-semibold'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  Organ
                </button>
                <button
                  type="button"
                  onClick={() => setZoomLevel('CELL_MODULE')}
                  className={`px-2.5 py-1 text-xs rounded-lg transition-colors cursor-pointer ${
                    zoomLevel === 'CELL_MODULE'
                      ? 'bg-emerald-500/20 text-emerald-300 font-semibold'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  Cell
                </button>
                <button
                  type="button"
                  onClick={() => setZoomLevel('CILIA_SCRIPT')}
                  className={`px-2.5 py-1 text-xs rounded-lg transition-colors cursor-pointer ${
                    zoomLevel === 'CILIA_SCRIPT'
                      ? 'bg-emerald-500/20 text-emerald-300 font-semibold'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  Cilia
                </button>
              </div>
            </div>

            {/* Interactive Canvas */}
            <canvas
              ref={canvasRef}
              width={900}
              height={560}
              className="w-full h-[460px] sm:h-[540px] block cursor-crosshair"
              onClick={(e) => {
                const rect = e.currentTarget.getBoundingClientRect();
                const clickX = (e.clientX - rect.left) / rect.width;
                const clickY = (e.clientY - rect.top) / rect.height;

                // Hit test closest organ
                const organPositions: Record<string, { x: number; y: number }> = {
                  ORACLE_CORE: { x: 0.5, y: 0.28 },
                  OTTO_SYNAPSE: { x: 0.32, y: 0.45 },
                  AURA_CONCIERGE: { x: 0.68, y: 0.45 },
                  NATS_VASCULAR: { x: 0.24, y: 0.68 },
                  BATTATION_METABOLISM: { x: 0.44, y: 0.8 },
                  CAMEL_IMMUNE: { x: 0.76, y: 0.68 },
                  COMPOUND_ENGINE: { x: 0.62, y: 0.8 },
                  GITOPS_LITESTREAM: { x: 0.5, y: 0.55 },
                };

                let closestId = 'ORACLE_CORE';
                let minDistance = Infinity;
                Object.entries(organPositions).forEach(([id, pos]) => {
                  const dist = Math.hypot(clickX - pos.x, clickY - pos.y);
                  if (dist < minDistance) {
                    minDistance = dist;
                    closestId = id;
                  }
                });
                if (minDistance < 0.16) {
                  setSelectedOrganId(closestId);
                }
              }}
            />

            {/* Bottom Scrubber & Causality Bar */}
            <div className="p-3 bg-slate-900/95 border-t border-slate-800 flex flex-wrap items-center justify-between gap-3 text-xs">
              <div className="flex items-center gap-3 text-slate-300">
                <span className="font-semibold text-emerald-400 flex items-center gap-1.5">
                  <Eye className="w-3.5 h-3.5" />
                  Causal Lens:
                </span>
                <span className="font-mono text-slate-200">{selectedOrgan.label}</span>
                <span className="text-slate-500">·</span>
                <span className="text-slate-400 text-[11px] hidden sm:inline">
                  {selectedOrgan.causalUpstream.length} Upstream / {selectedOrgan.causalDownstream.length} Downstream links
                </span>
              </div>

              {/* "Blood Memory" Time Scrubber */}
              <div className="flex items-center gap-3">
                <span className="text-slate-400 font-mono text-[11px] flex items-center gap-1">
                  <Clock className="w-3 h-3 text-slate-400" />
                  Blood Memory:
                </span>
                <input
                  type="range"
                  min="0"
                  max="300"
                  step="10"
                  value={timeScrubSecondsAgo}
                  onChange={(e) => setTimeScrubSecondsAgo(parseInt(e.target.value, 10))}
                  className="w-24 sm:w-36 accent-emerald-500 cursor-pointer"
                  title="Scrub Historical Pulse Memory"
                />
                <span className="font-mono text-emerald-400 text-[11px] w-12 text-right">
                  {timeScrubSecondsAgo === 0 ? 'LIVE' : `-${timeScrubSecondsAgo}s`}
                </span>
              </div>
            </div>
          </div>

          {/* Counterfactual Simulation Presets (Ties to Compounding Doctrine) */}
          <div className="p-4 bg-slate-900/60 rounded-xl border border-slate-800 space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-400 font-mono flex items-center gap-1.5">
                <Zap className="w-3.5 h-3.5 text-amber-400" />
                Pre-Visualized Counterfactuals · Impact On Living Heartbeat
              </h2>
              <span className="text-xs text-slate-500 font-mono">Core Law #7 Verification</span>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              <button
                type="button"
                onClick={() => handleApplyPreset('NORMAL_RESTING_HARMONY')}
                className={`p-2.5 rounded-lg border text-left text-xs transition-colors cursor-pointer ${
                  activePreset === 'NORMAL_RESTING_HARMONY'
                    ? 'bg-emerald-500/15 border-emerald-500/40 text-emerald-300 font-medium'
                    : 'bg-slate-800/40 border-slate-800 text-slate-300 hover:bg-slate-800'
                }`}
              >
                <div className="font-semibold text-white">Nominal 432Hz</div>
                <div className="text-[11px] text-slate-400 mt-0.5">Calm laminar rhythm</div>
              </button>

              <button
                type="button"
                onClick={() => handleApplyPreset('CI_FLAKE_IRREGULAR_TAP')}
                className={`p-2.5 rounded-lg border text-left text-xs transition-colors cursor-pointer ${
                  activePreset === 'CI_FLAKE_IRREGULAR_TAP'
                    ? 'bg-amber-500/15 border-amber-500/40 text-amber-300 font-medium'
                    : 'bg-slate-800/40 border-slate-800 text-slate-300 hover:bg-slate-800'
                }`}
              >
                <div className="font-semibold text-amber-400">CI Pipeline Flake</div>
                <div className="text-[11px] text-slate-400 mt-0.5">Pre-symptom micro-tremor</div>
              </button>

              <button
                type="button"
                onClick={() => handleApplyPreset('SPLIT_BRAIN_ZOMBIE_TREMOR')}
                className={`p-2.5 rounded-lg border text-left text-xs transition-colors cursor-pointer ${
                  activePreset === 'SPLIT_BRAIN_ZOMBIE_TREMOR'
                    ? 'bg-rose-500/15 border-rose-500/40 text-rose-300 font-medium'
                    : 'bg-slate-800/40 border-slate-800 text-slate-300 hover:bg-slate-800'
                }`}
              >
                <div className="font-semibold text-rose-400">Split-Brain Outage</div>
                <div className="text-[11px] text-slate-400 mt-0.5">Arrhythmia & vessel bruise</div>
              </button>

              <button
                type="button"
                onClick={() => handleApplyPreset('ASYMMETRIC_COMPOUNDING_CURE')}
                className={`p-2.5 rounded-lg border text-left text-xs transition-colors cursor-pointer ${
                  activePreset === 'ASYMMETRIC_COMPOUNDING_CURE'
                    ? 'bg-teal-500/15 border-teal-500/40 text-teal-300 font-medium'
                    : 'bg-slate-800/40 border-slate-800 text-slate-300 hover:bg-slate-800'
                }`}
              >
                <div className="font-semibold text-teal-300">Asymmetric Cure</div>
                <div className="text-[11px] text-slate-400 mt-0.5">A(s) ≥ 10.0 structural gate</div>
              </button>
            </div>
          </div>
        </div>

        {/* Right Column: Selected Organ Anatomical Telemetry + Founder Presence (4 Cols) */}
        <div className="lg:col-span-4 space-y-6">
          {/* Organ Detail Card */}
          <div className="p-5 rounded-2xl bg-slate-900 border border-slate-800 text-slate-100 shadow-xl space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span
                  className="w-3 h-3 rounded-full animate-ping"
                  style={{ backgroundColor: selectedOrgan.membraneHue }}
                />
                <h3 className="font-bold text-white text-base font-display">{selectedOrgan.label}</h3>
              </div>
              <span className="text-[11px] font-mono px-2 py-0.5 rounded-md bg-slate-800 text-slate-300">
                {selectedOrgan.category}
              </span>
            </div>

            <p className="text-xs text-slate-300 leading-relaxed">{selectedOrgan.description}</p>

            <div className="grid grid-cols-2 gap-3 text-xs font-mono">
              <div className="p-2.5 bg-slate-950/60 rounded-xl border border-slate-800/80">
                <span className="text-slate-400 block text-[10px] uppercase">Cardiac Rhythm</span>
                <span className="text-sm font-semibold text-emerald-400">{selectedOrgan.bpm} BPM</span>
              </div>
              <div className="p-2.5 bg-slate-950/60 rounded-xl border border-slate-800/80">
                <span className="text-slate-400 block text-[10px] uppercase">Vascular Flow</span>
                <span className="text-sm font-semibold text-cyan-400">{selectedOrgan.vascularFlowRate} p/s</span>
              </div>
              <div className="p-2.5 bg-slate-950/60 rounded-xl border border-slate-800/80">
                <span className="text-slate-400 block text-[10px] uppercase">Cellular Mass</span>
                <span className="text-sm font-semibold text-slate-200">{selectedOrgan.cellCount} Cells</span>
              </div>
              <div className="p-2.5 bg-slate-950/60 rounded-xl border border-slate-800/80">
                <span className="text-slate-400 block text-[10px] uppercase">Cilia Microvilli</span>
                <span className="text-sm font-semibold text-slate-200">{selectedOrgan.ciliaCount} Filaments</span>
              </div>
            </div>

            {/* Causal Graph Wiring */}
            <div className="space-y-2 text-xs pt-1 border-t border-slate-800">
              <div className="text-[11px] font-mono text-slate-400 uppercase tracking-wider">Causal Pathway</div>
              <div className="space-y-1">
                <div className="text-slate-400 text-[11px]">
                  <span className="text-slate-500">Upstream Roots:</span>{' '}
                  <span className="text-slate-300 font-mono">{selectedOrgan.causalUpstream.join(', ') || 'Root Origin'}</span>
                </div>
                <div className="text-slate-400 text-[11px]">
                  <span className="text-slate-500">Downstream Organs:</span>{' '}
                  <span className="text-slate-300 font-mono">{selectedOrgan.causalDownstream.join(', ') || 'Terminal'}</span>
                </div>
              </div>
            </div>
          </div>

          {/* Founder Presence Protocol & Final Boss Disappearance Drill */}
          <div className="p-5 rounded-2xl bg-slate-900 border border-slate-800 text-slate-100 shadow-xl space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Shield className="w-4 h-4 text-emerald-400" />
                <h3 className="font-bold text-white text-base font-display">Founder Presence Protocol</h3>
              </div>
              <span className="text-[11px] font-mono text-emerald-400 font-semibold flex items-center gap-1">
                <Radio className="w-3 h-3 animate-pulse" />
                {founderPresence.heartbeatStatus}
              </span>
            </div>

            <p className="text-xs text-slate-400 leading-relaxed">
              Two-way mutual heartbeat between Founder and Estate. If phone is lost and laptop dies, the estate locates you via
              independent lines while sustaining 100% autonomous operation.
            </p>

            {/* Registered Fallback Lines */}
            <div className="space-y-2 text-xs font-mono">
              <div className="text-[11px] text-slate-400 uppercase tracking-wider">Independent Channels (No Phone Needed)</div>
              <div className="space-y-1.5">
                {founderPresence.registeredChannels.map((channel) => (
                  <div
                    key={channel.channelId}
                    className="flex items-center justify-between p-2 rounded-lg bg-slate-950/60 border border-slate-800/80 text-[11px]"
                  >
                    <div className="flex items-center gap-2">
                      {channel.channelType === 'WEARABLE_ESIM' && <Watch className="w-3.5 h-3.5 text-cyan-400" />}
                      {channel.channelType === 'SATELLITE_SOS' && <Satellite className="w-3.5 h-3.5 text-amber-400" />}
                      {channel.channelType === 'SECONDARY_ESIM' && <Smartphone className="w-3.5 h-3.5 text-blue-400" />}
                      {channel.channelType === 'TRUSTED_RELAY' && <Lock className="w-3.5 h-3.5 text-purple-400" />}
                      <span className="text-slate-200">{channel.identifier}</span>
                    </div>
                    <span className="text-emerald-400 text-[10px]">{channel.status}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Final Boss Drill Trigger */}
            <div className="pt-2 border-t border-slate-800">
              <button
                type="button"
                onClick={handleRunFinalBossDrill}
                disabled={isDrillRunning}
                className="w-full flex items-center justify-center gap-2 px-4 py-2.5 text-xs font-semibold text-slate-900 bg-emerald-400 hover:bg-emerald-300 rounded-xl transition-colors cursor-pointer shadow-lg shadow-emerald-500/10 disabled:opacity-50"
              >
                <Compass className="w-4 h-4" />
                <span>
                  {isDrillRunning ? 'Simulating 7-Stage Failover...' : 'Execute Final Boss Drill (Phone Lost + Laptop Dead)'}
                </span>
              </button>
            </div>

            {/* Drill Output */}
            {drillResult && (
              <div className="p-3 bg-slate-950 rounded-xl border border-emerald-500/30 text-xs font-mono space-y-2">
                <div className="flex items-center justify-between text-emerald-400 font-semibold text-[11px]">
                  <span className="flex items-center gap-1.5">
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    7/7 Stages Passed (Drill {drillResult.drillId})
                  </span>
                  <span>100% Autonomous Uptime</span>
                </div>
                <div className="space-y-1 text-[11px] text-slate-300">
                  {drillResult.stageResults.slice(0, 4).map((s) => (
                    <div key={s.stage} className="flex items-start gap-1.5">
                      <span className="text-emerald-400 font-bold">[{s.stage}]</span>
                      <span className="text-slate-400">{s.detail}</span>
                    </div>
                  ))}
                </div>
                <div className="text-[10px] text-slate-500 pt-1 border-t border-slate-900 truncate">
                  SHA256: {drillResult.compoundingRemediationProof}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
