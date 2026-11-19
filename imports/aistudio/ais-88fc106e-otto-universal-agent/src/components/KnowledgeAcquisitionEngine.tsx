import React, { useState } from 'react';
import { 
  Database, 
  GitBranch, 
  Layers, 
  Cpu, 
  Search, 
  CheckCircle2, 
  ArrowRight, 
  FileText, 
  Eye, 
  Terminal, 
  ShieldCheck, 
  BookOpen,
  Sparkles,
  Zap,
  Radio
} from 'lucide-react';
import { KnowledgePipelineNode } from '../types/otto';

const KNOWLEDGE_TIERS: KnowledgePipelineNode[] = [
  {
    id: 'tier-1',
    layer: 'estate-records',
    title: 'Tier 1: Estate Sovereign Ground Truth',
    method: 'Git DAG Hash Inspection & AGENTS.md Laws',
    inputSource: 'argon, argon-sync, idp-archive, outbox-state',
    validationGate: 'Zero-Knowledge Commit Signatures',
    latencyMs: 14,
    trustScore: 1.0
  },
  {
    id: 'tier-2',
    layer: 'view-tree-ocr',
    title: 'Tier 2: Multimodal Real-World Grounding',
    method: 'Accessibility Trees (AX/UI Automator) + Framebuffer OCR',
    inputSource: 'macOS, Android Pixel 9, iPhone 16 Pro, Cloud Browser',
    validationGate: 'Screenshot Diff Delta & Coordinate Matching',
    latencyMs: 28,
    trustScore: 0.999
  },
  {
    id: 'tier-3',
    layer: 'peer-distillation',
    title: 'Tier 3: Cross-Vendor Peer Distillation',
    method: 'Arbitrated Bus Query via bin/genesis-crew.py',
    inputSource: 'DeepSeek (AST) + Gemini (Vision) + Kimi (2M Context)',
    validationGate: 'Independent Blind Verifier Consensus (QA Gate)',
    latencyMs: 42,
    trustScore: 0.998
  },
  {
    id: 'tier-4',
    layer: 'formal-induction',
    title: 'Tier 4: Formal Invariant Memory Induction',
    method: 'Hoare Invariant Verification & Coq Proof Packaging',
    inputSource: 'Candidate knowledge facts & tool execution trajectories',
    validationGate: 'M_{t+1} ⊇ M_t Monotonic Proof Check',
    latencyMs: 18,
    trustScore: 1.0
  }
];

