import React, { useState } from 'react';
import {
  Laptop,
  Server,
  Smartphone,
  Cpu,
  Clock,
  AlertTriangle,
  CheckCircle,
  HelpCircle,
  Shield,
  ArrowRight,
  RefreshCw,
} from 'lucide-react';
import { SurfaceAck, AgreementState } from '../protocol/types';
import { INITIAL_SURFACE_ACKS } from '../protocol/telemetry';

export const DisconnectedSurfacesView: React.FC = () => {
  const [surfaces, setSurfaces] = useState<SurfaceAck[]>(INITIAL_SURFACE_ACKS);

  const simulateAck = (surfaceId: string) => {
    setSurfaces((prev) =>
      prev.map((s) => {
        if (s.surfaceId === surfaceId) {
          return {
            ...s,
            state: 'agreed',
            token: `tok_ack_${Math.random().toString(36).slice(2, 10)}`,
            lastSeenMs: Date.now(),
            authSource: 'Cryptographic One-Time Token',
          };
        }
        return s;
      })
    );
  };

  const simulateExpire = (surfaceId: string) => {
    setSurfaces((prev) =>
      prev.map((s) => {
        if (s.surfaceId === surfaceId) {
          return {
            ...s,
            state: 'blind',
            token: undefined,
            deadlineMs: Date.now() - 1000,
          };
        }
        return s;
      })
    );
  };

  const agreedCount = surfaces.filter((s) => s.state === 'agreed').length;
  const deferredCount = surfaces.filter((s) => s.state === 'deferred').length;
  const blindCount = surfaces.filter((s) => s.state === 'blind').length;

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <div className="flex items-center space-x-2">
            <Shield className="h-5 w-5 text-indigo-400" />
            <h2 className="text-base font-semibold text-white">
              Cross-Surface Consensus & Disconnected Architecture Matrix
            </h2>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Eliminating false 100% self-reported scores with 3-state consensus: Agreed (One-Time Token), Deferred, or Blind.
          </p>
        </div>

        {/* 3-State Consensus Counter */}
        <div className="flex items-center space-x-2 text-xs font-mono">
          <span className="px-2.5 py-1 rounded-lg bg-emerald-950/80 border border-emerald-800 text-emerald-300 font-semibold">
            {agreedCount} Agreed
          </span>
          <span className="px-2.5 py-1 rounded-lg bg-amber-950/80 border border-amber-800 text-amber-300 font-semibold">
            {deferredCount} Deferred
          </span>
          <span className="px-2.5 py-1 rounded-lg bg-rose-950/80 border border-rose-800 text-rose-300 font-semibold">
            {blindCount} Blind
          </span>
        </div>
      </div>

      {/* Surface Architecture Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Surface 1: Mac Local Helper */}
        <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 flex flex-col justify-between space-y-3">
          <div>
            <div className="flex items-center justify-between">
              <span className="p-2 rounded-lg bg-indigo-950 text-indigo-400 border border-indigo-800/80">
                <Laptop className="h-4 w-4" />
              </span>
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 font-mono">
                Client Helper
              </span>
            </div>
            <h3 className="text-xs font-bold text-white mt-3">Mac Session CLI Helper</h3>
            <p className="text-[11px] text-slate-400 mt-1 leading-relaxed">
              `genesis-control-plane` local workspace tool. Client-side helper only—no cluster authority.
            </p>
          </div>
          <div className="pt-2 border-t border-slate-900 text-[10px] font-mono text-indigo-300">
            Path: session-local CLI
          </div>
        </div>

        {/* Surface 2: Argon Genesis Cluster */}
        <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 flex flex-col justify-between space-y-3">
          <div>
            <div className="flex items-center justify-between">
              <span className="p-2 rounded-lg bg-cyan-950 text-cyan-400 border border-cyan-800/80">
                <Server className="h-4 w-4" />
              </span>
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-cyan-950 text-cyan-300 border border-cyan-800 font-mono font-medium">
                Canonical Plane
              </span>
            </div>
            <h3 className="text-xs font-bold text-white mt-3">Argon Genesis (Dagster)</h3>
            <p className="text-[11px] text-slate-400 mt-1 leading-relaxed">
              Cluster single pane of glass. Dagster clock controls cron jobs; issues cryptographic receipts & authority.
            </p>
          </div>
          <div className="pt-2 border-t border-slate-900 text-[10px] font-mono text-cyan-300">
            Authority: Cluster Gateway
          </div>
        </div>

        {/* Surface 3: Mobile Node */}
        <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 flex flex-col justify-between space-y-3">
          <div>
            <div className="flex items-center justify-between">
              <span className="p-2 rounded-lg bg-amber-950 text-amber-400 border border-amber-800/80">
                <Smartphone className="h-4 w-4" />
              </span>
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-amber-950 text-amber-300 border border-amber-800 font-mono">
                Offline-First
              </span>
            </div>
            <h3 className="text-xs font-bold text-white mt-3">Mobile Node Client</h3>
            <p className="text-[11px] text-slate-400 mt-1 leading-relaxed">
              Safe mutations queue into local journal without lease; unsafe operations strictly refused when offline.
            </p>
          </div>
          <div className="pt-2 border-t border-slate-900 text-[10px] font-mono text-amber-300">
            Offline Policy: Safe Queue
          </div>
        </div>

        {/* Surface 4: CI Worker Runner */}
        <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 flex flex-col justify-between space-y-3">
          <div>
            <div className="flex items-center justify-between">
              <span className="p-2 rounded-lg bg-emerald-950 text-emerald-400 border border-emerald-800/80">
                <Cpu className="h-4 w-4" />
              </span>
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-950 text-emerald-300 border border-emerald-800 font-mono">
                Automated Gate
              </span>
            </div>
            <h3 className="text-xs font-bold text-white mt-3">CI Worker (MUM-298)</h3>
            <p className="text-[11px] text-slate-400 mt-1 leading-relaxed">
              Estate verification gate. Verified on Git head `cd17573 (main 3e761b5)`; records into action ledger.
            </p>
          </div>
          <div className="pt-2 border-t border-slate-900 text-[10px] font-mono text-emerald-300">
            Verified Git: cd17573
          </div>
        </div>
      </div>

      {/* Surface Agreement & Acknowledgment Status Table */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
            Surface Acknowledgment Consensus Ledger (No Self-Report Dial)
          </h3>
          <span className="text-[11px] text-slate-400">
            Silence != Consent &bull; Governed by verifiable one-time tokens
          </span>
        </div>

        <div className="border border-slate-800 rounded-xl overflow-hidden">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-950 text-slate-400 border-b border-slate-800 font-mono text-[11px]">
              <tr>
                <th className="py-2.5 px-4 font-medium">Surface Surface ID</th>
                <th className="py-2.5 px-4 font-medium">Consensus State</th>
                <th className="py-2.5 px-4 font-medium hidden sm:table-cell">Authority Source</th>
                <th className="py-2.5 px-4 font-medium hidden md:table-cell">Token / Deadline</th>
                <th className="py-2.5 px-4 font-medium text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/70 bg-slate-950/40">
              {surfaces.map((s) => (
                <tr key={s.surfaceId} className="hover:bg-slate-900/40 transition-colors">
                  <td className="py-3 px-4">
                    <div className="font-semibold text-white">{s.label}</div>
                    <div className="text-[11px] text-slate-400 font-mono mt-0.5">{s.surfaceId}</div>
                  </td>
                  <td className="py-3 px-4">
                    {s.state === 'agreed' && (
                      <span className="inline-flex items-center space-x-1.5 px-2 py-0.5 rounded-full bg-emerald-950/90 text-emerald-300 border border-emerald-800 text-[11px] font-mono font-bold">
                        <CheckCircle className="h-3 w-3 text-emerald-400" />
                        <span>AGREED</span>
                      </span>
                    )}
                    {s.state === 'deferred' && (
                      <span className="inline-flex items-center space-x-1.5 px-2 py-0.5 rounded-full bg-amber-950/90 text-amber-300 border border-amber-800 text-[11px] font-mono font-bold">
                        <Clock className="h-3 w-3 text-amber-400" />
                        <span>DEFERRED</span>
                      </span>
                    )}
                    {s.state === 'blind' && (
                      <span className="inline-flex items-center space-x-1.5 px-2 py-0.5 rounded-full bg-rose-950/90 text-rose-300 border border-rose-800 text-[11px] font-mono font-bold">
                        <AlertTriangle className="h-3 w-3 text-rose-400" />
                        <span>BLIND</span>
                      </span>
                    )}
                  </td>
                  <td className="py-3 px-4 text-slate-300 hidden sm:table-cell font-mono text-[11px]">
                    {s.authSource}
                  </td>
                  <td className="py-3 px-4 hidden md:table-cell font-mono text-[11px]">
                    {s.token ? (
                      <span className="text-cyan-400">{s.token}</span>
                    ) : s.deadlineMs && s.deadlineMs > Date.now() ? (
                      <span className="text-amber-400">
                        Deadline in {Math.round((s.deadlineMs - Date.now()) / 60000)}m
                      </span>
                    ) : (
                      <span className="text-rose-400">Deadline Expired</span>
                    )}
                  </td>
                  <td className="py-3 px-4 text-right">
                    <div className="flex items-center justify-end space-x-2">
                      {s.state !== 'agreed' && (
                        <button
                          onClick={() => simulateAck(s.surfaceId)}
                          className="px-2 py-1 rounded bg-emerald-950 hover:bg-emerald-900 border border-emerald-800 text-emerald-300 text-[10px] font-mono transition-colors"
                        >
                          Emit Token
                        </button>
                      )}
                      {s.state !== 'blind' && (
                        <button
                          onClick={() => simulateExpire(s.surfaceId)}
                          className="px-2 py-1 rounded bg-slate-900 hover:bg-rose-950 border border-slate-800 hover:border-rose-800 text-slate-400 hover:text-rose-300 text-[10px] font-mono transition-colors"
                        >
                          Expire
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
