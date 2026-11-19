/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState } from 'react';
import {
  X,
  ShieldCheck,
  ShieldAlert,
  Copy,
  Check,
  Database,
  Lock,
  FileCode,
} from 'lucide-react';
import { MerkleLedgerBlock } from '../types/optimus';

interface BlockDetailModalProps {
  block: MerkleLedgerBlock | null;
  onClose: () => void;
}

export const BlockDetailModal: React.FC<BlockDetailModalProps> = ({ block, onClose }) => {
  const [copiedJson, setCopiedJson] = useState(false);

  if (!block) return null;

  const isRatified = block.status === 'RATIFIED_AND_SIGNED';

  const inTotoAttestationBundle = {
    _type: 'https://in-toto.io/Statement/v1',
    subject: [
      {
        name: block.entityId,
        digest: {
          sha256: block.blockHash,
        },
      },
    ],
    predicateType: 'https://slsa.dev/provenance/v1',
    predicate: {
      builder: {
        id: 'https://optimus.internal.estate/builder/v3',
      },
      buildType: 'https://optimus.internal.estate/zero-circumvention/v1',
      invocation: {
        surface: block.surface,
        actor: block.actor,
        timestamp: block.timestamp,
        merkleHeight: block.index,
      },
      metadata: {
        completeness: {
          parameters: true,
          environment: true,
          materials: true,
        },
        reproducible: true,
      },
      metricsSnapshot: block.metricsSnapshot,
      cryptographicSignature: block.signature,
      merkleRoot: block.merkleRoot,
      previousBlockHash: block.previousHash,
    },
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(JSON.stringify(inTotoAttestationBundle, null, 2));
    setCopiedJson(true);
    setTimeout(() => setCopiedJson(false), 2000);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
      <div className="bg-[#0b0f17] border border-slate-800 rounded-xl max-w-2xl w-full max-h-[90vh] flex flex-col shadow-2xl">
        {/* Modal Header */}
        <div className="p-4 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="p-1.5 rounded bg-slate-900 border border-slate-800">
              <Database className="w-4 h-4 text-indigo-400" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <span>Block #{block.index}</span>
                <span
                  className={`text-[10px] font-mono px-2 py-0.5 rounded font-bold ${
                    isRatified
                      ? 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                      : 'bg-red-950 text-red-400 border border-red-800'
                  }`}
                >
                  {block.status}
                </span>
              </h3>
              <div className="text-[11px] text-slate-400 font-mono">
                {block.surface} · {block.entityId}
              </div>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-5 overflow-y-auto space-y-4 text-xs font-sans">
          {/* Rejection Alert if Blocked */}
          {!isRatified && block.rejectionSummary && (
            <div className="p-3.5 rounded-lg bg-red-950/40 border border-red-800 text-red-300 space-y-1">
              <div className="font-bold flex items-center gap-1.5 text-xs text-red-400">
                <ShieldAlert className="w-4 h-4" />
                <span>CIRCUMVENTION / INVARIANT VIOLATION INTERCEPTED</span>
              </div>
              <p className="text-[11px] leading-relaxed">{block.rejectionSummary}</p>
            </div>
          )}

          {/* Cryptographic Proof Details */}
          <div className="bg-slate-950 border border-slate-800/80 rounded-lg p-3.5 space-y-2 font-mono text-[11px]">
            <div className="text-slate-400 font-bold uppercase text-[10px] flex items-center gap-1.5">
              <Lock className="w-3 h-3 text-indigo-400" />
              <span>Cryptographic Attestation Proofs</span>
            </div>

            <div className="space-y-1.5 pt-1 text-slate-300">
              <div>
                <span className="text-slate-500 block">Block SHA-256 Hash:</span>
                <span className="text-emerald-400 break-all">{block.blockHash}</span>
              </div>
              <div>
                <span className="text-slate-500 block">Previous Chained Hash:</span>
                <span className="text-slate-400 break-all">{block.previousHash}</span>
              </div>
              <div>
                <span className="text-slate-500 block">Merkle Tree Root:</span>
                <span className="text-indigo-300 break-all">{block.merkleRoot}</span>
              </div>
              <div>
                <span className="text-slate-500 block">ECDSA Signature:</span>
                <span className="text-slate-400 break-all">{block.signature}</span>
              </div>
            </div>
          </div>

          {/* Metric Snapshot */}
          <div className="space-y-2">
            <span className="text-xs font-bold text-slate-300 uppercase tracking-wider block">
              Submitted Metric Snapshot
            </span>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
              {Object.entries(block.metricsSnapshot).map(([key, value]) => (
                <div key={key} className="p-2 rounded bg-slate-900 border border-slate-800 font-mono text-[11px]">
                  <span className="text-slate-500 block truncate">{key}</span>
                  <span className="text-white font-bold">{String(value)}</span>
                </div>
              ))}
            </div>
          </div>

          {/* in-toto Attestation JSON */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
                <FileCode className="w-3.5 h-3.5 text-indigo-400" />
                <span>in-toto Attestation Statement (SLSA Provenance v1)</span>
              </span>
              <button
                onClick={handleCopy}
                className="text-xs font-mono text-indigo-400 hover:text-indigo-300 flex items-center gap-1"
              >
                {copiedJson ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                <span>{copiedJson ? 'Copied' : 'Copy JSON'}</span>
              </button>
            </div>
            <div className="p-3 bg-slate-950 rounded border border-slate-800 font-mono text-[11px] text-slate-300 max-h-48 overflow-y-auto">
              <pre>{JSON.stringify(inTotoAttestationBundle, null, 2)}</pre>
            </div>
          </div>
        </div>

        {/* Modal Footer */}
        <div className="p-4 border-t border-slate-800 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-1.5 text-xs font-semibold rounded bg-slate-800 hover:bg-slate-700 text-white transition-colors"
          >
            Close Inspector
          </button>
        </div>
      </div>
    </div>
  );
};
