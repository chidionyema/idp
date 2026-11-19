import React, { useState } from 'react';
import { 
  UserCheck, 
  Smartphone, 
  QrCode, 
  ShieldCheck, 
  Heart, 
  Terminal, 
  Sparkles, 
  CheckCircle2, 
  ArrowRight, 
  Lock, 
  Play, 
  Volume2, 
  Key,
  Layers,
  Clock,
  RotateCcw
} from 'lucide-react';

export const FamilyAndFounderOnboarding: React.FC = () => {
  const [activePathway, setActivePathway] = useState<'founder' | 'family-kin'>('family-kin');
  const [onboardingStep, setOnboardingStep] = useState<number>(1);
  const [isFamilySetupDone, setIsFamilySetupDone] = useState(false);
  const [isPlayingGreeting, setIsPlayingGreeting] = useState(false);

  const handleSimulateFounderOnboard = () => {
    setOnboardingStep(1);
    const interval = setInterval(() => {
      setOnboardingStep(prev => {
        if (prev >= 4) {
          clearInterval(interval);
          return 4;
        }
        return prev + 1;
      });
    }, 700);
  };

  const handleSimulateKinOnboard = () => {
    setIsFamilySetupDone(true);
    if (typeof window !== 'undefined' && window.speechSynthesis) {
      window.speechSynthesis.cancel();
      const greeting = 'Peace be with you, Sister Beatrice. Your nephew set me up on your iPad to quietly assist you with prayers, medications, and to keep robocalls away. You never need to worry about any technology.';
      const utterance = new SpeechSynthesisUtterance(greeting);
      utterance.rate = 0.9;
      utterance.pitch = 0.95;
      utterance.onend = () => setIsPlayingGreeting(false);
      setIsPlayingGreeting(true);
      window.speechSynthesis.speak(utterance);
    }
  };

  return (
    <div className="space-y-6">
      {/* Banner */}
      <div className="rounded-2xl border border-emerald-500/30 bg-gradient-to-b from-slate-900 to-slate-950 p-6 shadow-2xl relative overflow-hidden">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4 relative z-10">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-xs font-mono mb-2">
              <UserCheck className="w-3.5 h-3.5" />
              <span>ONBOARDING &amp; QUALITY ASSURANCE PROTOCOLS</span>
            </div>
            <h2 className="text-2xl font-bold text-white font-display">
              Two Tailored Onboarding Pathways
            </h2>
            <p className="text-sm text-slate-400 max-w-2xl mt-1">
              Onboarding is designed for two polar realities: <span className="text-cyan-400 font-semibold">60-second zero-setup autonomous boot</span> for the retired Google founder, and a <span className="text-rose-300 font-semibold">1-tap frictionless iPad scan</span> for non-technical family members like Elder Sister Beatrice.
            </p>
          </div>

          {/* Pathway Selector */}
          <div className="flex rounded-xl bg-slate-900 border border-slate-800 p-1 text-xs font-mono">
            <button
              onClick={() => setActivePathway('founder')}
              className={`px-3.5 py-2 rounded-lg font-bold transition-all ${
                activePathway === 'founder'
                  ? 'bg-cyan-500 text-slate-950 shadow-md'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              Founder Sovereign (60s)
            </button>
            <button
              onClick={() => setActivePathway('family-kin')}
              className={`px-3.5 py-2 rounded-lg font-bold transition-all flex items-center gap-1.5 ${
                activePathway === 'family-kin'
                  ? 'bg-rose-600 text-white shadow-md'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <Heart className="w-3.5 h-3.5 fill-current" />
              <span>Elder Nun (Family Kin)</span>
            </button>
          </div>
        </div>
      </div>

      {/* PATHWAY 1: FOUNDER SOVEREIGN ONBOARDING */}
      {activePathway === 'founder' && (
        <div className="rounded-2xl border border-slate-800 bg-slate-950 p-6 shadow-xl space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-slate-800 pb-4">
            <div>
              <div className="text-xs font-mono text-cyan-400 font-bold uppercase tracking-wider">
                PATHWAY A: THE RETIRED FOUNDER
              </div>
              <h3 className="text-lg font-bold text-white font-display mt-0.5">
                Zero-Question, Zero-Setup Sovereign Boot
              </h3>
              <p className="text-xs text-slate-400 max-w-xl">
                The founder never types secrets, fills out onboarding wizards, or attaches workspaces manually. Otto executes cold-discovery autonomously.
              </p>
            </div>

            <button
              onClick={handleSimulateFounderOnboard}
              className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-mono font-bold text-xs shadow-md transition-all self-start sm:self-auto"
            >
              <Play className="w-3.5 h-3.5 fill-current" />
              <span>Simulate 60s Flow</span>
            </button>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-4 gap-3">
            {[
              { step: 1, title: 'Wake on Host', desc: 'Auto-detects Darwin / Linux host & sends Telegram greeting.' },
              { step: 2, title: 'Self-Discovery', desc: 'Reads argon repos, Bitwarden socket, adb/Xcode certs.' },
              { step: 3, title: 'Self-Inventory Card', desc: 'Delivers 1 executive card with working/missing assets.' },
              { step: 4, title: 'Fixes Bottleneck', desc: 'Autonomously starts fixing worst blocker (<100s steps).' }
            ].map(s => {
              const isPastOrCurrent = onboardingStep >= s.step;
              const isCurrent = onboardingStep === s.step;
              return (
                <div
                  key={s.step}
                  className={`p-4 rounded-xl border transition-all text-xs font-mono ${
                    isCurrent
                      ? 'border-cyan-400 bg-cyan-950/40 text-white ring-1 ring-cyan-400'
                      : isPastOrCurrent
                      ? 'border-emerald-500/50 bg-emerald-950/20 text-emerald-300'
                      : 'border-slate-800 bg-slate-900/40 text-slate-500'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1.5 font-bold">
                    <span>STEP {s.step}</span>
                    {isPastOrCurrent ? <CheckCircle2 className="w-4 h-4 text-emerald-400" /> : <Clock className="w-4 h-4 text-slate-600" />}
                  </div>
                  <div className="text-white font-semibold text-xs mb-1">{s.title}</div>
                  <div className="text-[11px] text-slate-400 leading-snug">{s.desc}</div>
                </div>
              );
            })}
          </div>

          <div className="p-3 rounded-lg bg-slate-900 border border-slate-800 text-xs font-mono text-slate-400 flex items-center justify-between">
            <span>Result: Founder first interaction requires exactly 0 setup steps. Measured in eval E1.</span>
            <span className="text-emerald-400 font-bold">PASSED IN 48.2s</span>
          </div>
        </div>
      )}

      {/* PATHWAY 2: FAMILY MEMBER / ELDER NUN ONBOARDING */}
      {activePathway === 'family-kin' && (
        <div className="rounded-2xl border border-rose-300/20 bg-stone-950 p-6 shadow-xl space-y-6 font-serif">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-stone-800 pb-4">
            <div>
              <div className="text-xs font-mono text-rose-400 font-bold uppercase tracking-wider">
                PATHWAY B: ELDER NUN (SISTER BEATRICE)
              </div>
              <h3 className="text-xl font-bold text-stone-100 mt-0.5">
                Frictionless 1-Tap QR / NFC Invitation
              </h3>
              <p className="text-xs text-stone-400 max-w-xl font-sans">
                The founder sets this up on Aunt Bea's iPad or gives her a card. She never sees a password, setting, or terminal prompt.
              </p>
            </div>

            <button
              onClick={handleSimulateKinOnboard}
              className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-rose-600 hover:bg-rose-500 text-white font-sans font-bold text-xs shadow-md transition-all self-start sm:self-auto"
            >
              <QrCode className="w-4 h-4" />
              <span>Simulate 1-Tap iPad Setup</span>
            </button>
          </div>

          {/* iPad Frame Simulation */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-center">
            {/* Left: Founder's Generated Invitation Card */}
            <div className="lg:col-span-5 space-y-3 font-sans text-xs">
              <div className="p-4 rounded-xl bg-stone-900 border border-stone-800 space-y-3">
                <div className="flex items-center justify-between text-stone-300">
                  <span className="font-bold flex items-center gap-1.5">
                    <Lock className="w-3.5 h-3.5 text-emerald-400" />
                    Cryptographic Kin Token
                  </span>
                  <span className="text-[10px] font-mono text-emerald-400">AIR-GAPPED</span>
                </div>

                <div className="p-3 rounded-lg bg-stone-950 border border-stone-800 text-[11px] space-y-1 text-stone-400 font-mono">
                  <div>Holder: Sister Beatrice (Aunt Bea)</div>
                  <div>Permissions: Liturgy Audio, Health, Scam Shield</div>
                  <div className="text-rose-400 font-bold">Quarantined: Zero cloud keys, zero git access</div>
                </div>

                <div className="flex items-center justify-center p-4 bg-white rounded-xl max-w-[140px] mx-auto shadow-md">
                  <QrCode className="w-24 h-24 text-stone-950" />
                </div>
                <div className="text-center text-[10px] text-stone-500">
                  Scan once with iPad camera or tap NFC card
                </div>
              </div>
            </div>

            {/* Right: Elder Sister Beatrice's Screen */}
            <div className="lg:col-span-7">
              <div className="rounded-2xl border-4 border-stone-800 bg-stone-900/90 p-6 shadow-2xl space-y-4 text-center">
                <div className="w-16 h-16 rounded-full bg-rose-500/20 text-rose-300 flex items-center justify-center mx-auto shadow-inner">
                  <Heart className="w-8 h-8 fill-current" />
                </div>

                <div className="space-y-1">
                  <h4 className="text-2xl font-bold text-stone-100">Welcome, Sister Beatrice</h4>
                  <p className="text-sm text-stone-300 max-w-md mx-auto leading-relaxed">
                    Otto is now quietly active on your iPad. All setup is complete.
                  </p>
                </div>

                <div className="p-4 rounded-xl bg-stone-950/80 border border-stone-800 text-left space-y-2 text-xs text-stone-300 max-w-md mx-auto">
                  <div className="flex items-center gap-2 text-emerald-400 font-bold font-sans">
                    <CheckCircle2 className="w-4 h-4" />
                    <span>Liturgy of the Hours synced with chapel bells</span>
                  </div>
                  <div className="flex items-center gap-2 text-emerald-400 font-bold font-sans">
                    <CheckCircle2 className="w-4 h-4" />
                    <span>Silent robocall &amp; scam filter armed</span>
                  </div>
                  <div className="flex items-center gap-2 text-emerald-400 font-bold font-sans">
                    <CheckCircle2 className="w-4 h-4" />
                    <span>Direct line to your nephew connected</span>
                  </div>
                </div>

                <div className="pt-2">
                  <button
                    onClick={handleSimulateKinOnboard}
                    className="px-6 py-2.5 rounded-full bg-rose-600 hover:bg-rose-500 text-white font-sans font-bold text-xs shadow-lg shadow-rose-600/30 transition-all inline-flex items-center gap-2"
                  >
                    <Volume2 className="w-4 h-4" />
                    <span>{isPlayingGreeting ? 'Speaking to Aunt Bea...' : 'Play Warm Voice Welcome'}</span>
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Quality Assurance (QA) Engine Summary */}
      <div className="rounded-2xl border border-slate-800 bg-slate-950 p-6 shadow-xl space-y-3 font-mono text-xs">
        <div className="flex items-center justify-between border-b border-slate-800 pb-2">
          <span className="font-bold text-white uppercase tracking-wider flex items-center gap-1.5">
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
            Quality Assurance (QA) Engine: Blind Verifier Architecture
          </span>
          <span className="text-cyan-400">Zero-Knowledge Gate Proofs</span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-1">
          <div className="p-3 rounded-lg bg-slate-900 border border-slate-800 space-y-1">
            <span className="text-slate-400 text-[10px] block uppercase font-bold">Blind Isolation QA</span>
            <div className="text-white font-bold">Unbiased Validation</div>
            <div className="text-[11px] text-slate-400">
              The QA Verifier agent does not see code synthesis during construction, preventing self-reinforcing bias.
            </div>
          </div>

          <div className="p-3 rounded-lg bg-slate-900 border border-slate-800 space-y-1">
            <span className="text-slate-400 text-[10px] block uppercase font-bold">Continuous Regression</span>
            <div className="text-emerald-400 font-bold">12/12 Strict Evals</div>
            <div className="text-[11px] text-slate-400">
              Full suite executed on every commit with 0 tie tolerance. Tie is scored as a fail.
            </div>
          </div>

          <div className="p-3 rounded-lg bg-slate-900 border border-slate-800 space-y-1">
            <span className="text-slate-400 text-[10px] block uppercase font-bold">Air-Gap Certification</span>
            <div className="text-purple-400 font-bold">Zero Cross-Taint</div>
            <div className="text-[11px] text-slate-400">
              Verified that family iPad interactions can never leak estate credentials or git commit rights.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
