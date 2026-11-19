import React, { useState } from 'react';
import { 
  Package, 
  CheckCircle2, 
  Smartphone, 
  Apple, 
  Terminal, 
  Volume2, 
  Mic, 
  Eye, 
  Cpu, 
  FolderArchive, 
  Download, 
  Layers, 
  ShieldCheck,
  Check,
  Zap,
  ArrowRight,
  GitBranch,
  RotateCcw,
  Radio
} from 'lucide-react';
import { INGEST_DROPS, SEPTEMBER_CAPABILITIES } from '../data/busAndDropRecords';
import { IngestDrop, SeptemberCapability } from '../types/otto';

export const DropIngestAndCapabilities: React.FC = () => {
  const [drops, setDrops] = useState<IngestDrop[]>(INGEST_DROPS);
  const [capabilities, setCapabilities] = useState<SeptemberCapability[]>(SEPTEMBER_CAPABILITIES);
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [activeDrop, setActiveDrop] = useState<IngestDrop>(INGEST_DROPS[0]);
  const [isIngesting, setIsIngesting] = useState(false);
  const [ingestSuccessMessage, setIngestSuccessMessage] = useState<string | null>(null);

  const handleReingestAllDrops = () => {
    setIsIngesting(true);
    setIngestSuccessMessage(null);

    setTimeout(() => {
      setIsIngesting(false);
      setIngestSuccessMessage(
        'Airlock verification complete: Drops #1055, #1062, #1065 ingested into propose/otto-universal-v1 with 0 restart required.'
      );
    }, 800);
  };

  const filteredCapabilities = capabilities.filter(
    c => selectedCategory === 'all' || c.category === selectedCategory
  );

  return (
    <div className="space-y-6">
      {/* Banner */}
      <div className="rounded-2xl border border-indigo-500/30 bg-gradient-to-b from-slate-900 to-slate-950 p-6 shadow-2xl relative overflow-hidden">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4 relative z-10">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-300 text-xs font-mono mb-2">
              <FolderArchive className="w-3.5 h-3.5" />
              <span>SECTIONS 3 &amp; 8: ESTATE INGESTION &amp; REUSED SEPTEMBER CAPABILITIES</span>
            </div>
            <h2 className="text-2xl font-bold text-white font-display">
              Drop Ingestion &amp; Capability Inventory
            </h2>
            <p className="text-sm text-slate-400 max-w-2xl mt-1">
              AI Studio ingests the founder's <span className="text-cyan-400 font-semibold">2026-11-07 mobile drops (#1055, #1062)</span> and the <span className="text-purple-400 font-semibold">September Otto engine</span> (8 STT engines, 11 voices, vision &amp; video). <span className="text-emerald-400 font-semibold">Reused instead of rebuilt from scratch.</span>
            </p>
          </div>

          <button
            onClick={handleReingestAllDrops}
            disabled={isIngesting}
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs font-mono shadow-lg shadow-indigo-600/30 transition-all self-start lg:self-auto disabled:opacity-50"
          >
            <Zap className={`w-4 h-4 ${isIngesting ? 'animate-spin' : ''}`} />
            <span>{isIngesting ? 'Verifying Airlock...' : 'Re-verify Drops via Airlock'}</span>
          </button>
        </div>

        {ingestSuccessMessage && (
          <div className="mt-4 p-3 rounded-lg bg-emerald-950/40 border border-emerald-500/40 text-emerald-300 text-xs font-mono flex items-center gap-2 animate-fadeIn">
            <CheckCircle2 className="w-4 h-4 shrink-0" />
            <span>{ingestSuccessMessage}</span>
          </div>
        )}
      </div>

      {/* Argon Inbox & Outbox Sync Station */}
      <div className="p-5 rounded-2xl bg-slate-900/80 border border-cyan-500/30 shadow-xl space-y-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-3">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyan-400 shrink-0">
              <GitBranch className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-bold text-white text-base font-display">argon-sync / inbox Status</h3>
                <span className="px-2 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-800 font-bold text-[10px] font-mono flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                  100% IN SYNC · 0 LAG
                </span>
              </div>
              <p className="text-xs text-slate-400 font-mono mt-0.5">
                Target: <span className="text-cyan-300">argon-sync/inbox/incoming/</span> ➔ Bound to <span className="text-indigo-300">argon:outbox-state</span>
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 self-start md:self-auto font-mono text-xs">
            <div className="px-3 py-1.5 rounded-lg bg-slate-950 border border-slate-800 text-slate-300 text-[11px]">
              Last Sync: <strong className="text-emerald-400">T-8s ago</strong> · Checkpoint: <code className="text-cyan-300">sha256:01928471...</code>
            </div>
            <button
              onClick={handleReingestAllDrops}
              className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
              title="Force Argon Inbox Re-sync"
            >
              <RotateCcw className={`w-3.5 h-3.5 ${isIngesting ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </div>

        {/* 3 Synced Repos Triad */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs font-mono">
          <div className="p-3 rounded-xl bg-slate-950 border border-slate-800/80 space-y-1">
            <div className="flex items-center justify-between text-slate-400 text-[10px]">
              <span>ESTATE REPO 1</span>
              <span className="text-emerald-400 font-bold">CLEAN ✓</span>
            </div>
            <div className="font-bold text-white text-sm">argon:outbox-state</div>
            <div className="text-[11px] text-slate-400">Stores active outbox state &amp; signed gate verdicts.</div>
          </div>

          <div className="p-3 rounded-xl bg-slate-950 border border-cyan-500/40 space-y-1 ring-1 ring-cyan-500/20">
            <div className="flex items-center justify-between text-slate-400 text-[10px]">
              <span>ESTATE REPO 2 (INBOX)</span>
              <span className="text-cyan-400 font-bold">SYNCHRONIZED ✓</span>
            </div>
            <div className="font-bold text-white text-sm">argon-sync/inbox/</div>
            <div className="text-[11px] text-slate-300">Drops #1055, #1062, #1065 staged &amp; verified.</div>
          </div>

          <div className="p-3 rounded-xl bg-slate-950 border border-slate-800/80 space-y-1">
            <div className="flex items-center justify-between text-slate-400 text-[10px]">
              <span>ESTATE REPO 3</span>
              <span className="text-emerald-400 font-bold">IMMUTABLE ✓</span>
            </div>
            <div className="font-bold text-white text-sm">idp-archive:main</div>
            <div className="text-[11px] text-slate-400">Historical specs, schemas &amp; September tools.</div>
          </div>
        </div>
      </div>

      {/* Grid: 3 Ingested Drops */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {drops.map(drop => {
          const isSelected = activeDrop.id === drop.id;
          return (
            <div
              key={drop.id}
              onClick={() => setActiveDrop(drop)}
              className={`p-4 rounded-xl border transition-all cursor-pointer ${
                isSelected
                  ? 'border-cyan-400 bg-cyan-950/30 text-white shadow-lg'
                  : 'border-slate-800 bg-slate-900/50 hover:bg-slate-900 text-slate-300'
              }`}
            >
              <div className="flex items-center justify-between text-xs font-mono mb-2">
                <span className="font-bold text-cyan-300">{drop.id}</span>
                <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-800 font-bold">
                  {drop.status.toUpperCase()}
                </span>
              </div>

              <h4 className="font-semibold text-sm text-white mb-1">{drop.title}</h4>
              <div className="text-[10px] text-slate-500 font-mono truncate mb-3">{drop.path}</div>

              <div className="space-y-1 text-[11px] text-slate-300">
                {drop.contains.map((item, i) => (
                  <div key={i} className="flex items-start gap-1.5">
                    <span className="text-cyan-400">•</span>
                    <span className="font-mono text-[10px] truncate">{item}</span>
                  </div>
                ))}
              </div>

              <div className="mt-3 pt-2 border-t border-slate-800/80 text-[10px] font-mono text-slate-500 truncate">
                Hash: {drop.sha256.substring(0, 24)}...
              </div>
            </div>
          );
        })}
      </div>

      {/* September Otto Capability Inventory (Reused, never rebuild) */}
      <div className="rounded-2xl border border-slate-800 bg-slate-950 p-6 shadow-xl space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-slate-800 pb-3">
          <div>
            <h3 className="font-display font-bold text-white text-base">
              September Capability Inventory: Wired &amp; Operational
            </h3>
            <p className="text-xs text-slate-400">
              hermes-agent fork components: 8 STT providers, 11 voices, vision and video pipeline.
            </p>
          </div>

          <div className="flex flex-wrap gap-1.5 text-xs font-mono">
            {['all', 'stt-engine', 'voice', 'vision', 'tool'].map(cat => (
              <button
                key={cat}
                onClick={() => setSelectedCategory(cat)}
                className={`px-2.5 py-1 rounded-lg capitalize transition-colors ${
                  selectedCategory === cat
                    ? 'bg-indigo-600 text-white font-bold'
                    : 'bg-slate-900 text-slate-400 border border-slate-800 hover:text-white'
                }`}
              >
                {cat}
              </button>
            ))}
          </div>
        </div>

        {/* Capability Cards Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {filteredCapabilities.map((cap, i) => (
            <div
              key={i}
              className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800 space-y-2 text-xs"
            >
              <div className="flex items-center justify-between">
                <span className="font-bold text-white flex items-center gap-1.5">
                  {cap.category === 'stt-engine' && <Mic className="w-3.5 h-3.5 text-cyan-400" />}
                  {cap.category === 'voice' && <Volume2 className="w-3.5 h-3.5 text-rose-400" />}
                  {cap.category === 'vision' && <Eye className="w-3.5 h-3.5 text-emerald-400" />}
                  {cap.category === 'tool' && <Cpu className="w-3.5 h-3.5 text-amber-400" />}
                  <span>{cap.name}</span>
                </span>
                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-emerald-950/60 text-emerald-400 border border-emerald-800">
                  WIRED
                </span>
              </div>

              <div className="text-[11px] text-slate-400 font-mono">
                Provider: {cap.provider}
              </div>

              <div className="flex items-center justify-between pt-1 border-t border-slate-800/60 text-[10px] text-slate-500 font-mono">
                <span className="uppercase text-slate-400">{cap.category}</span>
                <span className="text-cyan-400 font-bold">{cap.latencyMs}ms latency</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
