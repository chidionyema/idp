import React, { useState, useEffect } from 'react';
import { EstateMotion } from '../types/estate';
import { Send, Terminal, CheckCircle2, AlertTriangle, RefreshCw, Radio, Globe, Shield, ArrowUpRight } from 'lucide-react';

interface AgentOrchestratorProps {
  motions: EstateMotion[];
  onReceiptLogged: (artifactTitle: string, checksum: string) => void;
}

interface AgentEndpoint {
  id: string;
  name: string;
  type: 'n8n' | 'Python' | 'CrewAI' | 'Telegram' | 'REST';
  url: string;
  status: 'ONLINE' | 'STANDBY' | 'ERROR';
}

const DEFAULT_ENDPOINTS: AgentEndpoint[] = [
  { id: 'EP-1', name: 'n8n Sovereign Workflow Engine', type: 'n8n', url: 'https://webhook.site/placeholder-n8n', status: 'STANDBY' },
  { id: 'EP-2', name: 'CrewAI Multi-Agent Coordinator', type: 'CrewAI', url: 'http://localhost:8000/api/motion', status: 'STANDBY' },
  { id: 'EP-3', name: 'Python Autonomous Worker Daemon', type: 'Python', url: 'http://localhost:5000/dispatch', status: 'STANDBY' },
  { id: 'EP-4', name: 'Telegram Founder Alert Bot', type: 'Telegram', url: 'https://api.telegram.org/bot-placeholder', status: 'STANDBY' },
];

