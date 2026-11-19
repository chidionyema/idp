/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useMemo } from 'react';
import {
  ShieldCheck,
  FlaskConical,
  Layers,
  Network,
  TrendingDown,
  Scale,
  FileCheck2,
  Smartphone,
  ExternalLink,
  Code2,
  Compass,
} from 'lucide-react';
import { Header } from './components/Header';
import { EstateRecoveryDashboard } from './components/EstateRecoveryDashboard';
import { ProtocolTestRunner } from './components/ProtocolTestRunner';
import { CapabilitySandbox } from './components/CapabilitySandbox';
import { DisconnectedSurfacesView } from './components/DisconnectedSurfacesView';
import { DeliveryFrictionAnalytics } from './components/DeliveryFrictionAnalytics';
import { GovernanceMatrix } from './components/GovernanceMatrix';
import { ReceiptLedgerView } from './components/ReceiptLedgerView';
import { OfflineQueueView } from './components/OfflineQueueView';
import { IdpGatewayClientHarness } from './protocol/broker';
import { Receipt } from './protocol/types';
import { PINNED_RULES_HASH } from './protocol/rules';
import { signReceipt, CANONICAL_ISSUER_KEY_ID } from './protocol/crypto';

export default function App() {
  const [activeTab, setActiveTab] = useState<
    'recovery' | 'invariants' | 'sandbox' | 'surfaces' | 'telemetry' | 'governance' | 'receipts' | 'offline'
  >('recovery');

  const [isOnline, setIsOnline] = useState<boolean>(true);

  // Client Harness instance
  const broker = useMemo(() => new IdpGatewayClientHarness(), []);

  // Pre-seed receipt ledger with initial sample receipts signed via HMAC-SHA256
  const [receipts, setReceipts] = useState<Receipt[]>(() => {
    const r1Base: Omit<Receipt, 'signature'> = {
      receiptId: 'rcpt_1730974550_99a',
      callId: 'call_gcp_001',
      idempotencyKey: 'idem_key_git_pr_sync_001',
      actionType: 'mutation',
      surfaceId: 'argon_genesis_cluster',
      tenantId: 'tenant_estate_primary',
      issuedAt: Date.now() - 300000,
      compiledContextHash: 'sha256:ctx_f148e711b391f47a6d79061e9970593070d49f3f19947ef9094c9055759abf2d',
      rulesHash: PINNED_RULES_HASH,
      digest: 'sha256:8b9f012aa9e843cd29b1',
      issuer: 'Argon Genesis (Cluster IDP Gateway)',
      keyId: CANONICAL_ISSUER_KEY_ID,
      signatureAlgorithm: 'HMAC-SHA256',
    };
    const sig1 = signReceipt(r1Base);

    const r2Base: Omit<Receipt, 'signature'> = {
      receiptId: 'rcpt_1730974800_21f',
      callId: 'call_ci_005',
      idempotencyKey: 'idem_contract_verify_002',
      actionType: 'mutation',
      surfaceId: 'ci_worker_runner_01',
      tenantId: 'tenant_estate_primary',
      issuedAt: Date.now() - 60000,
      compiledContextHash: 'sha256:ctx_f148e711b391f47a6d79061e9970593070d49f3f19947ef9094c9055759abf2d',
      rulesHash: PINNED_RULES_HASH,
      digest: 'sha256:cd17573e8992ba0911fe',
      issuer: 'Argon Genesis (Cluster IDP Gateway)',
      keyId: CANONICAL_ISSUER_KEY_ID,
      signatureAlgorithm: 'HMAC-SHA256',
    };
    const sig2 = signReceipt(r2Base);

    return [
      { ...r1Base, signature: sig1.signature },
      { ...r2Base, signature: sig2.signature },
    ];
  });

  const [offlineQueueItems, setOfflineQueueItems] = useState(broker.getOfflineQueue());

  const handleReceiptIssued = (newReceipt: Receipt) => {
    setReceipts((prev) => [newReceipt, ...prev]);
  };

  const handleQueueUpdated = () => {
    setOfflineQueueItems(broker.getOfflineQueue());
  };

  const handleFlushQueue = async () => {
    const queue = broker.getOfflineQueue();
    for (const item of queue) {
      await broker.dispatch(
        {
          ...item.envelope,
          isOnline: true,
          actionType: 'mutation',
          lease: {
            token: `lease_reconnected_${Math.random().toString(36).slice(2, 8)}`,
            surfaceId: item.envelope.surfaceId,
            grantedAt: Date.now(),
            expiresAt: Date.now() + 3600000,
            scope: [item.envelope.capability],
          },
          compiledContextHash: 'sha256:ctx_f148e711b391f47a6d79061e9970593070d49f3f19947ef9094c9055759abf2d',
          idempotencyKey: `idem_flushed_${item.id}`,
        },
        async () => ({ flushed: true, originalCallId: item.envelope.callId })
      );
    }
    broker.clearOfflineQueue();
    handleQueueUpdated();
    setReceipts(broker.getReceiptLedger());
  };

  const handleClearQueue = () => {
    broker.clearOfflineQueue();
    handleQueueUpdated();
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-cyan-500/30 selection:text-cyan-200">
      {/* Global Header */}
      <Header
        isOnline={isOnline}
        setIsOnline={setIsOnline}
        activeReceiptCount={receipts.length}
        queuedCount={offlineQueueItems.length}
      />

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
        {/* Navigation Tabs */}
        <div className="flex overflow-x-auto pb-1 gap-2 border-b border-slate-800 scrollbar-none">
          <button
            onClick={() => setActiveTab('recovery')}
            className={`flex items-center space-x-2 px-3.5 py-2.5 rounded-xl text-xs font-semibold whitespace-nowrap transition-all ${
              activeTab === 'recovery'
                ? 'bg-cyan-950/80 text-cyan-300 border border-cyan-800/80 shadow-md shadow-cyan-950/50'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900 border border-transparent'
            }`}
          >
            <Compass className="h-4 w-4 text-cyan-400" />
            <span>Estate Recovery Audit (24h Plan & 9 Contracts)</span>
          </button>

          <button
            onClick={() => setActiveTab('invariants')}
            className={`flex items-center space-x-2 px-3.5 py-2.5 rounded-xl text-xs font-semibold whitespace-nowrap transition-all ${
              activeTab === 'invariants'
                ? 'bg-cyan-950/80 text-cyan-300 border border-cyan-800/80 shadow-md shadow-cyan-950/50'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900 border border-transparent'
            }`}
          >
            <FlaskConical className="h-4 w-4" />
            <span>Contract Fixtures (12 Proven)</span>
          </button>

          <button
            onClick={() => setActiveTab('sandbox')}
            className={`flex items-center space-x-2 px-3.5 py-2.5 rounded-xl text-xs font-semibold whitespace-nowrap transition-all ${
              activeTab === 'sandbox'
                ? 'bg-cyan-950/80 text-cyan-300 border border-cyan-800/80 shadow-md shadow-cyan-950/50'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900 border border-transparent'
            }`}
          >
            <Layers className="h-4 w-4" />
            <span>Admission Sandbox & Dispatch</span>
          </button>

          <button
            onClick={() => setActiveTab('surfaces')}
            className={`flex items-center space-x-2 px-3.5 py-2.5 rounded-xl text-xs font-semibold whitespace-nowrap transition-all ${
              activeTab === 'surfaces'
                ? 'bg-cyan-950/80 text-cyan-300 border border-cyan-800/80 shadow-md shadow-cyan-950/50'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900 border border-transparent'
            }`}
          >
            <Network className="h-4 w-4" />
            <span>Disconnected Surfaces Matrix</span>
          </button>

          <button
            onClick={() => setActiveTab('telemetry')}
            className={`flex items-center space-x-2 px-3.5 py-2.5 rounded-xl text-xs font-semibold whitespace-nowrap transition-all ${
              activeTab === 'telemetry'
                ? 'bg-cyan-950/80 text-cyan-300 border border-cyan-800/80 shadow-md shadow-cyan-950/50'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900 border border-transparent'
            }`}
          >
            <TrendingDown className="h-4 w-4" />
            <span>Delivery Friction (MUM-300)</span>
          </button>

          <button
            onClick={() => setActiveTab('governance')}
            className={`flex items-center space-x-2 px-3.5 py-2.5 rounded-xl text-xs font-semibold whitespace-nowrap transition-all ${
              activeTab === 'governance'
                ? 'bg-cyan-950/80 text-cyan-300 border border-cyan-800/80 shadow-md shadow-cyan-950/50'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900 border border-transparent'
            }`}
          >
            <Scale className="h-4 w-4" />
            <span>9 Governance Clauses</span>
          </button>

          <button
            onClick={() => setActiveTab('receipts')}
            className={`flex items-center space-x-2 px-3.5 py-2.5 rounded-xl text-xs font-semibold whitespace-nowrap transition-all ${
              activeTab === 'receipts'
                ? 'bg-cyan-950/80 text-cyan-300 border border-cyan-800/80 shadow-md shadow-cyan-950/50'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900 border border-transparent'
            }`}
          >
            <FileCheck2 className="h-4 w-4" />
            <span>Receipt Ledger ({receipts.length})</span>
          </button>

          <button
            onClick={() => setActiveTab('offline')}
            className={`flex items-center space-x-2 px-3.5 py-2.5 rounded-xl text-xs font-semibold whitespace-nowrap transition-all ${
              activeTab === 'offline'
                ? 'bg-cyan-950/80 text-cyan-300 border border-cyan-800/80 shadow-md shadow-cyan-950/50'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900 border border-transparent'
            }`}
          >
            <Smartphone className="h-4 w-4" />
            <span>Offline Journal ({offlineQueueItems.length})</span>
          </button>
        </div>

        {/* Tab View Routing */}
        {activeTab === 'recovery' && <EstateRecoveryDashboard />}

        {activeTab === 'invariants' && <ProtocolTestRunner />}

        {activeTab === 'sandbox' && (
          <CapabilitySandbox
            broker={broker}
            isOnline={isOnline}
            onReceiptIssued={handleReceiptIssued}
            onQueueUpdated={handleQueueUpdated}
          />
        )}

        {activeTab === 'surfaces' && <DisconnectedSurfacesView />}

        {activeTab === 'telemetry' && <DeliveryFrictionAnalytics />}

        {activeTab === 'governance' && <GovernanceMatrix />}

        {activeTab === 'receipts' && <ReceiptLedgerView receipts={receipts} />}

        {activeTab === 'offline' && (
          <OfflineQueueView
            queue={offlineQueueItems}
            isOnline={isOnline}
            onFlushQueue={handleFlushQueue}
            onClearQueue={handleClearQueue}
          />
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-900 bg-slate-950 py-4 text-center text-xs text-slate-500 font-mono">
        <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-2">
          <span>CONSULT Observability & Assurance Interface &bull; Upstream Mandate: IDP #7771 / #7790</span>
          <span>Rules Consensus: 18e3ccdaee2a0cce... &bull; Production Execution via Governed Action Doors</span>
        </div>
      </footer>
    </div>
  );
}
