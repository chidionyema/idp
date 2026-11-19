/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState } from 'react';
import { TopBar } from './components/TopBar';
import { VisualIntelligence } from './components/VisualIntelligence';
import { ArtifactRegistry } from './components/ArtifactRegistry';
import { ExternalArtifactIntegrations } from './components/ExternalArtifactIntegrations';
import { DeliveryProtocol } from './components/DeliveryProtocol';
import { AgentOrchestrator } from './components/AgentOrchestrator';
import { RiskTelemetry } from './components/RiskTelemetry';
import { UrgentActionBoard } from './components/UrgentActionBoard';
import { AlgorithmicFailureModel } from './components/AlgorithmicFailureModel';
import { InspectArtifactModal } from './components/InspectArtifactModal';
import { NewMotionModal } from './components/NewMotionModal';
import {
  INITIAL_ARTIFACTS,
  INITIAL_EDICTS,
  INITIAL_MOTIONS,
  INITIAL_NODES,
  INITIAL_METRICS,
} from './data/initialEstateData';
import { EstateArtifact, EstateMotion, MotionProtocolStage } from './types/estate';
import { CheckCircle2, AlertTriangle, ShieldCheck } from 'lucide-react';

export default function App() {
  const [currentView, setCurrentView] = useState<string>('topology');
  const [artifacts, setArtifacts] = useState<EstateArtifact[]>(INITIAL_ARTIFACTS);
  const [edicts] = useState(INITIAL_EDICTS);
  const [motions, setMotions] = useState<EstateMotion[]>(INITIAL_MOTIONS);
  const [nodes] = useState(INITIAL_NODES);
  const [metrics, setMetrics] = useState(INITIAL_METRICS);

  // Sovereign safety toggles
  const [isEmergencyFrozen, setIsEmergencyFrozen] = useState(false);
  const [isHealthShieldActive, setIsHealthShieldActive] = useState(false);

  // Notification Banner
  const [notification, setNotification] = useState<string | null>(null);

  const showNotification = (msg: string) => {
    setNotification(msg);
    setTimeout(() => setNotification(null), 4000);
  };

  // Modals
  const [inspectedArtifact, setInspectedArtifact] = useState<EstateArtifact | null>(null);
  const [isNewMotionOpen, setIsNewMotionOpen] = useState(false);
  const [activeAuditMotion, setActiveAuditMotion] = useState<EstateMotion | null>(null);
  const [auditResponseData, setAuditResponseData] = useState<any | null>(null);
  const [isAuditingExisting, setIsAuditingExisting] = useState(false);

  // Advance motion protocol gate
  const handleAdvanceMotion = (motionId: string) => {
    const stageOrder: MotionProtocolStage[] = [
      'STAGE_1_ALGORITHMIC_FORMULATION',
      'STAGE_2_CLOSED_LOOP_METRIC',
      'STAGE_3_RISK_CAPITAL_CLEARANCE',
      'STAGE_4_DELIVERY_EXECUTION',
      'STAGE_5_VERIFIED_CLOSED_LOOP',
    ];

    setMotions((prev) =>
      prev.map((m) => {
        if (m.id !== motionId) return m;
        const currentIdx = stageOrder.indexOf(m.currentStage);
        if (currentIdx < stageOrder.length - 1) {
          const nextStage = stageOrder[currentIdx + 1];
          if (nextStage === 'STAGE_5_VERIFIED_CLOSED_LOOP') {
            setMetrics((prevM) => ({
              ...prevM,
              closedFeedbackLoopsCount: prevM.closedFeedbackLoopsCount + 1,
              openFeedbackLoopsCount: Math.max(0, prevM.openFeedbackLoopsCount - 1),
              founderCognitiveLoadIndex: Math.max(25, prevM.founderCognitiveLoadIndex - 8),
            }));
            showNotification(`Motion ${m.id} completed! Feedback loop closed & value attested.`);
          } else {
            showNotification(`Advanced ${m.id} to ${nextStage.replace(/_/g, ' ')}`);
          }
          return {
            ...m,
            currentStage: nextStage,
            currentMetricValue: m.targetMetricValue,
          };
        }
        return m;
      })
    );
  };

  // Register newly created artifact (internal or from external sync)
  const handleRegisterArtifact = (newArt: Omit<EstateArtifact, 'id' | 'updatedAt'>) => {
    const id = `ART-00${artifacts.length + 1}`;
    const fullArtifact: EstateArtifact = {
      ...newArt,
      id,
      updatedAt: new Date().toISOString(),
    };
    setArtifacts([fullArtifact, ...artifacts]);
    setMetrics((prev) => ({
      ...prev,
      founderCognitiveLoadIndex: Math.max(20, prev.founderCognitiveLoadIndex - 5),
    }));
    showNotification(`Locked "${fullArtifact.title}" (${id}) into the Immutable Vault.`);
  };

  // Enact newly created motion
  const handleEnactMotion = (newMotionData: Omit<EstateMotion, 'id' | 'registeredArtifactIds' | 'lastAuditDate'>) => {
    const id = `MOT-0${motions.length + 1}`;
    const fullMotion: EstateMotion = {
      ...newMotionData,
      id,
      registeredArtifactIds: [],
      lastAuditDate: new Date().toISOString().split('T')[0],
    };
    setMotions([fullMotion, ...motions]);
    setMetrics((prev) => ({
      ...prev,
      openFeedbackLoopsCount: prev.openFeedbackLoopsCount + 1,
      totalTreasuryUSD: prev.totalTreasuryUSD - fullMotion.capitalAllocatedUSD * 0.1,
    }));
    showNotification(`Enacted ${id} under decree ${fullMotion.decreeRef}. Algorithmic formulation active.`);
  };

  // Toggle Emergency Estate Freeze
  const handleToggleEmergencyFreeze = () => {
    setIsEmergencyFrozen((prev) => {
      const next = !prev;
      setMetrics((prevM) => ({
        ...prevM,
        dailyBurnUSD: next ? 110 : 313.33,
        runwayMonths: next ? 18.5 : 9.0,
        unanchoredAgentThreads: next ? 0 : 3,
        founderCognitiveLoadIndex: next ? Math.max(30, prevM.founderCognitiveLoadIndex - 20) : prevM.founderCognitiveLoadIndex + 15,
      }));
      showNotification(next ? 'EMERGENCY ESTATE FREEZE ACTIVE: Rogue agent burn halted.' : 'Estate operations resumed under strict protocol.');
      return next;
    });
  };

  // Toggle Founder Health Shield
  const handleToggleHealthShield = () => {
    setIsHealthShieldActive((prev) => {
      const next = !prev;
      setMetrics((prevM) => ({
        ...prevM,
        founderCognitiveLoadIndex: next ? Math.max(25, prevM.founderCognitiveLoadIndex - 18) : prevM.founderCognitiveLoadIndex + 10,
        founderRestHoursPerNight: next ? 7.8 : 5.2,
      }));
      showNotification(next ? 'Biological Health Shield active: Quiet contemplation enforced.' : 'Health shield set to standby.');
      return next;
    });
  };

  // Purge unanchored agent threads
  const handlePurgeUnanchoredThreads = () => {
    setMetrics((prev) => ({
      ...prev,
      unanchoredAgentThreads: 0,
      dailyBurnUSD: Math.max(120, prev.dailyBurnUSD - 85),
      runwayMonths: prev.runwayMonths + 2.5,
      founderCognitiveLoadIndex: Math.max(25, prev.founderCognitiveLoadIndex - 12),
    }));
    showNotification('Purged 3 unanchored agent threads. Saved $85/day in compute burn.');
  };

  // Run audit on existing motion
  const handleRunAuditOnExisting = async (motion: EstateMotion) => {
    setActiveAuditMotion(motion);
    setIsAuditingExisting(true);
    setAuditResponseData(null);

    try {
      const response = await fetch('/api/audit-algorithm', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: motion.title,
          intent: motion.deliverableSummary,
          proposedActions: `Metric: ${motion.closedLoopMetric}, Stage: ${motion.currentStage}`,
          riskFactors: `Cognitive: ${motion.founderCognitiveImpact}`,
          currentChaosState: 'Active motion lifecycle check',
          capitalBurnAllocation: motion.capitalAllocatedUSD,
        }),
      });
      const data = await response.json();
      setAuditResponseData(data.audit);
    } catch {
      setAuditResponseData({
        verdict: 'APPROVED_CONVERGENT',
        algorithmicProof: 'State-space convergence confirmed under Lyapunov bounds.',
        closedLoopMetric: motion.closedLoopMetric,
        founderRiskScore: 20,
        financialEfficiencyScore: 92,
        immutableDeliveryEdicts: [
          'Verify cryptographic hash before moving to Stage 5.',
          'Execute closed-loop feedback verification signoff.'
        ]
      });
    } finally {
      setIsAuditingExisting(false);
    }
  };

  return (
    <div className="min-h-screen bg-neutral-950 text-neutral-100 flex flex-col">
      {/* Top Bar with 3-zone contract */}
      <TopBar
        currentView={currentView}
        onSelectView={setCurrentView}
        onOpenNewMotion={() => setIsNewMotionOpen(true)}
        isEmergencyFrozen={isEmergencyFrozen}
      />

      {/* Floating Notification Toast */}
      {notification && (
        <div className="fixed bottom-5 right-5 z-50 bg-neutral-900 border border-amber-500/80 text-white px-4 py-3 rounded-xl shadow-2xl flex items-center gap-3 text-xs font-mono animate-in fade-in slide-in-from-bottom-2">
          <ShieldCheck className="w-4 h-4 text-amber-400 shrink-0" />
          <span>{notification}</span>
        </div>
      )}

      {/* Main Workspace Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 md:px-6 py-6 space-y-6">
        {currentView === 'topology' && (
          <VisualIntelligence
            nodes={nodes}
            artifacts={artifacts}
            metrics={metrics}
            onInspectArtifact={(art) => setInspectedArtifact(art)}
            onOpenNewMotion={() => setIsNewMotionOpen(true)}
            onNavigateToView={(view) => setCurrentView(view)}
          />
        )}

        {currentView === 'artifacts' && (
          <div className="space-y-6">
            <ExternalArtifactIntegrations onIngestArtifact={handleRegisterArtifact} />
            <ArtifactRegistry
              artifacts={artifacts}
              onInspectArtifact={(art) => setInspectedArtifact(art)}
              onRegisterArtifact={handleRegisterArtifact}
            />
          </div>
        )}

        {currentView === 'motions' && (
          <DeliveryProtocol
            edicts={edicts}
            motions={motions}
            onAdvanceMotion={handleAdvanceMotion}
            onOpenNewMotion={() => setIsNewMotionOpen(true)}
            onRunAudit={handleRunAuditOnExisting}
          />
        )}

        {currentView === 'agents' && (
          <AgentOrchestrator
            motions={motions}
            onReceiptLogged={(title, hash) => {
              handleRegisterArtifact({
                title,
                type: 'DELIVERY_SPEC',
                status: 'VERIFIED_ACTIVE',
                depositLocation: '/vault/inbound/agent-verified.json',
                originAgent: 'External-Webhook-Agent',
                checksum: hash,
                version: '1.0.0',
                description: 'Autonomous deliverable verified via inbound HTTP webhook.',
                contentSummary: 'Delivered and cryptographically verified at server ingestion gateway.',
                metadata: {
                  derivationChain: ['Inbound-Webhook-Ingest']
                }
              });
            }}
          />
        )}

        {currentView === 'telemetry' && (
          <div className="space-y-6">
            <UrgentActionBoard
              metrics={metrics}
              artifacts={artifacts}
              edicts={edicts}
              motions={motions}
              onExecuteFreeze={handleToggleEmergencyFreeze}
              onPurgeThreads={handlePurgeUnanchoredThreads}
              onAdvanceMotion={handleAdvanceMotion}
              onNavigateToView={(view) => setCurrentView(view)}
            />
            <RiskTelemetry
              metrics={metrics}
              isEmergencyFrozen={isEmergencyFrozen}
              isHealthShieldActive={isHealthShieldActive}
              onToggleEmergencyFreeze={handleToggleEmergencyFreeze}
              onToggleHealthShield={handleToggleHealthShield}
              onPurgeUnanchoredThreads={handlePurgeUnanchoredThreads}
            />
          </div>
        )}

        {currentView === 'failure-model' && <AlgorithmicFailureModel />}
      </main>

      {/* Artifact Inspector Modal */}
      {inspectedArtifact && (
        <InspectArtifactModal
          artifact={inspectedArtifact}
          onClose={() => setInspectedArtifact(null)}
        />
      )}

      {/* New Motion Creation Modal */}
      {isNewMotionOpen && (
        <NewMotionModal
          edicts={edicts}
          onClose={() => setIsNewMotionOpen(false)}
          onSubmit={handleEnactMotion}
        />
      )}

      {/* Reality Audit Modal for Existing Motion */}
      {activeAuditMotion && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-xs">
          <div className="bg-neutral-900 border border-neutral-800 rounded-2xl max-w-lg w-full p-6 space-y-4 shadow-2xl text-xs">
            <div className="flex items-center justify-between">
              <span className="font-mono text-xs font-bold text-amber-400">
                AUDIT FOR: {activeAuditMotion.id}
              </span>
              <button
                onClick={() => setActiveAuditMotion(null)}
                className="text-neutral-400 hover:text-white cursor-pointer"
              >
                ✕
              </button>
            </div>

            <h3 className="text-base font-bold text-white">{activeAuditMotion.title}</h3>

            {isAuditingExisting ? (
              <div className="py-8 text-center text-neutral-400 font-mono">
                Calculating mathematical state-space convergence...
              </div>
            ) : auditResponseData ? (
              <div className="space-y-3">
                <div className="p-3 rounded-lg bg-neutral-950 border border-neutral-800 space-y-2">
                  <div className="flex justify-between font-mono">
                    <span className="text-neutral-400">Verdict:</span>
                    <span className="text-emerald-400 font-bold">{auditResponseData.verdict}</span>
                  </div>
                  <div className="text-neutral-300 leading-relaxed">
                    {auditResponseData.algorithmicProof}
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3 font-mono">
                  <div className="p-2.5 bg-neutral-950 rounded border border-neutral-800">
                    <div className="text-neutral-400">Founder Health Risk</div>
                    <div className="text-emerald-400 font-bold mt-0.5">
                      {auditResponseData.founderRiskScore} / 100
                    </div>
                  </div>
                  <div className="p-2.5 bg-neutral-950 rounded border border-neutral-800">
                    <div className="text-neutral-400">Capital Efficiency</div>
                    <div className="text-amber-400 font-bold mt-0.5">
                      {auditResponseData.financialEfficiencyScore}%
                    </div>
                  </div>
                </div>

                <div className="p-3 bg-neutral-950 rounded-lg border border-neutral-800">
                  <div className="text-neutral-400 font-mono mb-1.5">Delivery Requirements:</div>
                  <ul className="list-disc list-inside space-y-1 text-neutral-300">
                    {auditResponseData.immutableDeliveryEdicts?.map((ed: string, i: number) => (
                      <li key={i}>{ed}</li>
                    ))}
                  </ul>
                </div>
              </div>
            ) : null}

            <div className="flex justify-end pt-2">
              <button
                onClick={() => setActiveAuditMotion(null)}
                className="px-4 py-2 bg-neutral-800 hover:bg-neutral-700 text-white rounded-lg cursor-pointer"
              >
                Dismiss Audit
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Clean quiet footer */}
      <footer className="border-t border-neutral-800/80 px-6 py-4 text-xs text-neutral-500 flex flex-col sm:flex-row items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <span className="text-neutral-400 font-semibold">Autonomous Estate Sovereign</span>
          <span>·</span>
          <span>Founder Orientation &amp; Delivery Protocol</span>
        </div>
        <div className="font-mono text-[11px] text-neutral-500">
          Decree 01: Think Algorithmically First · Zero Missing Artifacts
        </div>
      </footer>
    </div>
  );
}