export const AgentOrchestrator: React.FC<AgentOrchestratorProps> = ({
  motions,
  onReceiptLogged,
}) => {
  const [endpoints, setEndpoints] = useState<AgentEndpoint[]>(DEFAULT_ENDPOINTS);
  const [selectedEndpointId, setSelectedEndpointId] = useState<string>(DEFAULT_ENDPOINTS[0].id);
  const [selectedMotionId, setSelectedMotionId] = useState<string>(motions[0]?.id || '');
  const [customUrl, setCustomUrl] = useState('');
  const [isDispatching, setIsDispatching] = useState(false);
  const [dispatchLog, setDispatchLog] = useState<any | null>(null);

  // Inbound receipts state
  const [inboundReceipts, setInboundReceipts] = useState<any[]>([]);
  const [isRefreshingReceipts, setIsRefreshingReceipts] = useState(false);

  // Add new endpoint state
  const [newEpName, setNewEpName] = useState('');
  const [newEpType, setNewEpType] = useState<AgentEndpoint['type']>('n8n');
  const [newEpUrl, setNewEpUrl] = useState('');
  const [isAddOpen, setIsAddOpen] = useState(false);

  const fetchReceipts = async () => {
    setIsRefreshingReceipts(true);
    try {
      const res = await fetch('/api/agent-receipts');
      const data = await res.json();
      if (data.receipts) {
        setInboundReceipts(data.receipts);
      }
    } catch {
      // offline fallback
    } finally {
      setIsRefreshingReceipts(false);
    }
  };

  useEffect(() => {
    fetchReceipts();
    const interval = setInterval(fetchReceipts, 10000);
    return () => clearInterval(interval);
  }, []);

  const handleDispatch = async () => {
    const selectedEp = endpoints.find((ep) => ep.id === selectedEndpointId);
    const targetUrl = customUrl || selectedEp?.url;
    const motion = motions.find((m) => m.id === selectedMotionId);

    if (!targetUrl || !motion) return;
    setIsDispatching(true);
    setDispatchLog(null);

    try {
      const res = await fetch('/api/dispatch-agent', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          targetUrl,
          motion,
        }),
      });
      const data = await res.json();
      setDispatchLog({
        targetUrl,
        timestamp: new Date().toLocaleTimeString(),
        ...data,
      });

      // Update endpoint status
      setEndpoints((prev) =>
        prev.map((ep) =>
          ep.id === selectedEndpointId
            ? { ...ep, status: data.success ? 'ONLINE' : 'ERROR' }
            : ep
        )
      );
    } catch (err: any) {
      setDispatchLog({
        targetUrl,
        timestamp: new Date().toLocaleTimeString(),
        success: false,
        error: err.message,
      });
    } finally {
      setIsDispatching(false);
    }
  };

  const handleSimulateInboundReceipt = async () => {
    const randomHash = `sha256:${Math.random().toString(16).substring(2, 10)}${Date.now().toString(16)}`;
    const artifactName = `Agent Deliverable: ${motions.find((m) => m.id === selectedMotionId)?.title || 'Algorithmic Module'}`;

    try {
      await fetch('/api/agent-receipt', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          agentId: endpoints.find((ep) => ep.id === selectedEndpointId)?.name || 'CrewAI-Worker-01',
          motionId: selectedMotionId,
          artifactTitle: artifactName,
          checksum: randomHash,
          status: 'DELIVERED',
          payload: {
            outputUri: '/vault/deliverables/generated-output.json',
            executionTimeSec: 4.8,
            status: 'CONVERGED',
          },
        }),
      });
      await fetchReceipts();
      onReceiptLogged(artifactName, randomHash);
    } catch {
      // offline fallback
    }
  };

  const handleAddEndpoint = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newEpName.trim() || !newEpUrl.trim()) return;

    const newEp: AgentEndpoint = {
      id: `EP-${Date.now()}`,
      name: newEpName,
      type: newEpType,
      url: newEpUrl,
      status: 'STANDBY',
    };

    setEndpoints([...endpoints, newEp]);
    setSelectedEndpointId(newEp.id);
    setNewEpName('');
    setNewEpUrl('');
    setIsAddOpen(false);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-neutral-900 border border-neutral-800 rounded-xl p-5">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2 text-xs font-mono uppercase tracking-wider text-amber-400">
              <Radio className="w-4 h-4 text-amber-400" />
              <span>Real Agent Orchestrator &amp; Dispatcher</span>
              <span className="text-neutral-600">/</span>
              <span>Closed-Loop Webhook Execution</span>
            </div>
            <h1 className="text-xl md:text-2xl font-bold text-white tracking-tight">
              Dispatch Sovereign Motions to Real Agents
            </h1>
            <p className="text-xs md:text-sm text-neutral-400 max-w-3xl">
              Connect real autonomous tools (n8n, Python daemons, CrewAI, LangChain, Telegram bots, or custom REST webhooks). 
              Every motion is transmitted with cryptographic invariants, and incoming delivery receipts are captured into the vault.
            </p>
          </div>

          <button
            onClick={() => setIsAddOpen(true)}
            className="px-4 py-2 text-xs font-semibold text-neutral-950 bg-amber-500 hover:bg-amber-400 rounded-lg transition-colors cursor-pointer shrink-0"
          >
            + Register Agent Endpoint
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left: Dispatch Console */}
        <div className="lg:col-span-7 bg-neutral-900 border border-neutral-800 rounded-xl p-5 space-y-4">
          <div className="flex items-center justify-between border-b border-neutral-800 pb-3">
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <Send className="w-4 h-4 text-amber-400" />
              <span>Motion Dispatch Console</span>
            </h3>
            <span className="text-xs font-mono text-neutral-400">HTTP REST &amp; Webhooks</span>
          </div>

          {/* Select Motion to Dispatch */}
          <div className="space-y-1 text-xs">
            <label className="text-neutral-300 font-medium">1. Select Sovereign Motion to Dispatch:</label>
            <select
              value={selectedMotionId}
              onChange={(e) => setSelectedMotionId(e.target.value)}
              className="w-full px-3 py-2 bg-neutral-950 border border-neutral-800 rounded-lg text-white focus:outline-none focus:border-amber-500"
            >
              {motions.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.id} - {m.title} ({m.currentStage.replace(/_/g, ' ')})
                </option>
              ))}
            </select>
          </div>

          {/* Select Target Agent Endpoint */}
          <div className="space-y-1 text-xs">
            <label className="text-neutral-300 font-medium">2. Select Registered Agent Endpoint:</label>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {endpoints.map((ep) => (
                <button
                  key={ep.id}
                  onClick={() => { setSelectedEndpointId(ep.id); setCustomUrl(''); }}
                  className={`p-3 rounded-lg border text-left transition-colors cursor-pointer ${
                    selectedEndpointId === ep.id
                      ? 'bg-amber-950/40 border-amber-500 ring-1 ring-amber-500/50'
                      : 'bg-neutral-950 border-neutral-800 hover:border-neutral-700'
                  }`}
                >
                  <div className="flex items-center justify-between text-xs font-mono">
                    <span className="font-bold text-white">{ep.name}</span>
                    <span className="text-neutral-500">{ep.type}</span>
                  </div>
                  <div className="text-[11px] font-mono text-neutral-400 truncate mt-1">
                    {ep.url}
                  </div>
                  <div className="flex items-center gap-1.5 mt-2 text-[10px] font-mono">
                    <span className={`w-1.5 h-1.5 rounded-full ${
                      ep.status === 'ONLINE' ? 'bg-emerald-400' : ep.status === 'ERROR' ? 'bg-red-400' : 'bg-neutral-500'
                    }`} />
                    <span className="text-neutral-400">{ep.status}</span>
                  </div>
                </button>
              ))}
            </div>
          </div>

          {/* Override URL */}
          <div className="space-y-1 text-xs">
            <label className="text-neutral-400">Or Custom Webhook URL (Overrides selection):</label>
            <input
              type="url"
              placeholder="https://your-agent-server.com/webhook/motion"
              value={customUrl}
              onChange={(e) => setCustomUrl(e.target.value)}
              className="w-full px-3 py-2 bg-neutral-950 border border-neutral-800 rounded-lg text-white font-mono placeholder-neutral-600 focus:outline-none focus:border-amber-500"
            />
          </div>

          {/* Dispatch Button */}
          <div className="pt-2 flex items-center gap-3">
            <button
              onClick={handleDispatch}
              disabled={isDispatching}
              className="px-5 py-2.5 bg-amber-500 hover:bg-amber-400 disabled:opacity-50 text-neutral-950 font-bold rounded-lg transition-colors cursor-pointer flex items-center gap-2 text-xs shadow"
            >
              <Send className="w-3.5 h-3.5" />
              <span>{isDispatching ? 'Transmitting Invariants...' : 'Dispatch Motion via HTTP'}</span>
            </button>

            <button
              onClick={handleSimulateInboundReceipt}
              className="px-4 py-2.5 bg-neutral-800 hover:bg-neutral-700 text-neutral-300 rounded-lg transition-colors cursor-pointer text-xs"
              title="Simulate external agent sending completion proof back"
            >
              Simulate Inbound Delivery Receipt
            </button>
          </div>

          {/* Dispatch Telemetry Log */}
          {dispatchLog && (
            <div className="p-3.5 rounded-lg bg-neutral-950 border border-neutral-800 space-y-2 text-xs font-mono">
              <div className="flex items-center justify-between">
                <span className="text-neutral-400 font-bold">DISPATCH RESPONSE TELEMETRY:</span>
                <span className={`px-2 py-0.5 rounded ${dispatchLog.success ? 'text-emerald-400 bg-emerald-950' : 'text-red-400 bg-red-950'}`}>
                  {dispatchLog.success ? `HTTP ${dispatchLog.status} OK` : 'TRANSMISSION FAILED'}
                </span>
              </div>
              <div className="text-neutral-400">Target: <span className="text-white">{dispatchLog.targetUrl}</span></div>
              <div className="text-neutral-400">Roundtrip Latency: <span className="text-amber-400">{dispatchLog.latencyMs}ms</span></div>
              <div className="p-2 bg-neutral-900 rounded border border-neutral-800 text-neutral-300 overflow-x-auto">
                <pre>{JSON.stringify(dispatchLog.agentResponse || dispatchLog.error, null, 2)}</pre>
              </div>
            </div>
          )}
        </div>

        {/* Right: Inbound Delivery Receipts Webhook Listener */}
        <div className="lg:col-span-5 bg-neutral-900 border border-neutral-800 rounded-xl p-5 space-y-4">
          <div className="flex items-center justify-between border-b border-neutral-800 pb-3">
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <Terminal className="w-4 h-4 text-emerald-400" />
              <span>Inbound Webhook Listener</span>
            </h3>
            <button
              onClick={fetchReceipts}
              className="text-neutral-400 hover:text-white cursor-pointer"
              title="Refresh Receipts"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isRefreshingReceipts ? 'animate-spin' : ''}`} />
            </button>
          </div>

          {/* Live Inbound Webhook URL */}
          <div className="p-3 bg-neutral-950 rounded-lg border border-neutral-800 space-y-1.5 text-xs font-mono">
            <div className="text-neutral-400 flex items-center gap-1.5">
              <Globe className="w-3.5 h-3.5 text-emerald-400" />
              <span>Your Estate Agent Ingestion URL:</span>
            </div>
            <div className="text-amber-400 bg-neutral-900 p-2 rounded border border-neutral-800 select-all break-all text-[11px]">
              {window.location.origin}/api/agent-receipt
            </div>
            <p className="text-[10px] text-neutral-500 font-sans">
              Have your external Python scripts, n8n nodes, or LangChain agents POST their artifacts and hashes to this URL to automatically close the feedback loop.
            </p>
          </div>

          {/* Receipts Stream */}
          <div className="space-y-2">
            <div className="text-xs font-semibold text-neutral-300">
              Live Inbound Receipts Log ({inboundReceipts.length}):
            </div>

            <div className="space-y-2 max-h-[340px] overflow-y-auto pr-1">
              {inboundReceipts.map((rcpt) => (
                <div
                  key={rcpt.id}
                  className="p-3 bg-neutral-950 rounded-lg border border-neutral-800/80 space-y-1 text-xs"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono font-bold text-emerald-400 flex items-center gap-1.5">
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      {rcpt.agentId}
                    </span>
                    <span className="text-[10px] font-mono text-neutral-500">
                      {new Date(rcpt.receivedAt).toLocaleTimeString()}
                    </span>
                  </div>
                  <div className="font-semibold text-white truncate">{rcpt.artifactTitle}</div>
                  <div className="text-[10px] font-mono text-neutral-400 truncate">
                    Hash: <span className="text-amber-300">{rcpt.checksum}</span>
                  </div>
                </div>
              ))}

              {inboundReceipts.length === 0 && (
                <div className="p-8 text-center text-xs text-neutral-500 font-mono">
                  No inbound agent receipts received yet. POST to /api/agent-receipt or click "Simulate" to test.
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Register Endpoint Modal */}
      {isAddOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-xs">
          <div className="bg-neutral-900 border border-neutral-800 rounded-xl max-w-md w-full p-6 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-white">Register Real Agent Endpoint</h3>
              <button
                onClick={() => setIsAddOpen(false)}
                className="text-neutral-400 hover:text-white cursor-pointer"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleAddEndpoint} className="space-y-3 text-xs">
              <div>
                <label className="block text-neutral-300 mb-1">Agent Name / Identifier</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. n8n Main Execution Cluster"
                  value={newEpName}
                  onChange={(e) => setNewEpName(e.target.value)}
                  className="w-full px-3 py-2 bg-neutral-950 border border-neutral-800 rounded-lg text-white placeholder-neutral-500 focus:outline-none focus:border-amber-500"
                />
              </div>

              <div>
                <label className="block text-neutral-300 mb-1">Integration Framework</label>
                <select
                  value={newEpType}
                  onChange={(e) => setNewEpType(e.target.value as any)}
                  className="w-full px-3 py-2 bg-neutral-950 border border-neutral-800 rounded-lg text-white focus:outline-none focus:border-amber-500"
                >
                  <option value="n8n">n8n Workflow</option>
                  <option value="CrewAI">CrewAI Cluster</option>
                  <option value="Python">Python Daemon</option>
                  <option value="Telegram">Telegram Bot</option>
                  <option value="REST">Custom REST API</option>
                </select>
              </div>

              <div>
                <label className="block text-neutral-300 mb-1">Webhook / API URL</label>
                <input
                  type="url"
                  required
                  placeholder="https://..."
                  value={newEpUrl}
                  onChange={(e) => setNewEpUrl(e.target.value)}
                  className="w-full px-3 py-2 bg-neutral-950 border border-neutral-800 rounded-lg text-white font-mono placeholder-neutral-500 focus:outline-none focus:border-amber-500"
                />
              </div>

              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setIsAddOpen(false)}
                  className="px-4 py-2 bg-neutral-800 text-neutral-300 rounded-lg cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-amber-500 font-bold text-neutral-950 rounded-lg cursor-pointer"
                >
                  Save Endpoint
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