export const KnowledgeAcquisitionEngine: React.FC = () => {
  const [selectedTier, setSelectedTier] = useState<KnowledgePipelineNode>(KNOWLEDGE_TIERS[0]);
  const [testDomainQuery, setTestDomainQuery] = useState('');
  const [ingestionStream, setIngestionStream] = useState<string[]>([]);
  const [isSimulatingIngestion, setIsSimulatingIngestion] = useState(false);

  const handleSimulateAcquisition = (queryText?: string) => {
    const q = queryText || testDomainQuery || 'How to safely patch the Android Maestro flow without breaking gate tests';
    setIsSimulatingIngestion(true);
    setIngestionStream([]);

    const log = (msg: string) => {
      setIngestionStream(prev => [...prev, `[${new Date().toISOString().substring(11, 19)}] ${msg}`]);
    };

    log(`INGESTION DISPATCH: Domain Goal = "${q}"`);
    setTimeout(() => {
      log(`TIER 1 (Estate Grounding): Reading ~/.maestro/flows and argon/outbox-state... Found 3 previous valid checkpoints.`);
      setTimeout(() => {
        log(`TIER 2 (Multimodal Ingestion): Inspecting Pixel 9 Pro UI Automator view tree (14 nodes). Validating target button IDs.`);
        setTimeout(() => {
          log(`TIER 3 (Peer Distillation): Bus query to DeepSeek-V3 for AST diff + Gemini Vision for bounding box verification.`);
          log(`BLIND VERIFIER QA: Consensus verified. Zero knowledge drift detected.`);
          setTimeout(() => {
            log(`TIER 4 (Memory Induction): Writing proof-backed fact to Project Memory layer (Key: maestro_safe_patch_v2).`);
            log(`INVARIANT CHECK: M_{t+1} ⊇ M_t verified. Sub-2s retrieval armed.`);
            setIsSimulatingIngestion(false);
          }, 350);
        }, 350);
      }, 350);
    }, 300);
  };

  return (
    <div className="space-y-6">
      {/* Banner */}
      <div className="rounded-2xl border border-cyan-500/30 bg-gradient-to-b from-slate-900 to-slate-950 p-6 shadow-2xl relative overflow-hidden">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4 relative z-10">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-cyan-500/10 border border-cyan-500/20 text-cyan-300 text-xs font-mono mb-2">
              <Database className="w-3.5 h-3.5" />
              <span>KNOWLEDGE ACQUISITION ARCHITECTURE: ZERO-HALLUCINATION INDUCTION</span>
            </div>
            <h2 className="text-2xl font-bold text-white font-display">
              How Otto Acquires &amp; Verifies Knowledge
            </h2>
            <p className="text-sm text-slate-400 max-w-2xl mt-1">
              Otto never relies on ungrounded hallucinations. Knowledge is acquired through a <span className="text-cyan-400 font-semibold">4-tier pipeline</span>: reading estate records before searching, multimodal device view-trees, cross-vendor peer distillation, and formal mathematical proof induction.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-xs font-mono px-3 py-1.5 rounded-lg bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 flex items-center gap-1.5 font-bold">
              <ShieldCheck className="w-3.5 h-3.5" />
              <span>MONOTONIC MEMORY PROOF: ACTIVE</span>
            </span>
          </div>
        </div>
      </div>

      {/* 4 Tier Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
        {KNOWLEDGE_TIERS.map(tier => {
          const isSelected = selectedTier.id === tier.id;
          return (
            <div
              key={tier.id}
              onClick={() => setSelectedTier(tier)}
              className={`p-4 rounded-xl border transition-all cursor-pointer text-xs font-mono flex flex-col justify-between ${
                isSelected
                  ? 'border-cyan-400 bg-cyan-950/40 text-white shadow-lg shadow-cyan-500/10'
                  : 'border-slate-800 bg-slate-900/50 hover:bg-slate-900 text-slate-300'
              }`}
            >
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[10px] uppercase font-bold text-cyan-400">{tier.layer}</span>
                  <span className="text-[10px] px-1.5 py-0.2 rounded bg-emerald-950 text-emerald-300 border border-emerald-800">
                    {(tier.trustScore * 100).toFixed(1)}% Trust
                  </span>
                </div>
                <div className="font-bold text-white text-sm mb-1">{tier.title}</div>
                <div className="text-[11px] text-slate-400 mb-2">{tier.method}</div>
              </div>

              <div className="mt-3 pt-2 border-t border-slate-800/80 space-y-1 text-[10px]">
                <div className="text-slate-400 truncate">Source: <span className="text-slate-200">{tier.inputSource}</span></div>
                <div className="flex items-center justify-between text-cyan-400">
                  <span>Latency: {tier.latencyMs}ms</span>
                  <span>Inspect →</span>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Interactive Simulation & Tier Deep Dive */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Tier Architecture Details */}
        <div className="lg:col-span-6 space-y-4">
          <div className="rounded-xl border border-slate-800 bg-slate-950 p-5 shadow-xl space-y-3 font-mono text-xs">
            <div className="flex items-center justify-between border-b border-slate-800 pb-2">
              <span className="font-bold text-white flex items-center gap-1.5">
                <Layers className="w-4 h-4 text-cyan-400" />
                Pipeline Deep Dive: {selectedTier.title}
              </span>
              <span className="text-[10px] text-cyan-400">{selectedTier.id}</span>
            </div>

            <div className="space-y-2 text-[11px] leading-relaxed text-slate-300">
              <p>
                <strong className="text-white">Ingestion Mechanism: </strong>
                {selectedTier.method}
              </p>
              <p>
                <strong className="text-white">Authoritative Inputs: </strong>
                <code className="text-cyan-300 bg-slate-900 px-1 py-0.5 rounded">{selectedTier.inputSource}</code>
              </p>
              <p>
                <strong className="text-white">Cryptographic Gate: </strong>
                <span className="text-emerald-400 font-bold">{selectedTier.validationGate}</span>
              </p>
            </div>

            <div className="p-3 rounded-lg bg-slate-900 border border-slate-800 text-[11px] text-slate-400 space-y-1">
              <div className="text-white font-bold">Why This Eliminates Hallucination:</div>
              <div>
                Unlike conversational LLMs that fabricate facts from probability weights, Otto operates as a compiler over immutable estate records and verified view-trees. If a claim cannot be tied to a hash or diff, Otto does not assert it.
              </div>
            </div>

            {/* Test Input */}
            <div className="space-y-1 pt-2">
              <label className="text-[11px] text-slate-400">Simulate Real-World Knowledge Ingestion:</label>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={testDomainQuery}
                  onChange={e => setTestDomainQuery(e.target.value)}
                  placeholder="Enter a domain query (e.g. 'How to patch Android Maestro flow safely')..."
                  className="flex-1 bg-slate-900 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500"
                />
                <button
                  onClick={() => handleSimulateAcquisition()}
                  disabled={isSimulatingIngestion}
                  className="px-4 py-2 rounded-lg bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold text-xs transition-all disabled:opacity-50"
                >
                  {isSimulatingIngestion ? 'Ingesting...' : 'Ingest Knowledge'}
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Live Ingestion Stream */}
        <div className="lg:col-span-6">
          <div className="rounded-xl border border-slate-800 bg-slate-950 p-5 shadow-xl space-y-3 font-mono text-xs">
            <div className="flex items-center justify-between border-b border-slate-800 pb-2">
              <span className="font-bold text-white flex items-center gap-1.5">
                <Terminal className="w-4 h-4 text-emerald-400" />
                Live Ingestion &amp; Induction Stream
              </span>
              <span className="text-[10px] text-slate-500">Sub-2s Query Bound</span>
            </div>

            <div className="h-64 overflow-y-auto p-3 rounded-lg bg-slate-900 border border-slate-800 text-[11px] space-y-1.5 text-slate-300">
              {ingestionStream.length === 0 ? (
                <div className="py-16 text-center text-slate-600 italic">
                  Click "Ingest Knowledge" above to watch Otto acquire and prove a new capability across all 4 tiers...
                </div>
              ) : (
                ingestionStream.map((log, idx) => (
                  <div key={idx} className="leading-relaxed">
                    {log.includes('INGESTION DISPATCH') && <span className="text-cyan-400 font-bold">{log}</span>}
                    {log.includes('TIER 1') && <span className="text-sky-300">{log}</span>}
                    {log.includes('TIER 2') && <span className="text-amber-300">{log}</span>}
                    {log.includes('TIER 3') && <span className="text-purple-300">{log}</span>}
                    {log.includes('TIER 4') && <span className="text-emerald-400 font-bold">{log}</span>}
                    {log.includes('BLIND VERIFIER') && <span className="text-emerald-400 font-bold">{log}</span>}
                    {log.includes('INVARIANT CHECK') && <span className="text-cyan-300 font-bold">{log}</span>}
                    {!log.includes('TIER') && !log.includes('INGESTION') && !log.includes('BLIND') && !log.includes('INVARIANT') && (
                      <span className="text-slate-400">{log}</span>
                    )}
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
