import React from 'react';
import { Smartphone, Clock, ArrowUpRight, CheckCircle2, Trash2, Info, AlertTriangle } from 'lucide-react';
import { OfflineQueueItem } from '../protocol/broker';
import { CANONICAL_OFFLINE_ALLOWLIST } from '../protocol/types';

interface OfflineQueueViewProps {
  queue: OfflineQueueItem[];
  isOnline: boolean;
  onFlushQueue: () => void;
  onClearQueue: () => void;
}

export const OfflineQueueView: React.FC<OfflineQueueViewProps> = ({
  queue,
  isOnline,
  onFlushQueue,
  onClearQueue,
}) => {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <div className="flex items-center space-x-2">
            <Smartphone className="h-5 w-5 text-amber-400" />
            <h2 className="text-base font-semibold text-white">
              Mobile Node Offline Journal & Policy Guard
            </h2>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Enforces the canonical offline safe allowlist from node_protocol.json:19 without offline policy drift.
          </p>
        </div>

        <div className="flex items-center space-x-2">
          {queue.length > 0 && (
            <>
              <button
                onClick={onClearQueue}
                className="flex items-center space-x-1.5 px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium transition-colors"
              >
                <Trash2 className="h-3.5 w-3.5 text-slate-400" />
                <span>Clear Queue</span>
              </button>
              <button
                onClick={onFlushQueue}
                disabled={!isOnline}
                className="flex items-center space-x-1.5 px-3 py-1.5 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white text-xs font-semibold shadow-lg shadow-emerald-950/40 transition-all disabled:opacity-40"
              >
                <ArrowUpRight className="h-3.5 w-3.5" />
                <span>Flush to Cluster {isOnline ? '' : '(Requires Online)'}</span>
              </button>
            </>
          )}
        </div>
      </div>

      {/* Policy Boundary Banner */}
      <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 text-xs space-y-2">
        <div className="flex items-center space-x-2 text-amber-400 font-semibold">
          <AlertTriangle className="h-4 w-4 flex-shrink-0" />
          <span>Canonical Offline Safe Allowlist (node_protocol.json:19 & node_protocol.py:104)</span>
        </div>
        <div className="flex flex-wrap gap-2 pt-1 font-mono text-[11px]">
          {CANONICAL_OFFLINE_ALLOWLIST.map((action) => (
            <span
              key={action}
              className="px-2.5 py-1 rounded-lg bg-emerald-950 text-emerald-300 border border-emerald-800"
            >
              &bull; {action}
            </span>
          ))}
        </div>
        <p className="text-[11px] text-slate-400 pt-1 leading-relaxed">
          <strong>Anti-drift rule:</strong> Only the four actions above can be queued offline without a cluster lease.
          Arbitrary operations (including <code className="text-rose-300 font-mono">mobile.sync_draft</code> or unreviewed mutations)
          are strictly refused with <code className="text-rose-400 font-mono">OFFLINE_ACTION_NOT_IN_ALLOWLIST</code>.
        </p>
      </div>

      {/* Queue Listing */}
      {queue.length === 0 ? (
        <div className="py-8 text-center text-slate-500 text-xs">
          Offline journal is clean. Switch to Offline Mode and dispatch <code className="text-cyan-300 font-mono">launch</code> or <code className="text-cyan-300 font-mono">wait</code> in the sandbox to queue actions safely.
        </div>
      ) : (
        <div className="space-y-2">
          {queue.map((item) => (
            <div
              key={item.id}
              className="p-3 rounded-xl bg-slate-950 border border-slate-800 flex items-center justify-between text-xs font-mono"
            >
              <div className="space-y-0.5">
                <div className="flex items-center space-x-2">
                  <span className="text-amber-400 font-bold">{item.id}</span>
                  <span className="text-slate-400">&bull;</span>
                  <span className="text-white font-semibold">{item.envelope.capability}</span>
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-950 text-emerald-300 border border-emerald-800">
                    CANONICAL ALLOWLISTED
                  </span>
                </div>
                <div className="text-[11px] text-slate-500">
                  Call ID: {item.envelope.callId} &bull; Surface: {item.envelope.surfaceId}
                </div>
              </div>

              <div className="text-right text-[11px] text-slate-400">
                {new Date(item.enqueuedAt).toLocaleTimeString()}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
