import React, { useState } from 'react';
import { 
  ShieldAlert, 
  CheckCircle2, 
  Smartphone, 
  Watch, 
  Glasses, 
  Key, 
  CreditCard, 
  Trash2, 
  FileCheck, 
  Zap, 
  RotateCcw,
  Sparkles,
  Lock,
  ArrowRight,
  Fingerprint
} from 'lucide-react';

interface TrustCaptchaHandoverProps {
  onChallengeResolved?: () => void;
}

export const TrustCaptchaHandover: React.FC<TrustCaptchaHandoverProps> = ({ onChallengeResolved }) => {
  const [activeTab, setActiveTab] = useState<'turnstile' | 'slider' | 'passkey' | 'payment' | 'governance'>('turnstile');
  const [isTurnstileChecking, setIsTurnstileChecking] = useState(false);
  const [isTurnstileSolved, setIsTurnstileSolved] = useState(false);

  const [sliderPosition, setSliderPosition] = useState(0);
  const [isSliderSolved, setIsSliderSolved] = useState(false);

  const [isPasskeyApproved, setIsPasskeyApproved] = useState(false);
  const [isPaymentConfirmed, setIsPaymentConfirmed] = useState(false);
  const [isGovernanceSigned, setIsGovernanceSigned] = useState(false);

  const [resumedLatencyMs, setResumedLatencyMs] = useState<number | null>(null);

  const handleTurnstileClick = () => {
    setIsTurnstileChecking(true);
    setTimeout(() => {
      setIsTurnstileChecking(false);
      setIsTurnstileSolved(true);
      triggerOttoResume(340);
    }, 700);
  };

  const handleSliderChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = Number(e.target.value);
    setSliderPosition(val);
    if (val >= 88 && val <= 94) {
      setIsSliderSolved(true);
      triggerOttoResume(280);
    }
  };

  const handlePasskeyClick = () => {
    setIsPasskeyApproved(true);
    triggerOttoResume(410);
  };

  const handlePaymentClick = () => {
    setIsPaymentConfirmed(true);
    triggerOttoResume(320);
  };

  const handleGovernanceClick = () => {
    setIsGovernanceSigned(true);
    triggerOttoResume(250);
  };

  const triggerOttoResume = (latency: number) => {
    setResumedLatencyMs(latency);
    if (onChallengeResolved) {
      setTimeout(() => {
        onChallengeResolved();
      }, 500);
    }
  };

  const resetAll = () => {
    setIsTurnstileChecking(false);
    setIsTurnstileSolved(false);
    setSliderPosition(0);
    setIsSliderSolved(false);
    setIsPasskeyApproved(false);
    setIsPaymentConfirmed(false);
    setIsGovernanceSigned(false);
    setResumedLatencyMs(null);
  };

  return (
    <div className="space-y-6">
      {/* Luxury Trust Banner */}
      <div className="rounded-2xl border border-amber-500/30 bg-gradient-to-b from-slate-900 to-slate-950 p-6 shadow-2xl relative overflow-hidden">
        <div className="absolute top-0 right-0 -mr-16 -mt-16 w-64 h-64 rounded-full bg-amber-500/10 blur-3xl pointer-events-none" />

        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4 relative z-10">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-amber-500/10 border border-amber-500/20 text-amber-300 text-xs font-mono mb-2">
              <ShieldAlert className="w-3.5 h-3.5" />
              <span>SECTION 6: DELIBERATE TRUST BOUNDARY & LUXURY HANDOVER</span>
            </div>
            <h2 className="text-2xl font-bold text-white font-display">
              The Luxury 1-Tap Handover Experience
            </h2>
            <p className="text-sm text-slate-400 max-w-2xl mt-1">
              Otto <span className="text-rose-400 font-semibold">NEVER</span> tries to solve or bypass CAPTCHAs automatically (breaking site terms & risking accounts). Instead, Otto beams the exact screen instantly to the founder's phone, watch, or glasses for a <span className="text-amber-300 font-semibold">single tap resolution</span>.
            </p>
          </div>

          <button
            onClick={resetAll}
            className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 text-slate-300 hover:text-white border border-slate-800 text-xs font-mono transition-colors self-start lg:self-auto"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>Reset Challenges</span>
          </button>
        </div>

        {/* Handover Surface Nodes */}
        <div className="mt-6 flex flex-wrap items-center gap-3 text-xs font-mono">
          <span className="text-slate-400">Push Handover Nodes:</span>
          <span className="px-2.5 py-1 rounded-lg bg-slate-900 border border-slate-800 text-slate-200 flex items-center gap-1.5">
            <Smartphone className="w-3.5 h-3.5 text-cyan-400" />
            <span>Founder iPhone / Pixel</span>
          </span>
          <span className="px-2.5 py-1 rounded-lg bg-slate-900 border border-slate-800 text-slate-200 flex items-center gap-1.5">
            <Watch className="w-3.5 h-3.5 text-amber-400" />
            <span>Watch Ultra 2 (Haptic)</span>
          </span>
          <span className="px-2.5 py-1 rounded-lg bg-slate-900 border border-slate-800 text-slate-200 flex items-center gap-1.5">
            <Glasses className="w-3.5 h-3.5 text-indigo-400" />
            <span>AR Glasses (HUD Tap)</span>
          </span>
        </div>
      </div>

      {/* Challenge Type Tabs */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-2">
        {[
          { id: 'turnstile', label: 'Cloudflare Turnstile', icon: ShieldAlert },
          { id: 'slider', label: 'Slider Puzzle', icon: Lock },
          { id: 'passkey', label: 'Bitwarden Passkey', icon: Fingerprint },
          { id: 'payment', label: 'Purchase Approval', icon: CreditCard },
          { id: 'governance', label: 'Gate Signature', icon: FileCheck }
        ].map(item => {
          const Icon = item.icon;
          const isSelected = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id as any)}
              className={`p-3 rounded-xl border flex flex-col items-center justify-center text-center transition-all ${
                isSelected
                  ? 'border-amber-400 bg-amber-950/30 text-white shadow-lg shadow-amber-500/10'
                  : 'border-slate-800 bg-slate-900/40 text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
              }`}
            >
              <Icon className={`w-4 h-4 mb-1.5 ${isSelected ? 'text-amber-400' : 'text-slate-500'}`} />
              <span className="text-xs font-semibold">{item.label}</span>
            </button>
          );
        })}
      </div>

      {/* Interactive Handover Simulation Card */}
      <div className="rounded-2xl border border-slate-800 bg-slate-950 p-6 shadow-xl">
        <div className="max-w-xl mx-auto space-y-6">
          <div className="text-center space-y-1">
            <div className="text-xs font-mono uppercase tracking-wider text-amber-400 font-bold">
              Autonomous Handover Triggered
            </div>
            <h3 className="text-lg font-bold text-white font-display">
              {activeTab === 'turnstile' && 'Cloudflare Turnstile Challenge'}
              {activeTab === 'slider' && 'Anti-Bot Spatial Alignment'}
              {activeTab === 'passkey' && 'Bitwarden Session Vault Authorization'}
              {activeTab === 'payment' && 'Cloud Infrastructure Expense Gate'}
              {activeTab === 'governance' && 'Commit Gate Air-Gap Signature'}
            </h3>
            <p className="text-xs text-slate-400">
              Otto paused the cloud browser and queued execution. Tap once below to resolve.
            </p>
          </div>

          {/* CHALLENGE 1: CLOUDFLARE TURNSTILE */}
          {activeTab === 'turnstile' && (
            <div className="p-6 rounded-xl bg-slate-900/90 border border-slate-700 max-w-sm mx-auto shadow-2xl space-y-4">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <span className="text-xs font-semibold text-slate-200">Cloudflare Verification</span>
                <span className="text-[10px] font-mono text-slate-500">Ray ID: 890ab2c41</span>
              </div>

              <div
                onClick={!isTurnstileSolved ? handleTurnstileClick : undefined}
                className={`p-4 rounded-lg border-2 flex items-center justify-between cursor-pointer transition-all ${
                  isTurnstileSolved
                    ? 'border-emerald-500 bg-emerald-950/20 text-emerald-300'
                    : isTurnstileChecking
                    ? 'border-amber-400 bg-amber-950/20 text-amber-200 animate-pulse'
                    : 'border-slate-600 bg-slate-950 hover:border-cyan-400 text-slate-300'
                }`}
              >
                <div className="flex items-center gap-3">
                  <div className={`w-6 h-6 rounded border flex items-center justify-center transition-colors ${
                    isTurnstileSolved
                      ? 'border-emerald-500 bg-emerald-500 text-slate-950'
                      : isTurnstileChecking
                      ? 'border-amber-400'
                      : 'border-slate-500'
                  }`}>
                    {isTurnstileSolved && <CheckCircle2 className="w-4 h-4 fill-current" />}
                    {isTurnstileChecking && <div className="w-3 h-3 rounded-full border-2 border-amber-400 border-t-transparent animate-spin" />}
                  </div>
                  <span className="text-xs font-medium">
                    {isTurnstileSolved ? 'Human Verified' : isTurnstileChecking ? 'Verifying...' : 'Verify you are human'}
                  </span>
                </div>

                <div className="text-[10px] text-slate-500 font-mono flex flex-col items-end">
                  <span>Cloudflare</span>
                  <span className="text-[8px]">Privacy · Terms</span>
                </div>
              </div>
            </div>
          )}

          {/* CHALLENGE 2: SLIDER PUZZLE */}
          {activeTab === 'slider' && (
            <div className="p-6 rounded-xl bg-slate-900/90 border border-slate-700 max-w-sm mx-auto shadow-2xl space-y-4">
              <div className="text-xs font-semibold text-slate-200">Slide to Complete the Shape</div>
              
              <div className="h-28 bg-slate-950 rounded-lg border border-slate-800 relative overflow-hidden flex items-center">
                {/* Target Slot */}
                <div className="absolute right-8 w-10 h-10 border-2 border-dashed border-amber-400/80 rounded bg-amber-500/10 flex items-center justify-center">
                  <span className="text-[9px] text-amber-400 font-mono">TARGET</span>
                </div>

                {/* Movable Piece */}
                <div
                  className="absolute w-10 h-10 rounded bg-cyan-500 border border-white flex items-center justify-center text-slate-950 shadow-lg transition-all"
                  style={{ left: `${sliderPosition * 2.2 + 8}px` }}
                >
                  <Lock className="w-4 h-4" />
                </div>
              </div>

              <div className="space-y-1">
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={sliderPosition}
                  onChange={handleSliderChange}
                  className="w-full h-2 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-cyan-400"
                />
                <div className="text-[10px] font-mono text-slate-400 text-center">
                  {isSliderSolved ? 'Aligned! Passing to Otto...' : 'Drag slider to dock piece (approx 90%)'}
                </div>
              </div>
            </div>
          )}

          {/* CHALLENGE 3: PASSKEY */}
          {activeTab === 'passkey' && (
            <div className="p-6 rounded-xl bg-slate-900/90 border border-slate-700 max-w-sm mx-auto shadow-2xl text-center space-y-4">
              <div className="w-12 h-12 rounded-full bg-indigo-500/20 text-indigo-400 flex items-center justify-center mx-auto">
                <Fingerprint className="w-7 h-7" />
              </div>
              <div>
                <div className="font-semibold text-white text-sm">Bitwarden Touch ID Request</div>
                <div className="text-xs text-slate-400 mt-0.5">Approve access to cloud cluster credentials</div>
              </div>
              <button
                onClick={handlePasskeyClick}
                disabled={isPasskeyApproved}
                className={`w-full py-2.5 rounded-xl font-bold text-xs transition-all ${
                  isPasskeyApproved
                    ? 'bg-emerald-600 text-white'
                    : 'bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-600/30'
                }`}
              >
                {isPasskeyApproved ? 'Passkey Approved ✓' : 'Approve with Touch ID / Face ID'}
              </button>
            </div>
          )}

          {/* CHALLENGE 4: PAYMENT */}
          {activeTab === 'payment' && (
            <div className="p-6 rounded-xl bg-slate-900/90 border border-slate-700 max-w-sm mx-auto shadow-2xl space-y-4">
              <div className="flex items-center justify-between text-xs border-b border-slate-800 pb-2">
                <span className="font-semibold text-white">Cloud GPU Runner Reserve</span>
                <span className="font-bold text-amber-400 font-mono">$1,420.00</span>
              </div>
              <div className="text-[11px] text-slate-400 space-y-1">
                <div>• 2x NVIDIA H100 SXM5 (128h reservation)</div>
                <div>• Zero-spend tier exhausted for cluster</div>
              </div>
              <button
                onClick={handlePaymentClick}
                disabled={isPaymentConfirmed}
                className={`w-full py-2.5 rounded-xl font-bold text-xs transition-all ${
                  isPaymentConfirmed
                    ? 'bg-emerald-600 text-white'
                    : 'bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold'
                }`}
              >
                {isPaymentConfirmed ? 'Purchase Confirmed ✓' : 'Confirm Purchase (Founder Apple Pay)'}
              </button>
            </div>
          )}

          {/* CHALLENGE 5: GOVERNANCE */}
          {activeTab === 'governance' && (
            <div className="p-6 rounded-xl bg-slate-900/90 border border-slate-700 max-w-sm mx-auto shadow-2xl space-y-4 text-center">
              <div className="w-12 h-12 rounded-full bg-cyan-500/20 text-cyan-400 flex items-center justify-center mx-auto">
                <FileCheck className="w-7 h-7" />
              </div>
              <div>
                <div className="font-semibold text-white text-sm">Airlock Gate Sign-Off</div>
                <div className="text-xs text-slate-400 mt-0.5">Cryptographic gate verdict for propose/otto-v1</div>
              </div>
              <button
                onClick={handleGovernanceClick}
                disabled={isGovernanceSigned}
                className={`w-full py-2.5 rounded-xl font-bold text-xs transition-all ${
                  isGovernanceSigned
                    ? 'bg-emerald-600 text-white'
                    : 'bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold'
                }`}
              >
                {isGovernanceSigned ? 'Signed & Merged ✓' : 'One-Tap Sign & Authorize Gate'}
              </button>
            </div>
          )}

          {/* Otto Resumption Result Banner */}
          {resumedLatencyMs !== null && (
            <div className="p-4 rounded-xl bg-emerald-950/40 border border-emerald-500/40 text-emerald-300 text-xs flex items-center justify-between animate-fadeIn">
              <div className="flex items-center gap-2">
                <Zap className="w-4 h-4 text-emerald-400" />
                <span className="font-semibold">
                  Signal Received! Otto resumed autonomously in {resumedLatencyMs}ms.
                </span>
              </div>
              <span className="font-mono text-[10px] text-emerald-400">0 FOUNDER HUNTING</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
