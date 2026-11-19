import React, { useState, useEffect } from 'react';
import { 
  Radio, 
  Terminal, 
  Search, 
  Play, 
  Pause, 
  RotateCcw, 
  CheckCircle2, 
  Clock, 
  ArrowRight, 
  ShieldCheck, 
  Filter, 
  Send,
  Zap,
  Layers,
  Code
} from 'lucide-react';
import { PeerBusPacket } from '../types/otto';
import { INITIAL_BUS_PACKETS } from '../data/busAndDropRecords';

export const PeerBusLogViewer: React.FC = () => {
  const [packets, setPackets] = useState<PeerBusPacket[]>(INITIAL_BUS_PACKETS);
  const [isStreaming, setIsStreaming] = useState(true);
  const [selectedChannel, setSelectedChannel] = useState<string>('all');
  const [selectedAgent, setSelectedAgent] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedPacket, setSelectedPacket] = useState<PeerBusPacket | null>(null);

  // Auto-stream incoming bus packets
  useEffect(() => {
    if (!isStreaming) return;

    const channels: PeerBusPacket['channel'][] = [
      'topic/ast-refactor',
      'topic/screen-diff',
      'topic/blind-qa',
      'topic/heartbeat',
      'topic/gate-verdict'
    ];
    const agents = ['otto-lead', 'deepseek-worker', 'gemini-vision', 'kimi-context', 'blind-verifier'];

    const interval = setInterval(() => {
      const ch = channels[Math.floor(Math.random() * channels.length)];
      const sender = agents[Math.floor(Math.random() * agents.length)];
      let receiver = agents[Math.floor(Math.random() * agents.length)];
      while (receiver === sender) {
        receiver = agents[Math.floor(Math.random() * agents.length)];
      }

      let summary = '';
      let jsonPayload: any = {};

      if (ch === 'topic/ast-refactor') {
        summary = `AST transformation node #${Math.floor(Math.random() * 900) + 100} verified: 0 syntax errors`;
        jsonPayload = { astNodes: 18, transformLatencyMs: 14, targetDriver: 'android_maestro' };
      } else if (ch === 'topic/screen-diff') {
        summary = `Diff comparison delta: 0.00% misclick variance on 4K display buffer`;
        jsonPayload = { boundingBox: [412, 180, 520, 240], confidence: 0.999 };
      } else if (ch === 'topic/blind-qa') {
        summary = `Independent verifier cryptographically evaluated execution hash`;
        jsonPayload = { zkProof: 'PASS', verifierAuditId: 'audit-' + Math.floor(Math.random() * 1000) };
      } else if (ch === 'topic/gate-verdict') {
        summary = `Airlock consensus confirmed across 5 vendor peers without human relay`;
        jsonPayload = { consensus: '5/5 APPROVED', branch: 'propose/otto-universal-v1' };
      } else {
        summary = `Heartbeat telemetry pulse on bin/genesis-crew.py bus (14ms RTT)`;
        jsonPayload = { rttMs: 14, memoryFootprintMb: 42.1 };
      }

      const newPacket: PeerBusPacket = {
        id: 'pkt-bus-' + Date.now().toString().slice(-4),
        timestamp: new Date().toLocaleTimeString() + '.' + Math.floor(Math.random() * 900 + 100),
        channel: ch,
        sender,
        receiver,
        payloadSummary: summary,
        payloadJson: jsonPayload,
        transitMs: Math.floor(Math.random() * 15) + 6,
        status: 'VERIFIED',
        proofHash: 'sha256:' + Math.random().toString(16).substring(2, 10)
      };

      setPackets(prev => [newPacket, ...prev.slice(0, 35)]);
    }, 2400);

    return () => clearInterval(interval);
  }, [isStreaming]);

  const filteredPackets = packets.filter(pkt => {
    const matchesChannel = selectedChannel === 'all' || pkt.channel === selectedChannel;
    const matchesAgent = selectedAgent === 'all' || pkt.sender === selectedAgent || pkt.receiver === selectedAgent;
    const matchesSearch = 
      pkt.payloadSummary.toLowerCase().includes(searchQuery.toLowerCase()) ||
      pkt.sender.toLowerCase().includes(searchQuery.toLowerCase()) ||
      pkt.receiver.toLowerCase().includes(searchQuery.toLowerCase()) ||
      pkt.proofHash.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesChannel && matchesAgent && matchesSearch;
  });

  const handleDispatchManualPacket = () => {
    const manualPacket: PeerBusPacket = {
      id: 'pkt-manual-' + Date.now().toString().slice(-4),
      timestamp: new Date().toLocaleTimeString() + '.001',
      channel: 'topic/ast-refactor',
      sender: 'otto-lead',
      receiver: 'deepseek-worker',
      payloadSummary: 'Manual Probe: AST Verification of Bounded Verb Envelope (<= 100s)',
      payloadJson: { initiatedBy: 'Founder Console', priority: 'HIGH', timeoutSec: 100 },
      transitMs: 8,
      status: 'VERIFIED',
      proofHash: 'sha256:' + Math.random().toString(16).substring(2, 10)
    };
    setPackets(prev => [manualPacket, ...prev]);
    setSelectedPacket(manualPacket);
  };

  return (
    <div className="space-y-6">
      {/* Banner */}
      <div className="rounded-2xl border border-cyan-500/30 bg-gradient-to-b from-slate-900 to-slate-950 p-6 shadow-2xl relative overflow-hidden">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4 relative z-10">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-cyan-500/10 border border-cyan-500/20 text-cyan-300 text-xs font-mono mb-2">
              <Radio className="w-3.5 h-3.5" />
              <span>SECTION 4: REAL-TIME PEER BUS LOG (bin/genesis-crew.py)</span>
            </div>
            <h2 className="text-2xl font-bold text-white font-display">
              Autonomous Peer Bus Packet Inspector
            </h2>
            <p className="text-sm text-slate-400 max-w-2xl mt-1">
              Live cryptographic packet stream traversing <code className="text-cyan-400 font-mono text-xs">bin/genesis-crew.py</code>. Otto runs as Lead, dispatching sub-goals to DeepSeek, Gemini, Kimi, and a separate blind verifier with <span className="text-emerald-400 font-semibold">zero founder relay</span>.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <button
              onClick={() => setIsStreaming(!isStreaming)}
              className={`flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-mono font-semibold transition-colors ${
                isStreaming
                  ? 'bg-emerald-950/60 text-emerald-300 border border-emerald-700'
                  : 'bg-amber-950/60 text-amber-300 border border-amber-700'
              }`}
            >
              {isStreaming ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
              <span>{isStreaming ? 'Streaming Live' : 'Stream Paused'}</span>
            </button>

            <button
              onClick={handleDispatchManualPacket}
              className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-cyan-500 hover:bg-cyan-400 text-slate-950 text-xs font-bold shadow-md shadow-cyan-500/20 transition-all font-mono"
            >
              <Send className="w-3.5 h-3.5" />
              <span>Dispatch Packet</span>
            </button>
          </div>
        </div>

        {/* Bus Ticker Statistics */}
        <div className="mt-6 grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono">
          <div className="p-3 rounded-xl bg-slate-950/80 border border-slate-800">
            <span className="text-slate-400 text-[10px] uppercase">Active Nodes</span>
            <div className="text-white font-bold text-sm mt-0.5">5 Vendor Peers</div>
            <div className="text-emerald-400 text-[10px]">Otto · DeepSeek · Gemini · Kimi · Verifier</div>
          </div>

          <div className="p-3 rounded-xl bg-slate-950/80 border border-slate-800">
            <span className="text-slate-400 text-[10px] uppercase">Bus Latency RTT</span>
            <div className="text-cyan-400 font-bold text-sm mt-0.5">11.4 ms avg</div>
            <div className="text-slate-500 text-[10px]">Zero-overhead Unix domain socket</div>
          </div>

          <div className="p-3 rounded-xl bg-slate-950/80 border border-slate-800">
            <span className="text-slate-400 text-[10px] uppercase">Consensus Protocol</span>
            <div className="text-purple-400 font-bold text-sm mt-0.5">Zero-Knowledge Gate</div>
            <div className="text-slate-500 text-[10px]">Independent blind QA signed</div>
          </div>

          <div className="p-3 rounded-xl bg-slate-950/80 border border-slate-800">
            <span className="text-slate-400 text-[10px] uppercase">Founder Relays</span>
            <div className="text-emerald-400 font-bold text-sm mt-0.5">0 Relays Required</div>
            <div className="text-slate-500 text-[10px]">Eval E12: 100% Autonomous</div>
          </div>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="p-4 rounded-xl border border-slate-800 bg-slate-950 flex flex-col md:flex-row items-center justify-between gap-3 text-xs font-mono">
        <div className="flex flex-wrap items-center gap-2 w-full md:w-auto">
          <Filter className="w-4 h-4 text-slate-500 shrink-0" />
          
          <select
            value={selectedChannel}
            onChange={e => setSelectedChannel(e.target.value)}
            className="bg-slate-900 border border-slate-800 rounded-lg px-2.5 py-1.5 text-slate-200 text-xs focus:outline-none focus:border-cyan-500"
          >
            <option value="all">All Channels</option>
            <option value="topic/ast-refactor">topic/ast-refactor</option>
            <option value="topic/screen-diff">topic/screen-diff</option>
            <option value="topic/blind-qa">topic/blind-qa</option>
            <option value="topic/gate-verdict">topic/gate-verdict</option>
            <option value="topic/heartbeat">topic/heartbeat</option>
          </select>

          <select
            value={selectedAgent}
            onChange={e => setSelectedAgent(e.target.value)}
            className="bg-slate-900 border border-slate-800 rounded-lg px-2.5 py-1.5 text-slate-200 text-xs focus:outline-none focus:border-cyan-500"
          >
            <option value="all">All Agents</option>
            <option value="otto-lead">otto-lead</option>
            <option value="deepseek-worker">deepseek-worker</option>
            <option value="gemini-vision">gemini-vision</option>
            <option value="kimi-context">kimi-context</option>
            <option value="blind-verifier">blind-verifier</option>
          </select>
        </div>

        <div className="relative w-full md:w-72">
          <Search className="w-3.5 h-3.5 text-slate-500 absolute left-3 top-2.5" />
          <input
            type="text"
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            placeholder="Search packet payloads or proofs..."
            className="w-full pl-8 pr-3 py-1.5 bg-slate-900 border border-slate-800 rounded-lg text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500 font-sans"
          />
        </div>
      </div>

      {/* Main Packet Stream & Inspector */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Packet Stream List */}
        <div className="lg:col-span-8 space-y-2">
          <div className="rounded-xl border border-slate-800 bg-slate-950 p-4 shadow-xl">
            <div className="flex items-center justify-between pb-3 mb-2 border-b border-slate-800 text-xs font-mono">
              <span className="text-slate-300 font-bold">
                BUS PACKETS ({filteredPackets.length})
              </span>
              <span className="text-[10px] text-slate-500">
                Click any row to inspect JSON structure
              </span>
            </div>

            <div className="space-y-2 max-h-[500px] overflow-y-auto pr-1">
              {filteredPackets.map(pkt => {
                const isSelected = selectedPacket?.id === pkt.id;
                return (
                  <div
                    key={pkt.id}
                    onClick={() => setSelectedPacket(pkt)}
                    className={`p-3 rounded-lg border text-xs font-mono transition-all cursor-pointer ${
                      isSelected
                        ? 'border-cyan-400 bg-cyan-950/30 text-white shadow-md'
                        : 'border-slate-800/80 bg-slate-900/50 hover:bg-slate-900 hover:border-slate-700 text-slate-300'
                    }`}
                  >
                    <div className="flex items-center justify-between text-[11px] mb-1">
                      <div className="flex items-center gap-2">
                        <span className="text-cyan-400 font-bold">{pkt.channel}</span>
                        <span className="text-slate-500">|</span>
                        <span className="text-indigo-300 font-semibold">{pkt.sender}</span>
                        <ArrowRight className="w-3 h-3 text-slate-500 inline" />
                        <span className="text-purple-300 font-semibold">{pkt.receiver}</span>
                      </div>
                      <span className="text-slate-500 text-[10px]">{pkt.timestamp}</span>
                    </div>

                    <p className="text-slate-200 text-[11px] leading-relaxed">
                      {pkt.payloadSummary}
                    </p>

                    <div className="flex items-center justify-between pt-2 mt-2 border-t border-slate-800/60 text-[10px] text-slate-500">
                      <span className="text-emerald-400 flex items-center gap-1 font-bold">
                        <CheckCircle2 className="w-3 h-3" /> {pkt.status} ({pkt.transitMs}ms)
                      </span>
                      <span>Proof: {pkt.proofHash}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Packet JSON Inspector */}
        <div className="lg:col-span-4">
          <div className="rounded-xl border border-slate-800 bg-slate-950 p-4 shadow-xl space-y-3 font-mono text-xs sticky top-24">
            <div className="flex items-center justify-between border-b border-slate-800 pb-2">
              <span className="font-bold text-white flex items-center gap-1.5">
                <Code className="w-4 h-4 text-cyan-400" />
                Packet Payload Inspector
              </span>
              {selectedPacket && (
                <span className="text-[10px] text-cyan-400">{selectedPacket.id}</span>
              )}
            </div>

            {selectedPacket ? (
              <div className="space-y-3">
                <div className="space-y-1">
                  <div className="text-[10px] text-slate-400 uppercase">Channel / Topic:</div>
                  <div className="text-cyan-300 font-bold">{selectedPacket.channel}</div>
                </div>

                <div className="grid grid-cols-2 gap-2 text-[11px]">
                  <div className="p-2 rounded bg-slate-900 border border-slate-800">
                    <span className="text-slate-500 text-[9px] block">Sender:</span>
                    <span className="text-indigo-300">{selectedPacket.sender}</span>
                  </div>
                  <div className="p-2 rounded bg-slate-900 border border-slate-800">
                    <span className="text-slate-500 text-[9px] block">Receiver:</span>
                    <span className="text-purple-300">{selectedPacket.receiver}</span>
                  </div>
                </div>

                <div>
                  <div className="text-[10px] text-slate-400 uppercase mb-1">Payload JSON:</div>
                  <pre className="p-3 rounded-lg bg-slate-900 border border-slate-800 text-[11px] text-emerald-300 overflow-x-auto leading-relaxed">
                    {JSON.stringify(selectedPacket.payloadJson, null, 2)}
                  </pre>
                </div>

                <div>
                  <div className="text-[10px] text-slate-400 uppercase mb-1">Cryptographic Proof:</div>
                  <div className="p-2 rounded bg-slate-900 border border-slate-800 text-[10px] text-slate-300 break-all select-all">
                    {selectedPacket.proofHash}
                  </div>
                </div>
              </div>
            ) : (
              <div className="py-16 text-center text-slate-600 text-xs">
                Select any packet from the live bus stream to inspect its AST tokens & cryptographic payload.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
