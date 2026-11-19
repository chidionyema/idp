/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect } from 'react';
import {
  AlienOrganismHeartbeat,
  INITIAL_HEARTBEAT,
} from '../lib/protocolEngine.ts';
import {
  Activity,
  Heart,
  ShieldCheck,
  Zap,
  Fingerprint,
  RotateCw,
  TrendingUp,
  FileCode,
  Copy,
  Check,
} from 'lucide-react';

export const AlienOrganismHeartbeatSurface: React.FC = () => {
  const [heartbeat, setHeartbeat] = useState<AlienOrganismHeartbeat>(INITIAL_HEARTBEAT);
  const [isBeating, setIsBeating] = useState<boolean>(false);
  const [copiedEnvelope, setCopiedEnvelope] = useState<boolean>(false);

  // Heartbeat lease countdown
  useEffect(() => {
    const timer = setInterval(() => {
      setHeartbeat((prev) => {
        const nextSeconds = prev.presenceValidSecondsRemaining <= 1 ? 900 : prev.presenceValidSecondsRemaining - 1;
        return {
          ...prev,
          presenceValidSecondsRemaining: nextSeconds,
        };
      });
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  const handlePulse = () => {
    setIsBeating(true);
    setTimeout(() => setIsBeating(false), 500);
    setHeartbeat((prev) => ({
      ...prev,
      lastFounderAttestation: new Date().toISOString(),
      presenceValidSecondsRemaining: 900,
      cellularEnergyScore: Math.min(100, prev.cellularEnergyScore + 0.5),
      compoundingLeverageExponent: Number((prev.compoundingLeverageExponent + 0.02).toFixed(2)),
    }));
  };

  const rawEnvelopeJson = {
    envelopeVersion: "2.0.0",
    envelopeId: "DROP-2026-1079-2100",
    sender: "founder-sovereign-key-0x8f2d",
    recipient: "genesis-autonomous-kernel",
    protocol: "ALIEN_ORGANISM_HEARTBEAT_AND_FOUNDER_PRESENCE",
    timestamp: heartbeat.lastFounderAttestation,
    payload: {
      biometricPresence: {
        active: true,
        heartbeatBpm: heartbeat.pulseFrequencyBpm,
        remainingLeaseSeconds: heartbeat.presenceValidSecondsRemaining,
      },
      compoundingMetrics: {
        metabolicPhase: heartbeat.metabolicPhase,
        energyScore: heartbeat.cellularEnergyScore,
        entropyDecayRate: heartbeat.entropyDecayFactor,
        leverageExponent: heartbeat.compoundingLeverageExponent,
      },
      dnaHash: heartbeat.dnaHash,
    },
    hmacSha256Signature: "9b8a7c6d5e4f3a2b1c0d9e8f7a6b5c4d3e2f1a0b9c8d7e6f5a4b3c2d1e0f9a8b"
  };

  const handleCopyEnvelope = () => {
    navigator.clipboard.writeText(JSON.stringify(rawEnvelopeJson, null, 2));
    setCopiedEnvelope(true);
    setTimeout(() => setCopiedEnvelope(false), 2000);
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-6 sm:p-8">
        <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-6">
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-xs font-mono text-cyan-400">
              <Activity className="w-4 h-4 text-cyan-400" />
              <span>DROP-2026-1079-2100 · SOVEREIGN PROTOCOL ENVELOPE</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-white">
              Alien Organism Heartbeat & Founder Presence
            </h1>
            <p className="text-slate-400 text-sm max-w-2xl">
              Genesis operates as an autonomous self-catalyzing organism. The cellular metabolic pulse maintains compounding leverage while the Founder Presence Protocol verifies biometrics and prevents entropy collapse.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={handlePulse}
              className="flex items-center gap-2 px-5 py-3 text-xs font-mono font-bold text-slate-950 bg-gradient-to-r from-rose-400 via-pink-400 to-cyan-400 hover:from-rose-300 hover:to-cyan-300 rounded-xl transition-all shadow-lg shadow-rose-950/40 cursor-pointer active:scale-95"
            >
              <Heart className={`w-4 h-4 text-slate-950 ${isBeating ? 'scale-125' : ''} transition-transform`} />
              <span>ATTEST FOUNDER PRESENCE (PULSE)</span>
            </button>
          </div>
        </div>
      </div>

      {/* Grid: Biological Organism & Leverage Curve */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        
        {/* Left Column: Biometric Organism Visualizer (6 cols) */}
        <div className="lg:col-span-6 bg-slate-900/60 border border-slate-800 rounded-xl p-6 sm:p-8 space-y-6">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div className="flex items-center gap-2">
              <Fingerprint className="w-5 h-5 text-rose-400" />
              <h2 className="text-base font-semibold text-white">Biological Heartbeat Metaphor</h2>
            </div>
            <span className="text-xs font-mono text-emerald-400 flex items-center gap-1 font-semibold">
              <ShieldCheck className="w-3.5 h-3.5" />
              ATTESTATION VALID
            </span>
          </div>

          {/* Central Pulsing Heartbeat Visualizer */}
          <div className="py-8 flex flex-col items-center justify-center relative">
            <div
              className={`w-40 h-40 rounded-full flex items-center justify-center transition-all duration-300 ${
                isBeating
                  ? 'bg-rose-500/30 scale-110 ring-8 ring-rose-500/20'
                  : 'bg-slate-950 ring-2 ring-slate-800'
              }`}
            >
              <div className="w-28 h-28 rounded-full bg-gradient-to-br from-rose-500/20 to-cyan-500/20 border border-rose-500/40 flex flex-col items-center justify-center text-center p-2">
                <Heart className={`w-7 h-7 text-rose-400 mb-1 ${isBeating ? 'scale-125 text-rose-300' : ''}`} />
                <div className="text-lg font-bold font-mono text-white tabular-nums">
                  {heartbeat.pulseFrequencyBpm} <span className="text-[10px] text-slate-400 font-normal">BPM</span>
                </div>
                <div className="text-[9px] font-mono text-cyan-400 uppercase tracking-wider">
                  {heartbeat.metabolicPhase}
                </div>
              </div>
            </div>

            <div className="mt-6 text-center space-y-1 font-mono">
              <div className="text-xs text-slate-400">Founder Presence Lease Countdown:</div>
              <div className="text-xl font-bold text-cyan-300 tabular-nums">
                {Math.floor(heartbeat.presenceValidSecondsRemaining / 60)}m{' '}
                {heartbeat.presenceValidSecondsRemaining % 60}s remaining
              </div>
              <div className="text-[11px] text-slate-500">
                Auto-refreshes on Founder Cockpit steering interaction or manual pulse.
              </div>
            </div>
          </div>

          {/* Vitals Strip */}
          <div className="grid grid-cols-3 gap-3 pt-4 border-t border-slate-800 text-xs font-mono">
            <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
              <span className="text-slate-500 block text-[10px]">Cellular Energy:</span>
              <span className="text-emerald-400 font-bold text-sm tabular-nums">
                {heartbeat.cellularEnergyScore}%
              </span>
            </div>
            <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
              <span className="text-slate-500 block text-[10px]">Entropy Decay:</span>
              <span className="text-slate-200 font-bold text-sm tabular-nums">
                {heartbeat.entropyDecayFactor}
              </span>
            </div>
            <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
              <span className="text-slate-500 block text-[10px]">Leverage Exponent:</span>
              <span className="text-cyan-400 font-bold text-sm tabular-nums">
                {heartbeat.compoundingLeverageExponent}x
              </span>
            </div>
          </div>
        </div>

        {/* Right Column: Compounding Growth Curve & Envelope Inspector (6 cols) */}
        <div className="lg:col-span-6 bg-slate-900/60 border border-slate-800 rounded-xl p-6 sm:p-8 space-y-6">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div className="flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-cyan-400" />
              <h2 className="text-base font-semibold text-white">Compounding vs Entropy Math</h2>
            </div>
            <span className="text-xs font-mono text-cyan-400">L(t) = L₀ · e^(λt)</span>
          </div>

          {/* Visual Curve Representation */}
          <div className="p-4 bg-slate-950 rounded-xl border border-slate-800 space-y-4">
            <div className="flex justify-between text-xs font-mono">
              <span className="text-emerald-400 font-bold">● Compounding Engineering Yield</span>
              <span className="text-slate-500">○ Entropy Tax (Point Fixes)</span>
            </div>

            {/* Simulated ASCII/SVG Chart */}
            <div className="h-32 flex items-end gap-1.5 pt-4 px-2 border-b border-slate-800">
              {[12, 16, 21, 28, 38, 49, 64, 82, 105, 134, 172, 220].map((val, idx) => (
                <div key={idx} className="flex-1 flex flex-col items-center gap-1">
                  <div
                    style={{ height: `${Math.min(100, (val / 220) * 100)}%` }}
                    className="w-full bg-gradient-to-t from-cyan-600 to-teal-400 rounded-t"
                  />
                  <span className="text-[9px] font-mono text-slate-500">{idx + 1}</span>
                </div>
              ))}
            </div>

            <p className="text-xs text-slate-400 leading-relaxed font-mono">
              While conventional engineering codebases decay under point fixes, Genesis compounds exponentially: each invariant test and reusable module permanently removes an entire class of potential failures.
            </p>
          </div>

          {/* Incoming Envelope Json Box */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono font-bold text-slate-300 flex items-center gap-1.5">
                <FileCode className="w-4 h-4 text-cyan-400" />
                <span>INCOMING ENVELOPE: DROP-2026-1079-2100</span>
              </span>

              <button
                onClick={handleCopyEnvelope}
                className="text-cyan-400 hover:text-cyan-300 text-xs font-mono flex items-center gap-1 cursor-pointer"
              >
                {copiedEnvelope ? (
                  <>
                    <Check className="w-3.5 h-3.5 text-emerald-400" />
                    <span className="text-emerald-400">Copied</span>
                  </>
                ) : (
                  <>
                    <Copy className="w-3.5 h-3.5" />
                    <span>Copy JSON</span>
                  </>
                )}
              </button>
            </div>

            <pre className="p-3 bg-slate-950 rounded-lg border border-slate-800 text-[10px] font-mono text-cyan-300 max-h-48 overflow-y-auto leading-relaxed">
              {JSON.stringify(rawEnvelopeJson, null, 2)}
            </pre>
          </div>
        </div>

      </div>
    </div>
  );
};
