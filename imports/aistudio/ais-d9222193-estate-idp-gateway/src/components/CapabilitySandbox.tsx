import React, { useState } from 'react';
import {
  Send,
  ShieldCheck,
  ShieldAlert,
  Clock,
  Sparkles,
  FileCheck2,
  AlertTriangle,
  RotateCcw,
  Check,
  Copy,
  Layers,
  Server,
  Terminal,
} from 'lucide-react';
import { IdpGatewayClientHarness } from '../protocol/broker';
import { PINNED_RULES_HASH } from '../protocol/rules';
import { Envelope, ActionType, AdmissionResult, Receipt, Lease } from '../protocol/types';

interface CapabilitySandboxProps {
  broker: IdpGatewayClientHarness;
  isOnline: boolean;
  onReceiptIssued: (receipt: Receipt) => void;
  onQueueUpdated: () => void;
}

export const CapabilitySandbox: React.FC<CapabilitySandboxProps> = ({
  broker,
  isOnline,
  onReceiptIssued,
  onQueueUpdated,
}) => {
  const [selectedPreset, setSelectedPreset] = useState<string>('pr_sync');

  // Form states
  const [tenantId, setTenantId] = useState<string>('tenant_estate_primary');
  const [surfaceId, setSurfaceId] = useState<string>('mac_session_460567726510256');
  const [capability, setCapability] = useState<string>('git.pr_sync');
  const [actionType, setActionType] = useState<ActionType>('mutation');
  const [leaseOption, setLeaseOption] = useState<'valid' | 'expired' | 'none'>('valid');
  const [contextHashOption, setContextHashOption] = useState<'valid' | 'missing'>('valid');
  const [idempotencyKey, setIdempotencyKey] = useState<string>(`idem_${Date.now()}`);
  const [rulesHashOption, setRulesHashOption] = useState<'pinned' | 'tampered'>('pinned');
  const [evidenceDigest, setEvidenceDigest] = useState<string>('sha256:ev_fresh_evidence_101');
  const [payloadText, setPayloadText] = useState<string>(
    JSON.stringify({ branch: 'feat/idp-gateway', prNumber: 7760, targetCommit: 'cd17573' }, null, 2)
  );

  // Result state
  const [lastResult, setLastResult] = useState<AdmissionResult | null>(null);
  const [lastEnvelope, setLastEnvelope] = useState<Envelope | null>(null);
  const [isExecuting, setIsExecuting] = useState<boolean>(false);
  const [copiedReceipt, setCopiedReceipt] = useState<boolean>(false);

  // Apply preset configurations
  const applyPreset = (preset: string) => {
    setSelectedPreset(preset);
    if (preset === 'pr_sync') {
      setSurfaceId('mac_session_460567726510256');
      setCapability('git.pr_sync');
      setActionType('mutation');
      setLeaseOption('valid');
      setContextHashOption('valid');
      setIdempotencyKey(`idem_pr_${Date.now()}`);
      setRulesHashOption('pinned');
      setPayloadText(JSON.stringify({ branch: 'feat/idp-gateway', prNumber: 7760, targetCommit: 'cd17573' }, null, 2));
    } else if (preset === 'offline_launch') {
      // Canonical allowlisted offline action per node_protocol.json:19
      setSurfaceId('mobile_node_ios_client');
      setCapability('launch');
      setActionType('safe_mutation');
      setLeaseOption('none');
      setContextHashOption('missing');
      setIdempotencyKey(`idem_launch_${Date.now()}`);
      setRulesHashOption('pinned');
      setPayloadText(JSON.stringify({ action: 'launch', targetApp: 'estate-node-ui' }, null, 2));
    } else if (preset === 'offline_drift') {
      // Attempting to queue mobile.sync_draft which is NOT in node_protocol.json:19 allowlist
      setSurfaceId('mobile_node_ios_client');
      setCapability('mobile.sync_draft');
      setActionType('safe_mutation');
      setLeaseOption('none');
      setContextHashOption('missing');
      setIdempotencyKey(`idem_drift_${Date.now()}`);
      setRulesHashOption('pinned');
      setPayloadText(JSON.stringify({ draftText: 'unreviewed offline policy mutation' }, null, 2));
    } else if (preset === 'unsafe_deploy') {
      setSurfaceId('mobile_node_ios_client');
      setCapability('cluster.deploy');
      setActionType('unsafe_mutation');
      setLeaseOption('none');
      setContextHashOption('valid');
      setIdempotencyKey(`idem_deploy_${Date.now()}`);
      setRulesHashOption('pinned');
      setPayloadText(JSON.stringify({ env: 'production', releaseTag: 'v1.4.0' }, null, 2));
    } else if (preset === 'unknown_capability') {
      setSurfaceId('ci_worker_runner_01');
      setCapability('estate.force_drop_all');
      setActionType('mutation');
      setLeaseOption('valid');
      setContextHashOption('valid');
      setIdempotencyKey(`idem_unk_${Date.now()}`);
      setRulesHashOption('pinned');
      setPayloadText(JSON.stringify({ target: 'all_tables' }, null, 2));
    }
  };

  const handleDispatch = async () => {
    setIsExecuting(true);

    let parsedPayload: unknown;
    try {
      parsedPayload = JSON.parse(payloadText);
    } catch {
      parsedPayload = { text: payloadText };
    }

    // Build Lease
    let lease: Lease | null = null;
    if (leaseOption === 'valid') {
      lease = {
        token: `lease_tok_${Math.random().toString(36).slice(2, 10)}`,
        surfaceId,
        grantedAt: Date.now(),
        expiresAt: Date.now() + 3600000,
        scope: [capability],
      };
    } else if (leaseOption === 'expired') {
      lease = {
        token: `lease_expired_${Math.random().toString(36).slice(2, 8)}`,
        surfaceId,
        grantedAt: Date.now() - 7200000,
        expiresAt: Date.now() - 5000,
        scope: [capability],
      };
    }

    const compiledContextHash =
      contextHashOption === 'valid'
        ? 'sha256:ctx_f148e711b391f47a6d79061e9970593070d49f3f19947ef9094c9055759abf2d'
        : '';

    const rulesHash =
      rulesHashOption === 'pinned'
        ? PINNED_RULES_HASH
        : 'tampered_rules_hash_8f990172ba9a';

    const envelope: Envelope = {
      callId: `call_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`,
      tenantId,
      surfaceId,
      capability,
      actionType,
      isOnline,
      lease,
      compiledContextHash,
      idempotencyKey,
      rulesHash,
      payload: parsedPayload,
      evidenceDigest,
    };

    setLastEnvelope(envelope);

    // Dispatch through CONSULT harness (with simulated upstream gateway fallback)
    const result = await broker.dispatch(envelope, async () => {
      return {
        executed: true,
        capability,
        surfaceId,
        tenantId,
        timestamp: Date.now(),
        verifiedSha: 'cd17573',
      };
    });

    setLastResult(result);
    setIsExecuting(false);

    if (result.admitted) {
      if (result.receipt) {
        onReceiptIssued(result.receipt);
      }
      if (result.queued) {
        onQueueUpdated();
      }
    }
  };

  const copyReceiptJson = () => {
    if (lastResult?.admitted && lastResult.receipt) {
      navigator.clipboard.writeText(JSON.stringify(lastResult.receipt, null, 2));
      setCopiedReceipt(true);
      setTimeout(() => setCopiedReceipt(false), 2000);
    }
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <div className="flex items-center space-x-2">
            <Layers className="h-5 w-5 text-cyan-400" />
            <h2 className="text-base font-semibold text-white">
              Interactive Admission Broker & Capability Dispatch Sandbox
            </h2>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Construct envelopes, test admission gates across disconnected surfaces, and inspect durable tenant-scoped receipts.
          </p>
        </div>

        {/* Preset quick buttons */}
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="text-[11px] text-slate-400 mr-1 font-medium">Presets:</span>
          <button
            onClick={() => applyPreset('pr_sync')}
            className={`px-2.5 py-1 text-xs rounded-lg font-medium transition-all ${
              selectedPreset === 'pr_sync'
                ? 'bg-cyan-600 text-white shadow-md shadow-cyan-900/50'
                : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
            }`}
          >
            Online PR Sync
          </button>
          <button
            onClick={() => applyPreset('offline_launch')}
            className={`px-2.5 py-1 text-xs rounded-lg font-medium transition-all ${
              selectedPreset === 'offline_launch'
                ? 'bg-emerald-600 text-white shadow-md shadow-emerald-900/50'
                : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
            }`}
            title="node_protocol.json:19 allowlisted action 'launch'"
          >
            Offline 'launch' (Allowed)
          </button>
          <button
            onClick={() => applyPreset('offline_drift')}
            className={`px-2.5 py-1 text-xs rounded-lg font-medium transition-all ${
              selectedPreset === 'offline_drift'
                ? 'bg-rose-600 text-white shadow-md shadow-rose-900/50'
                : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
            }`}
            title="Unallowlisted action 'mobile.sync_draft' (Refused)"
          >
            Offline 'sync_draft' (Refused)
          </button>
          <button
            onClick={() => applyPreset('unsafe_deploy')}
            className={`px-2.5 py-1 text-xs rounded-lg font-medium transition-all ${
              selectedPreset === 'unsafe_deploy'
                ? 'bg-cyan-600 text-white shadow-md shadow-cyan-900/50'
                : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
            }`}
          >
            Offline Unsafe Deploy
          </button>
          <button
            onClick={() => applyPreset('unknown_capability')}
            className={`px-2.5 py-1 text-xs rounded-lg font-medium transition-all ${
              selectedPreset === 'unknown_capability'
                ? 'bg-cyan-600 text-white shadow-md shadow-cyan-900/50'
                : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
            }`}
          >
            Unknown Capability
          </button>
        </div>
      </div>

      {/* Grid: Form Controls (Left) and Admission Execution & Receipt Output (Right) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Envelope Configuration Form */}
        <div className="lg:col-span-7 space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {/* Tenant ID */}
            <div>
              <label htmlFor="tenant-input" className="block text-xs font-medium text-slate-300 mb-1">Tenant ID (Durable Scope)</label>
              <input
                id="tenant-input"
                type="text"
                value={tenantId}
                onChange={(e) => setTenantId(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-cyan-500 font-mono"
              />
            </div>

            {/* Surface Selector */}
            <div>
              <label htmlFor="surface-select" className="block text-xs font-medium text-slate-300 mb-1">Target Surface</label>
              <select
                id="surface-select"
                value={surfaceId}
                onChange={(e) => setSurfaceId(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-cyan-500 font-mono"
              >
                <option value="mac_session_460567726510256">Mac Session (genesis-control-plane)</option>
                <option value="argon_genesis_cluster">Argon Genesis (Dagster Cluster)</option>
                <option value="mobile_node_ios_client">Mobile Node (iOS/Android Client)</option>
                <option value="ci_worker_runner_01">CI Worker Runner (MUM-298 Gate)</option>
              </select>
            </div>

            {/* Capability Name */}
            <div>
              <label htmlFor="capability-input" className="block text-xs font-medium text-slate-300 mb-1">Capability</label>
              <input
                id="capability-input"
                type="text"
                value={capability}
                onChange={(e) => setCapability(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-cyan-500 font-mono"
                placeholder="e.g. launch, git.pr_sync"
              />
            </div>

            {/* Action Type */}
            <div>
              <label htmlFor="action-type-select" className="block text-xs font-medium text-slate-300 mb-1">Action Type</label>
              <select
                id="action-type-select"
                value={actionType}
                onChange={(e) => setActionType(e.target.value as ActionType)}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-cyan-500 font-mono"
              >
                <option value="mutation">mutation (Standard State Change)</option>
                <option value="safe_mutation">safe_mutation (Offline Allowed if in Allowlist)</option>
                <option value="unsafe_mutation">unsafe_mutation (Cluster Consensus Required)</option>
                <option value="read">read (Idempotent Query)</option>
              </select>
            </div>

            {/* Lease Option */}
            <div>
              <label htmlFor="lease-option-select" className="block text-xs font-medium text-slate-300 mb-1">Lease Token</label>
              <select
                id="lease-option-select"
                value={leaseOption}
                onChange={(e) => setLeaseOption(e.target.value as 'valid' | 'expired' | 'none')}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-cyan-500 font-mono"
              >
                <option value="valid">Valid Active Lease (1h TTL)</option>
                <option value="expired">Expired Lease (Violates Gate)</option>
                <option value="none">No Lease Token (Null)</option>
              </select>
            </div>

            {/* Compiled Context Hash Option */}
            <div>
              <label htmlFor="ctx-hash-select" className="block text-xs font-medium text-slate-300 mb-1">Compiled Context Hash</label>
              <select
                id="ctx-hash-select"
                value={contextHashOption}
                onChange={(e) => setContextHashOption(e.target.value as 'valid' | 'missing')}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-cyan-500 font-mono"
              >
                <option value="valid">Valid Compiled Hash (f148e711...)</option>
                <option value="missing">Empty / Missing (Violates Gate)</option>
              </select>
            </div>
          </div>

          {/* Idempotency Key & Evidence Digest */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <div className="flex items-center justify-between mb-1">
                <label htmlFor="idempotency-input" className="text-xs font-medium text-slate-300">Idempotency Key (Durable Store)</label>
                <button
                  type="button"
                  onClick={() => setIdempotencyKey(`idem_${Date.now()}`)}
                  className="text-[10px] text-cyan-400 hover:text-cyan-300 font-mono"
                >
                  Regenerate
                </button>
              </div>
              <input
                id="idempotency-input"
                type="text"
                value={idempotencyKey}
                onChange={(e) => setIdempotencyKey(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-cyan-500 font-mono"
              />
            </div>
            <div>
              <label htmlFor="evidence-digest-input" className="block text-xs font-medium text-slate-300 mb-1">Evidence Digest</label>
              <input
                id="evidence-digest-input"
                type="text"
                value={evidenceDigest}
                onChange={(e) => setEvidenceDigest(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-cyan-500 font-mono"
              />
            </div>
          </div>

          {/* Payload textarea */}
          <div>
            <label htmlFor="payload-textarea" className="block text-xs font-medium text-slate-300 mb-1">JSON Payload</label>
            <textarea
              id="payload-textarea"
              rows={3}
              value={payloadText}
              onChange={(e) => setPayloadText(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-xs text-slate-300 font-mono focus:outline-none focus:border-cyan-500 resize-none"
            />
          </div>

          {/* Dispatch Button */}
          <button
            onClick={handleDispatch}
            disabled={isExecuting}
            className="w-full flex items-center justify-center space-x-2 py-2.5 px-4 rounded-xl bg-gradient-to-r from-cyan-600 via-blue-600 to-indigo-600 hover:from-cyan-500 hover:to-indigo-500 text-white font-semibold text-xs shadow-lg shadow-cyan-950/50 transition-all disabled:opacity-50"
          >
            <Send className="h-4 w-4" />
            <span>Dispatch Envelope to IDP Broker Harness</span>
          </button>
        </div>

        {/* Admission Pipeline Execution & Verdict Output */}
        <div className="lg:col-span-5 flex flex-col justify-between space-y-4 bg-slate-950 rounded-xl p-4 border border-slate-800">
          <div>
            <div className="flex items-center justify-between pb-3 border-b border-slate-800/80">
              <span className="text-xs font-semibold text-slate-300">Admission Verdict & Receipt</span>
              {lastResult ? (
                lastResult.admitted ? (
                  <span className="px-2 py-0.5 rounded-full bg-emerald-950 text-emerald-400 border border-emerald-800 text-[11px] font-bold font-mono">
                    {lastResult.queued ? 'ADMITTED (QUEUED)' : lastResult.cached ? 'ADMITTED (CACHED REPLAY)' : 'ADMITTED'}
                  </span>
                ) : (
                  <span className="px-2 py-0.5 rounded-full bg-rose-950 text-rose-400 border border-rose-800 text-[11px] font-bold font-mono">
                    REFUSED ({lastResult.code})
                  </span>
                )
              ) : (
                <span className="text-[11px] text-slate-400 font-mono">Awaiting Dispatch</span>
              )}
            </div>

            {/* Verdict Details */}
            {lastResult ? (
              <div className="mt-4 space-y-3">
                {lastResult.admitted ? (
                  <div className="space-y-3">
                    <div className="p-3 rounded-lg bg-emerald-950/30 border border-emerald-800/50 text-emerald-300 text-xs">
                      <div className="flex items-center space-x-2 font-medium">
                        <ShieldCheck className="h-4 w-4 text-emerald-400 flex-shrink-0" />
                        <span>Admission Granted &bull; Capability Dispatch Executed</span>
                      </div>
                      <p className="text-[11px] text-emerald-400/80 mt-1">
                        All contract invariants verified. Zero-call check passed on refusals.
                      </p>
                    </div>

                    {/* Receipt Presence Box */}
                    {lastResult.receipt && (
                      <div className="bg-slate-900 rounded-lg p-3 border border-slate-800 text-xs space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="text-slate-400 font-medium flex items-center space-x-1.5">
                            <FileCheck2 className="h-4 w-4 text-cyan-400" />
                            <span>Receipt Presence Record</span>
                          </span>
                          <button
                            onClick={copyReceiptJson}
                            className="text-slate-400 hover:text-white transition-colors p-1"
                            title="Copy Receipt JSON"
                          >
                            {copiedReceipt ? (
                              <Check className="h-3.5 w-3.5 text-emerald-400" />
                            ) : (
                              <Copy className="h-3.5 w-3.5" />
                            )}
                          </button>
                        </div>
                        <div className="font-mono text-[11px] space-y-1 text-slate-300 bg-slate-950 p-2.5 rounded border border-slate-800/80">
                          <div><span className="text-slate-400">Receipt ID:</span> <span className="text-cyan-400">{lastResult.receipt.receiptId}</span></div>
                          <div><span className="text-slate-400">Tenant ID:</span> <span className="text-amber-300">{lastResult.receipt.tenantId}</span></div>
                          <div><span className="text-slate-400">Issuer:</span> {lastResult.receipt.issuer}</div>
                          <div><span className="text-slate-400">Digest:</span> <span className="text-indigo-400">{lastResult.receipt.digest}</span></div>
                          <div><span className="text-slate-400">Rules Hash:</span> <span className="text-slate-400">{lastResult.receipt.rulesHash.slice(0, 16)}...</span></div>
                          <div><span className="text-slate-400">Signature:</span> <span className="text-emerald-400">{lastResult.receipt.signatureAlgorithm || 'HMAC-SHA256'}</span> ({lastResult.receipt.signature ? lastResult.receipt.signature.slice(0, 16) + '...' : 'none'})</div>
                          <div><span className="text-slate-400">Key ID:</span> <span className="text-cyan-300">{lastResult.receipt.keyId || 'canonical_key'}</span></div>
                        </div>
                      </div>
                    )}

                    {/* Queued notification */}
                    {lastResult.queued && (
                      <div className="p-3 rounded-lg bg-amber-950/30 border border-amber-800/50 text-amber-300 text-xs font-mono">
                        <div className="flex items-center space-x-2">
                          <Clock className="h-4 w-4 text-amber-400" />
                          <span>Action enqueued in mobile offline journal</span>
                        </div>
                        <p className="text-[11px] text-amber-400/80 mt-1">
                          Canonical safe action queued without lease per node_protocol.json:19.
                        </p>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="p-3.5 rounded-lg bg-rose-950/40 border border-rose-800/60 text-rose-300 text-xs space-y-2">
                    <div className="flex items-center space-x-2 font-semibold">
                      <ShieldAlert className="h-4 w-4 text-rose-400 flex-shrink-0" />
                      <span>Admission Refused: {lastResult.code}</span>
                    </div>
                    <p className="text-[11px] text-rose-200 leading-relaxed">
                      {lastResult.reason}
                    </p>
                    <div className="pt-1 text-[11px] text-rose-400 font-mono">
                      &bull; Invariant enforced: Capability handler was NOT executed.
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="h-48 flex flex-col items-center justify-center text-center text-slate-400 space-y-2">
                <ShieldCheck className="h-8 w-8 text-slate-700" />
                <span className="text-xs">Select parameters and click "Dispatch Envelope" to run admission pipeline</span>
              </div>
            )}
          </div>

          {/* Envelope Summary Footer */}
          {lastEnvelope && (
            <div className="pt-3 border-t border-slate-800/80 text-[11px] text-slate-400 font-mono">
              Call ID: {lastEnvelope.callId} &bull; Tenant: {lastEnvelope.tenantId} &bull; Surface: {lastEnvelope.surfaceId}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
