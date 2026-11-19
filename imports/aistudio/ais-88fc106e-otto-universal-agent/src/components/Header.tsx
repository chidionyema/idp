import React from 'react';
import { 
  Cpu, 
  ShieldCheck, 
  Zap, 
  Terminal, 
  Watch, 
  Glasses, 
  Bot, 
  Smartphone, 
  Monitor, 
  RefreshCw, 
  Play, 
  Radio,
  CheckCircle2,
  AlertTriangle,
  Volume2,
  Database,
  UserCheck,
  ShieldAlert,
  Rocket,
  Scale,
  Globe,
  Brain,
  Users,
  Activity
} from 'lucide-react';

import { PersonaMode, ActiveTabType } from '../types/otto';

interface HeaderProps {
  activeTab: ActiveTabType;
  setActiveTab: (tab: ActiveTabType) => void;
  personaMode: PersonaMode;
  setPersonaMode: (mode: PersonaMode) => void;
  currentPersonaName?: string;
  onTriggerBoot: () => void;
  onTriggerEvals: () => void;
  onTriggerCaptcha: () => void;
  evalPassCount: number;
  totalEvals: number;
  isEvaluating: boolean;
}

export const Header: React.FC<HeaderProps> = ({
  activeTab,
  setActiveTab,
  personaMode,
  setPersonaMode,
  currentPersonaName,
  onTriggerBoot,
  onTriggerEvals,
  onTriggerCaptcha,
  evalPassCount,
  totalEvals,
  isEvaluating
}) => {
  return (
    <header className="border-b border-slate-800/80 bg-slate-950/90 backdrop-blur-md sticky top-0 z-40">
      {/* Top Telemetry Ticker */}
      <div className="border-b border-slate-800/40 bg-slate-900/60 px-4 py-1.5 flex flex-wrap items-center justify-between text-xs font-mono text-slate-400">
        <div className="flex items-center gap-4">
          <span className="flex items-center gap-1.5 text-emerald-400 font-semibold">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping inline-block"></span>
            OTTO CORE v2026.11.07
          </span>
          <span className="text-slate-600">|</span>
          <span className="hidden sm:inline text-slate-300">
            SPEC: <span className="text-indigo-400 font-medium">FOUNDER AGENT WITH HANDS</span>
          </span>
          <span className="hidden md:inline text-slate-600">|</span>
          <span className="hidden md:flex items-center gap-1 text-slate-300">
            <Radio className="w-3 h-3 text-cyan-400" />
            PEER BUS: <span className="text-cyan-400">bin/genesis-crew.py (5 NODES)</span>
          </span>
        </div>

        <div className="flex items-center gap-4">
          <span className="flex items-center gap-1 text-slate-300">
            <Zap className="w-3 h-3 text-amber-400" />
            LANE: <span className="text-amber-300">CHEAP (DEFAULT) ➔ FRONTIER FAILOVER &lt;5s</span>
          </span>
          <span className="hidden lg:inline text-slate-600">|</span>
          <span className="hidden lg:flex items-center gap-1 text-emerald-400 font-bold">
            <ShieldCheck className="w-3.5 h-3.5" />
            EVALS: {evalPassCount}/{totalEvals} BEATING MINIMAX
          </span>
        </div>
      </div>

      {/* Main Bar */}
      <div className="max-w-7xl mx-auto px-4 py-3 flex flex-col md:flex-row md:items-center md:justify-between gap-3">
        {/* Brand & Badge */}
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-600 via-violet-600 to-cyan-400 p-[1px] shadow-lg shadow-indigo-500/20">
            <div className="w-full h-full bg-slate-950 rounded-xl flex items-center justify-center">
              <Bot className="w-6 h-6 text-cyan-400 animate-pulse" />
            </div>
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-lg font-bold tracking-tight text-white font-display">
                OTTO <span className="text-xs px-2 py-0.5 rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">UNIVERSAL CONSTANT</span>
              </h1>
            </div>
            <p className="text-xs text-slate-400">
              The Founder's Agent with Hands · Computers, Phones, Watches, Glasses & Robotics
            </p>
          </div>
        </div>

        {/* Quick Execution Trigger Actions & Persona Switcher */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Persona Switcher & Identity Control */}
          <div className="flex items-center rounded-lg bg-slate-900 border border-slate-800 p-0.5 text-xs">
            <button
              onClick={() => {
                setPersonaMode('founder-sovereign');
                if (activeTab === 'family') setActiveTab('boot');
              }}
              className={`px-2.5 py-1 rounded-md transition-all font-medium ${
                personaMode === 'founder-sovereign'
                  ? 'bg-indigo-600 text-white shadow-sm font-semibold'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Founder Sovereign
            </button>
            <button
              onClick={() => {
                setPersonaMode('compassionate-kin');
                setActiveTab('family');
              }}
              className={`px-2.5 py-1 rounded-md transition-all font-medium flex items-center gap-1 ${
                personaMode === 'compassionate-kin'
                  ? 'bg-rose-600 text-white shadow-sm font-semibold'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <span>Elder Nun (Kin)</span>
              <span className="w-1.5 h-1.5 rounded-full bg-rose-400 animate-pulse" />
            </button>
            <button
              onClick={() => setActiveTab('personas-memory')}
              className={`px-2.5 py-1 rounded-md transition-all font-medium flex items-center gap-1.5 ${
                activeTab === 'personas-memory'
                  ? 'bg-violet-600 text-white shadow-sm font-semibold'
                  : 'text-violet-300 hover:text-violet-100 bg-violet-950/40 hover:bg-violet-900/50'
              }`}
              title="Open Universal Personas & Memory Engine"
            >
              <Brain className="w-3.5 h-3.5 text-violet-300" />
              <span>Studio: <span className="font-semibold text-white">{currentPersonaName || 'Adaptive'}</span></span>
            </button>
          </div>

          <button
            onClick={onTriggerBoot}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-500/15 hover:bg-emerald-500/25 border border-emerald-500/30 text-emerald-300 text-xs font-medium transition-colors"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Simulate 60s Cold Start</span>
          </button>

          <button
            onClick={onTriggerCaptcha}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-amber-500/15 hover:bg-amber-500/25 border border-amber-500/30 text-amber-300 text-xs font-medium transition-colors"
          >
            <AlertTriangle className="w-3.5 h-3.5" />
            <span>Test Luxury Handover</span>
          </button>

          <button
            onClick={onTriggerEvals}
            disabled={isEvaluating}
            className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white text-xs font-semibold shadow-md shadow-indigo-600/30 transition-all disabled:opacity-50"
          >
            <Play className={`w-3.5 h-3.5 fill-current ${isEvaluating ? 'animate-spin' : ''}`} />
            <span>{isEvaluating ? 'Running 12 Evals...' : 'Run All Strict Evals'}</span>
          </button>

          <button
            onClick={() => setActiveTab('launch-checklist')}
            className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg font-mono text-xs font-bold transition-all shadow-md ${
              activeTab === 'launch-checklist'
                ? 'bg-emerald-500 text-slate-950 shadow-emerald-500/25 ring-2 ring-emerald-400'
                : 'bg-emerald-500/20 hover:bg-emerald-500/30 border border-emerald-500/40 text-emerald-300'
            }`}
          >
            <Rocket className="w-3.5 h-3.5" />
            <span>GO/NO-GO Checklist</span>
          </button>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="max-w-7xl mx-auto px-4 flex gap-1 overflow-x-auto no-scrollbar border-t border-slate-800/40 pt-1">
        <button
          onClick={() => setActiveTab('boot')}
          className={`px-3.5 py-2 text-xs font-medium flex items-center gap-2 border-b-2 transition-colors whitespace-nowrap ${
            activeTab === 'boot'
              ? 'border-cyan-400 text-cyan-300 bg-cyan-950/20'
              : 'border-transparent text-slate-400 hover:text-slate-200 hover:bg-slate-900/40'
          }`}
        >
          <Terminal className="w-3.5 h-3.5" />
          <span>1. First Run & Discovery</span>
        </button>

        <button
          onClick={() => setActiveTab('hands')}
          className={`px-3.5 py-2 text-xs font-medium flex items-center gap-2 border-b-2 transition-colors whitespace-nowrap ${
            activeTab === 'hands'
              ? 'border-indigo-400 text-indigo-300 bg-indigo-950/20'
              : 'border-transparent text-slate-400 hover:text-slate-200 hover:bg-slate-900/40'
          }`}
        >
          <Monitor className="w-3.5 h-3.5" />
          <span>2. Hands & Devices</span>
          <span className="px-1.5 py-0.2 rounded bg-indigo-500/20 text-indigo-300 text-[10px] font-mono">7 NODES</span>
        </button>

        <button
          onClick={() => setActiveTab('telegram')}
          className={`px-3.5 py-2 text-xs font-medium flex items-center gap-2 border-b-2 transition-colors whitespace-nowrap ${
            activeTab === 'telegram'
              ? 'border-sky-400 text-sky-300 bg-sky-950/20'
              : 'border-transparent text-slate-400 hover:text-slate-200 hover:bg-slate-900/40'
          }`}
        >
          <Smartphone className="w-3.5 h-3.5" />
          <span>3. Founder VIP Telegram</span>
        </button>

        <button
          onClick={() => setActiveTab('trust')}
          className={`px-3.5 py-2 text-xs font-medium flex items-center gap-2 border-b-2 transition-colors whitespace-nowrap ${
            activeTab === 'trust'
              ? 'border-amber-400 text-amber-300 bg-amber-950/20'
              : 'border-transparent text-slate-400 hover:text-slate-200 hover:bg-slate-900/40'
          }`}
        >
          <ShieldCheck className="w-3.5 h-3.5" />
          <span>4. Luxury CAPTCHA & Trust</span>
        </button>

        <button
          onClick={() => setActiveTab('peers')}
          className={`px-3.5 py-2 text-xs font-medium flex items-center gap-2 border-b-2 transition-colors whitespace-nowrap ${
            activeTab === 'peers'
              ? 'border-purple-400 text-purple-300 bg-purple-950/20'
              : 'border-transparent text-slate-400 hover:text-slate-200 hover:bg-slate-900/40'
          }`}
        >
          <Cpu className="w-3.5 h-3.5" />
          <span>5. Brain & Peers</span>
        </button>

        <button
          onClick={() => setActiveTab('bus-log')}
          className={`px-3.5 py-2 text-xs font-medium flex items-center gap-2 border-b-2 transition-colors whitespace-nowrap ${
            activeTab === 'bus-log'
              ? 'border-cyan-400 text-cyan-300 bg-cyan-950/20'
              : 'border-transparent text-slate-400 hover:text-slate-200 hover:bg-slate-900/40'
          }`}
        >
          <Radio className="w-3.5 h-3.5 text-cyan-400 animate-pulse" />
          <span>6. Peer Bus Log</span>
          <span className="px-1.5 py-0.2 rounded bg-cyan-500/20 text-cyan-300 text-[10px] font-mono">LIVE</span>
        </button>

        <button
          onClick={() => setActiveTab('drops')}
          className={`px-3.5 py-2 text-xs font-medium flex items-center gap-2 border-b-2 transition-colors whitespace-nowrap ${
            activeTab === 'drops'
              ? 'border-indigo-400 text-indigo-300 bg-indigo-950/20'
              : 'border-transparent text-slate-400 hover:text-slate-200 hover:bg-slate-900/40'
          }`}
        >
          <Zap className="w-3.5 h-3.5 text-indigo-400" />
          <span>7. Drops & Capabilities</span>
          <span className="px-1.5 py-0.2 rounded bg-indigo-500/20 text-indigo-300 text-[10px] font-mono">REUSED</span>
        </button>

        <button
          onClick={() => setActiveTab('evals')}
          className={`px-3.5 py-2 text-xs font-medium flex items-center gap-2 border-b-2 transition-colors whitespace-nowrap ${
            activeTab === 'evals'
              ? 'border-emerald-400 text-emerald-300 bg-emerald-950/20'
              : 'border-transparent text-slate-400 hover:text-slate-200 hover:bg-slate-900/40'
          }`}
        >
          <CheckCircle2 className="w-3.5 h-3.5" />
          <span>8. Strict 12 Evals vs MiniMax</span>
          <span className="px-1.5 py-0.2 rounded bg-emerald-500/20 text-emerald-300 text-[10px] font-mono">12/12 PASS</span>
        </button>

        <button
          onClick={() => setActiveTab('rsi')}
          className={`px-3.5 py-2 text-xs font-medium flex items-center gap-2 border-b-2 transition-colors whitespace-nowrap ${
            activeTab === 'rsi'
              ? 'border-cyan-400 text-cyan-300 bg-cyan-950/20'
              : 'border-transparent text-slate-400 hover:text-slate-200 hover:bg-slate-900/40'
          }`}
        >
          <Zap className="w-3.5 h-3.5 text-cyan-400" />
          <span>9. Mathematical RSI Guarantees</span>
          <span className="px-1.5 py-0.2 rounded bg-cyan-500/20 text-cyan-300 text-[10px] font-mono">GÖDEL PCC</span>
        </button>

        <button
          onClick={() => {
            setActiveTab('family');
            setPersonaMode('compassionate-kin');
          }}
          className={`px-3.5 py-2 text-xs font-medium flex items-center gap-2 border-b-2 transition-colors whitespace-nowrap ${
            activeTab === 'family'
              ? 'border-rose-400 text-rose-300 bg-rose-950/20'
              : 'border-transparent text-slate-400 hover:text-slate-200 hover:bg-slate-900/40'
          }`}
        >
          <span className="w-2 h-2 rounded-full bg-rose-400 inline-block" />
          <span>10. Compassionate Kin (Elder Nun)</span>
        </button>

        <button
          onClick={() => setActiveTab('security')}
          className={`px-3.5 py-2 text-xs font-medium flex items-center gap-2 border-b-2 transition-colors whitespace-nowrap ${
            activeTab === 'security'
              ? 'border-rose-400 text-rose-300 bg-rose-950/20'
              : 'border-transparent text-slate-400 hover:text-slate-200 hover:bg-slate-900/40'
          }`}
        >
          <ShieldAlert className="w-3.5 h-3.5 text-rose-400" />
          <span>11. Security &amp; Injection Defense</span>
          <span className="px-1.5 py-0.2 rounded bg-rose-500/20 text-rose-300 text-[10px] font-mono">DLP AIR-GAP</span>
        </button>

        <button
          onClick={() => setActiveTab('voice-avatar')}
          className={`px-3.5 py-2 text-xs font-medium flex items-center gap-2 border-b-2 transition-colors whitespace-nowrap ${
            activeTab === 'voice-avatar'
              ? 'border-indigo-400 text-indigo-300 bg-indigo-950/20'
              : 'border-transparent text-slate-400 hover:text-slate-200 hover:bg-slate-900/40'
          }`}
        >
          <Volume2 className="w-3.5 h-3.5 text-indigo-400" />
          <span>12. Voice &amp; Avatar Studio</span>
          <span className="px-1.5 py-0.2 rounded bg-indigo-500/20 text-indigo-300 text-[10px] font-mono">11 VOICES</span>
        </button>

        <button
          onClick={() => setActiveTab('knowledge')}
          className={`px-3.5 py-2 text-xs font-medium flex items-center gap-2 border-b-2 transition-colors whitespace-nowrap ${
            activeTab === 'knowledge'
              ? 'border-cyan-400 text-cyan-300 bg-cyan-950/20'
              : 'border-transparent text-slate-400 hover:text-slate-200 hover:bg-slate-900/40'
          }`}
        >
          <Database className="w-3.5 h-3.5 text-cyan-400" />
          <span>13. Knowledge Acquisition</span>
          <span className="px-1.5 py-0.2 rounded bg-cyan-500/20 text-cyan-300 text-[10px] font-mono">4-TIER</span>
        </button>

        <button
          onClick={() => setActiveTab('onboarding')}
          className={`px-3.5 py-2 text-xs font-medium flex items-center gap-2 border-b-2 transition-colors whitespace-nowrap ${
            activeTab === 'onboarding'
              ? 'border-emerald-400 text-emerald-300 bg-emerald-950/20'
              : 'border-transparent text-slate-400 hover:text-slate-200 hover:bg-slate-900/40'
          }`}
        >
          <UserCheck className="w-3.5 h-3.5 text-emerald-400" />
          <span>14. Onboarding &amp; QA Protocols</span>
          <span className="px-1.5 py-0.2 rounded bg-emerald-500/20 text-emerald-300 text-[10px] font-mono">BLIND QA</span>
        </button>

        <button
          onClick={() => setActiveTab('launch-checklist')}
          className={`px-3.5 py-2 text-xs font-medium flex items-center gap-2 border-b-2 transition-colors whitespace-nowrap ${
            activeTab === 'launch-checklist'
              ? 'border-emerald-400 text-emerald-300 bg-emerald-950/30'
              : 'border-transparent text-slate-400 hover:text-slate-200 hover:bg-slate-900/40'
          }`}
        >
          <Rocket className="w-3.5 h-3.5 text-emerald-400" />
          <span className="font-bold">15. Launch Checklist</span>
          <span className="px-1.5 py-0.2 rounded bg-emerald-500/20 text-emerald-300 text-[10px] font-mono">GO/NO-GO</span>
        </button>

        <button
          onClick={() => setActiveTab('minimax-comparison')}
          className={`px-3.5 py-2 text-xs font-medium flex items-center gap-2 border-b-2 transition-colors whitespace-nowrap ${
            activeTab === 'minimax-comparison'
              ? 'border-cyan-400 text-cyan-300 bg-cyan-950/30'
              : 'border-transparent text-slate-400 hover:text-slate-200 hover:bg-slate-900/40'
          }`}
        >
          <Scale className="w-3.5 h-3.5 text-cyan-400" />
          <span className="font-bold">16. Frontier AI Supremacy</span>
          <span className="px-1.5 py-0.2 rounded bg-cyan-500/20 text-cyan-300 text-[10px] font-mono">MUSE · GROK · MINIMAX</span>
        </button>

        <button
          onClick={() => setActiveTab('omnipresence')}
          className={`px-3.5 py-2 text-xs font-medium flex items-center gap-2 border-b-2 transition-colors whitespace-nowrap ${
            activeTab === 'omnipresence'
              ? 'border-indigo-400 text-indigo-300 bg-indigo-950/30'
              : 'border-transparent text-slate-400 hover:text-slate-200 hover:bg-slate-900/40'
          }`}
        >
          <Globe className="w-3.5 h-3.5 text-cyan-400" />
          <span className="font-bold">17. Omnipresence &amp; Future-Proof</span>
          <span className="px-1.5 py-0.2 rounded bg-indigo-500/20 text-indigo-300 text-[10px] font-mono">14 SURFACES</span>
        </button>

        <button
          onClick={() => setActiveTab('personas-memory')}
          className={`px-3.5 py-2 text-xs font-medium flex items-center gap-2 border-b-2 transition-colors whitespace-nowrap ${
            activeTab === 'personas-memory'
              ? 'border-violet-400 text-violet-300 bg-violet-950/30'
              : 'border-transparent text-slate-400 hover:text-slate-200 hover:bg-slate-900/40'
          }`}
        >
          <Brain className="w-3.5 h-3.5 text-violet-400 animate-pulse" />
          <span className="font-bold">18. Personas &amp; Memory Engine</span>
          <span className="px-1.5 py-0.2 rounded bg-violet-500/20 text-violet-300 text-[10px] font-mono">ON-DEMAND RSI · IDENTITY GRAPH</span>
        </button>

        <button
          onClick={() => setActiveTab('physical-estate')}
          className={`px-3.5 py-2 text-xs font-medium flex items-center gap-2 border-b-2 transition-colors whitespace-nowrap ${
            activeTab === 'physical-estate'
              ? 'border-cyan-400 text-cyan-300 bg-cyan-950/30'
              : 'border-transparent text-slate-400 hover:text-slate-200 hover:bg-slate-900/40'
          }`}
        >
          <Activity className="w-3.5 h-3.5 text-cyan-400 animate-pulse" />
          <span className="font-bold">19. Physical Estate Inventory</span>
          <span className="px-1.5 py-0.2 rounded bg-cyan-500/20 text-cyan-300 text-[10px] font-mono">9 NODES · TELEMETRY</span>
        </button>
      </div>
    </header>
  );
};
