import React, { useState, useMemo } from 'react';
import {
  FileCheck,
  Search,
  ShieldCheck,
  ShieldAlert,
  Copy,
  Check,
  Key,
  Terminal,
  Bug,
  RotateCcw,
  CheckCircle2,
  XCircle,
  ChevronDown,
  ChevronRight,
  Fingerprint,
} from 'lucide-react';
import { Receipt } from '../protocol/types';
import {
  verifyReceiptSignature,
  ReceiptVerificationResult,
  canonicalizeReceiptPayload,
  CANONICAL_ISSUER_KEY_ID,
} from '../protocol/crypto';
import { PINNED_RULES_HASH } from '../protocol/rules';

interface ReceiptLedgerViewProps {
  receipts: Receipt[];
}

export const ReceiptLedgerView: React.FC<ReceiptLedgerViewProps> = ({ receipts }) => {
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [selectedReceiptId, setSelectedReceiptId] = useState<string | null>(null);

  // Local simulated tampered receipts for the tamper laboratory
  const [tamperedReceipts, setTamperedReceipts] = useState<Record<string, Partial<Receipt>>>({});

  // Merge simulated tampering into receipts
  const activeReceipts = useMemo(() => {
    return receipts.map((r) => {
      const overrides = tamperedReceipts[r.receiptId];
      if (overrides) {
        return { ...r, ...overrides };
      }
      return r;
    });
  }, [receipts, tamperedReceipts]);

  // Compute live verification results for all receipts
  const verificationMap = useMemo(() => {
    const map = new Map<string, ReceiptVerificationResult>();
    for (const r of activeReceipts) {
      map.set(r.receiptId, verifyReceiptSignature(r));
    }
    return map;
  }, [activeReceipts]);

  const filteredReceipts = activeReceipts.filter(
    (r) =>
      r.receiptId.toLowerCase().includes(searchTerm.toLowerCase()) ||
      r.callId.toLowerCase().includes(searchTerm.toLowerCase()) ||
      r.surfaceId.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const copyText = (id: string, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const simulateTamper = (receiptId: string, field: 'rulesHash' | 'digest' | 'signature') => {
    setTamperedReceipts((prev) => {
      if (field === 'rulesHash') {
        return {
          ...prev,
          [receiptId]: {
            ...prev[receiptId],
            rulesHash: 'tampered_rules_hash_bad8981c2',
          },
        };
      } else if (field === 'digest') {
        return {
          ...prev,
          [receiptId]: {
            ...prev[receiptId],
            digest: 'sha256:tampered_payload_digest_attack_999',
          },
        };
      } else if (field === 'signature') {
        return {
          ...prev,
          [receiptId]: {
            ...prev[receiptId],
            signature: 'sig_v1_tampered_forged_bytes_000000000',
          },
        };
      }
      return prev;
    });
  };

  const resetTamper = (receiptId: string) => {
    setTamperedReceipts((prev) => {
      const copy = { ...prev };
      delete copy[receiptId];
      return copy;
    });
  };

  const allVerified = activeReceipts.every((r) => verificationMap.get(r.receiptId)?.valid);

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <div className="flex items-center space-x-2">
            <Fingerprint className="h-5 w-5 text-cyan-400" />
            <h2 className="text-base font-semibold text-white">
              Cryptographic Receipt Verification & Signature Audit Module
            </h2>
            <span
              className={`text-xs px-2 py-0.5 rounded-full border font-mono font-medium ${
                allVerified
                  ? 'bg-emerald-950 text-emerald-300 border-emerald-800'
                  : 'bg-rose-950 text-rose-300 border-rose-800'
              }`}
            >
              {allVerified ? 'All Signatures Valid' : 'Tamper Detected'}
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Simulates HMAC-SHA256 issuer signature validation and canonical rules hash binding against RFC-8785 serialized payloads.
          </p>
        </div>

        {/* Search */}
        <div className="relative">
          <Search className="h-3.5 w-3.5 text-slate-400 absolute left-3 top-2.5" />
          <input
            type="text"
            placeholder="Search receipt, call, or surface..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="bg-slate-950 border border-slate-800 rounded-xl pl-9 pr-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500 font-mono w-64"
          />
        </div>
      </div>

      {/* Verification Summary Banner */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800">
          <div className="flex items-center space-x-2 text-xs text-slate-400 font-medium">
            <Key className="h-4 w-4 text-cyan-400" />
            <span>Issuer Key Identity</span>
          </div>
          <div className="text-xs font-mono font-bold text-white mt-1.5 truncate">
            {CANONICAL_ISSUER_KEY_ID}
          </div>
          <div className="text-[10px] text-slate-400 mt-0.5">Argon Genesis Cluster KMS</div>
        </div>

        <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800">
          <div className="flex items-center space-x-2 text-xs text-slate-400 font-medium">
            <ShieldCheck className="h-4 w-4 text-emerald-400" />
            <span>Signature Algorithm</span>
          </div>
          <div className="text-xs font-mono font-bold text-emerald-400 mt-1.5">
            HMAC-SHA256 (RFC-8785)
          </div>
          <div className="text-[10px] text-slate-400 mt-0.5">Replaced 'none' placeholder</div>
        </div>

        <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800">
          <div className="flex items-center space-x-2 text-xs text-slate-400 font-medium">
            <Fingerprint className="h-4 w-4 text-indigo-400" />
            <span>Rules Hash Binding</span>
          </div>
          <div className="text-xs font-mono font-bold text-cyan-300 mt-1.5 truncate">
            {PINNED_RULES_HASH.slice(0, 16)}...
          </div>
          <div className="text-[10px] text-slate-400 mt-0.5">18e3ccdaee2a... pinned</div>
        </div>
      </div>

      {/* Receipts Table with Live Verification Badges */}
      <div className="border border-slate-800 rounded-xl overflow-hidden">
        <table className="w-full text-left text-xs">
          <thead className="bg-slate-950 text-slate-400 border-b border-slate-800 font-mono text-[11px]">
            <tr>
              <th className="py-2.5 px-4 font-medium">Receipt ID & Issuer</th>
              <th className="py-2.5 px-4 font-medium">Target Call / Tenant</th>
              <th className="py-2.5 px-4 font-medium">Cryptographic Signature Status</th>
              <th className="py-2.5 px-4 font-medium hidden md:table-cell">Digest / Rules Binding</th>
              <th className="py-2.5 px-4 font-medium text-right">Tamper Test / Inspect</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/70 bg-slate-950/40 font-mono text-[11px]">
            {filteredReceipts.length === 0 ? (
              <tr>
                <td colSpan={5} className="py-8 text-center text-slate-400">
                  No receipts matching query
                </td>
              </tr>
            ) : (
              filteredReceipts.map((r) => {
                const vResult = verificationMap.get(r.receiptId);
                const isSelected = selectedReceiptId === r.receiptId;
                const isTampered = !!tamperedReceipts[r.receiptId];

                return (
                  <React.Fragment key={r.receiptId}>
                    <tr className="hover:bg-slate-900/40 transition-colors">
                      <td className="py-3 px-4">
                        <div className="flex items-center space-x-1.5">
                          <span className="text-cyan-400 font-bold">{r.receiptId}</span>
                          <button
                            onClick={() => copyText(r.receiptId, r.receiptId)}
                            className="text-slate-400 hover:text-white p-0.5"
                            title="Copy Receipt ID"
                          >
                            {copiedId === r.receiptId ? (
                              <Check className="h-3 w-3 text-emerald-400" />
                            ) : (
                              <Copy className="h-3 w-3" />
                            )}
                          </button>
                        </div>
                        <div className="text-[10px] text-slate-400">{r.issuer}</div>
                      </td>

                      <td className="py-3 px-4">
                        <div className="text-slate-300">{r.callId}</div>
                        <div className="text-[10px] text-amber-400">{r.tenantId}</div>
                      </td>

                      <td className="py-3 px-4">
                        {vResult?.valid ? (
                          <span className="inline-flex items-center space-x-1.5 px-2.5 py-0.5 rounded-full bg-emerald-950 text-emerald-300 border border-emerald-800 text-[10px] font-bold">
                            <CheckCircle2 className="h-3 w-3 text-emerald-400" />
                            <span>VALID (HMAC-SHA256)</span>
                          </span>
                        ) : (
                          <span className="inline-flex items-center space-x-1.5 px-2.5 py-0.5 rounded-full bg-rose-950 text-rose-300 border border-rose-800 text-[10px] font-bold">
                            <XCircle className="h-3 w-3 text-rose-400" />
                            <span>INVALID / TAMPERED</span>
                          </span>
                        )}
                        <div className="text-[10px] text-slate-400 font-mono mt-0.5 truncate max-w-[200px]" title={r.signature}>
                          {r.signature ? r.signature.slice(0, 24) + '...' : 'none'}
                        </div>
                      </td>

                      <td className="py-3 px-4 hidden md:table-cell text-slate-400">
                        <div>
                          Digest:{' '}
                          <span className="text-slate-300">{r.digest.slice(0, 16)}...</span>
                        </div>
                        <div className="text-[10px]">
                          Rules:{' '}
                          <span
                            className={
                              vResult?.rulesHashBound ? 'text-emerald-400' : 'text-rose-400 font-bold'
                            }
                          >
                            {r.rulesHash.slice(0, 12)}...
                          </span>
                        </div>
                      </td>

                      <td className="py-3 px-4 text-right">
                        <div className="flex items-center justify-end space-x-2">
                          {isTampered ? (
                            <button
                              onClick={() => resetTamper(r.receiptId)}
                              className="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-[10px] flex items-center space-x-1"
                              title="Reset to untampered state"
                            >
                              <RotateCcw className="h-3 w-3" />
                              <span>Reset</span>
                            </button>
                          ) : (
                            <div className="flex items-center space-x-1">
                              <button
                                onClick={() => simulateTamper(r.receiptId, 'digest')}
                                className="px-1.5 py-0.5 rounded bg-rose-950/80 hover:bg-rose-900 border border-rose-800 text-rose-300 text-[10px]"
                                title="Simulate tampering with payload digest"
                              >
                                Mutate Digest
                              </button>
                              <button
                                onClick={() => simulateTamper(r.receiptId, 'rulesHash')}
                                className="px-1.5 py-0.5 rounded bg-rose-950/80 hover:bg-rose-900 border border-rose-800 text-rose-300 text-[10px]"
                                title="Simulate tampering with rules hash"
                              >
                                Mutate Rules
                              </button>
                            </div>
                          )}

                          <button
                            onClick={() =>
                              setSelectedReceiptId(isSelected ? null : r.receiptId)
                            }
                            className="p-1 rounded hover:bg-slate-800 text-slate-400 hover:text-white"
                            title="Inspect cryptographic proof"
                          >
                            {isSelected ? (
                              <ChevronDown className="h-4 w-4" />
                            ) : (
                              <ChevronRight className="h-4 w-4" />
                            )}
                          </button>
                        </div>
                      </td>
                    </tr>

                    {/* Expandable Cryptographic Inspector */}
                    {isSelected && (
                      <tr className="bg-slate-950/80 border-b border-slate-800/80">
                        <td colSpan={5} className="p-4 space-y-3">
                          <div className="flex items-center justify-between pb-2 border-b border-slate-800">
                            <span className="font-semibold text-white text-xs flex items-center space-x-1.5">
                              <ShieldCheck className="h-4 w-4 text-cyan-400" />
                              <span>Cryptographic Audit Proof Inspector</span>
                            </span>
                            <span className="text-[10px] text-slate-400">
                              Verified at: {new Date(vResult?.verifiedAt || Date.now()).toLocaleTimeString()}
                            </span>
                          </div>

                          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
                            <div className="p-2.5 rounded-lg bg-slate-900 border border-slate-800">
                              <span className="text-slate-400 text-[11px] block">1. Rules Hash Verification</span>
                              <span
                                className={`font-bold font-mono text-[11px] ${
                                  vResult?.rulesHashBound ? 'text-emerald-400' : 'text-rose-400'
                                }`}
                              >
                                {vResult?.rulesHashBound
                                  ? 'BOUND TO CANONICAL HASH'
                                  : 'TAMPERED / MISMATCHED'}
                              </span>
                            </div>

                            <div className="p-2.5 rounded-lg bg-slate-900 border border-slate-800">
                              <span className="text-slate-400 text-[11px] block">2. Payload Digest Format</span>
                              <span
                                className={`font-bold font-mono text-[11px] ${
                                  vResult?.digestValid ? 'text-emerald-400' : 'text-rose-400'
                                }`}
                              >
                                {vResult?.digestValid ? 'VALID SHA-256' : 'INVALID DIGEST'}
                              </span>
                            </div>

                            <div className="p-2.5 rounded-lg bg-slate-900 border border-slate-800">
                              <span className="text-slate-400 text-[11px] block">3. Issuer Signature Match</span>
                              <span
                                className={`font-bold font-mono text-[11px] ${
                                  vResult?.signatureValid ? 'text-emerald-400' : 'text-rose-400'
                                }`}
                              >
                                {vResult?.signatureValid ? 'HMAC-SHA256 MATCH' : 'SIGNATURE REJECTED'}
                              </span>
                            </div>
                          </div>

                          {vResult?.reason && (
                            <div className="p-2.5 rounded-lg bg-rose-950/40 border border-rose-800/60 text-rose-300 text-xs">
                              <span className="font-bold">Failure Reason:</span> {vResult.reason}
                            </div>
                          )}

                          <div>
                            <span className="text-[10px] text-slate-400 font-mono block mb-1">
                              Canonical RFC-8785 Serialization String:
                            </span>
                            <pre className="p-2.5 rounded bg-slate-950 border border-slate-800 text-[10px] text-slate-300 font-mono whitespace-pre-wrap break-all overflow-x-auto">
                              {canonicalizeReceiptPayload(r)}
                            </pre>
                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
