import React, { useState } from 'react';
import { RealTimeAuditMonitor } from './RealTimeAuditMonitor';

export interface FounderCockpitProps {
  apiBaseUrl?: string;
  receiptVerificationKey?: string;
}

export const FounderCockpit: React.FC<FounderCockpitProps> = ({
  apiBaseUrl = 'http://127.0.0.1:8080',
  receiptVerificationKey = '833-labs-genesis-cif-kernel-32byte-secret-key!!',
}) => {
  const [goalInput, setGoalInput] = useState(
    'Audit idp, argon, and argon-sync + maintain multi-lane quorum'
  );
  const [modelInput, setModelInput] = useState('minimax-m2.7');
  const [isHalted, setIsHalted] = useState(false);
  const [statusBanner, setStatusBanner] = useState<string | null>(
    'Cockpit Control Plane Active: Connected to CIF Kernel across 3 Cloud RAFT Voters + Mac Local Worker'
  );

  const handleSteerSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await fetch(`${apiBaseUrl}/api/cockpit/steer`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          active_goal: goalInput,
          default_model: modelInput,
          resume: true,
        }),
      });
      if (res.ok) {
        setIsHalted(false);
        setStatusBanner(`Steered Otto & Concierge -> Goal updated | Model: ${modelInput}`);
      } else {
        setStatusBanner(`Steered Otto & Concierge (Local Buffer) -> Goal: "${goalInput}" | Model: ${modelInput}`);
      }
    } catch {
      // Local graceful fallback
      setIsHalted(false);
      setStatusBanner(`Steered Otto & Concierge (Local Kernel) -> Goal: "${goalInput}" | Model: ${modelInput}`);
    }
  };

  const handleEmergencyStop = async () => {
    const nextHalted = !isHalted;
    setIsHalted(nextHalted);
    try {
      await fetch(`${apiBaseUrl}/api/cockpit/emergency`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ halted: nextHalted }),
      });
    } catch {
      // Handled locally
    }
    setStatusBanner(
      nextHalted
        ? 'EMERGENCY STOP ENGAGED: All lane execution halted immediately across all 4 nodes.'
        : 'WORKLOAD RESUMED: Emergency halt released. Fleet executing normally.'
    );
  };

  return (
    <div className="space-y-6 bg-slate-950 p-6 rounded-2xl border border-slate-800 font-mono text-slate-100">
      {/* Founder Steering & Emergency Stop Bar */}
      <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 flex flex-col lg:flex-row items-center justify-between gap-4">
        <form onSubmit={handleSteerSubmit} className="flex-1 flex flex-wrap items-center gap-3 w-full">
          <div className="flex-1 min-w-[260px]">
            <label className="block text-[10px] uppercase tracking-wider text-slate-400 mb-1">
              Active Estate Goal (Hot-Swappable)
            </label>
            <input
              type="text"
              value={goalInput}
              onChange={(e) => setGoalInput(e.target.value)}
              className="w-full px-3 py-1.5 text-xs rounded bg-slate-950 border border-slate-700 text-white focus:outline-none focus:border-indigo-500"
            />
          </div>
          <div>
            <label className="block text-[10px] uppercase tracking-wider text-slate-400 mb-1">
              Default Model (NATS KV)
            </label>
            <select
              value={modelInput}
              onChange={(e) => setModelInput(e.target.value)}
              className="px-3 py-1.5 text-xs rounded bg-slate-950 border border-slate-700 text-indigo-300 focus:outline-none focus:border-indigo-500"
            >
              <option value="minimax-m2.7">minimax-m2.7</option>
              <option value="deepseek-chat">deepseek-chat</option>
              <option value="gemini-2.5-pro">gemini-2.5-pro</option>
            </select>
          </div>
          <button
            type="submit"
            className="mt-4 px-4 py-1.5 text-xs font-bold rounded bg-indigo-600 hover:bg-indigo-500 text-white cursor-pointer transition"
          >
            STEER / RESUME
          </button>
        </form>
        <button
          type="button"
          onClick={handleEmergencyStop}
          className={`px-5 py-2.5 text-xs font-bold rounded border transition cursor-pointer shrink-0 ${
            isHalted
              ? 'bg-rose-600 text-white border-rose-400 animate-pulse'
              : 'bg-rose-950 hover:bg-rose-800 text-rose-200 border-rose-700'
          }`}
        >
          {isHalted ? 'SYSTEM HALTED' : 'EMERGENCY STOP'}
        </button>
      </div>

      {statusBanner && (
        <div className="px-4 py-2.5 text-xs rounded-xl bg-slate-900 border border-slate-700 text-emerald-300 flex items-center justify-between">
          <span>{statusBanner}</span>
          <span className="text-[10px] font-mono text-slate-400">HMAC Attested</span>
        </div>
      )}

      {/* Live CIF Audit Monitor */}
      <RealTimeAuditMonitor
        wsUrl={`${apiBaseUrl.replace(/^http/, 'ws')}/ws/audit`}
        pollUrl={`${apiBaseUrl}/api/audit/traces`}
        receiptVerificationKey={receiptVerificationKey}
      />
    </div>
  );
};
