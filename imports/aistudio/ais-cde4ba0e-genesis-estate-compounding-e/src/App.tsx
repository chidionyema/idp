/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState } from 'react';
import { TopNav, ActiveTab } from './components/TopNav.tsx';
import { AlienCeoVisualSurface } from './components/AlienCeoVisualSurface.tsx';
import { FlowStateAndFprpSurface } from './components/FlowStateAndFprpSurface.tsx';
import { InstructionPocketNetworkSurface } from './components/InstructionPocketNetworkSurface.tsx';
import { CdoLoopSurface } from './components/CdoLoopSurface.tsx';
import { KeyLoanAndGuardrailSurface } from './components/KeyLoanAndGuardrailSurface.tsx';
import { ScienceLaneAndHistoryBridge } from './components/ScienceLaneAndHistoryBridge.tsx';
import { CompoundingEngineeringSurface } from './components/CompoundingEngineeringSurface.tsx';
import { FounderCockpit } from './components/FounderCockpit.tsx';
import { RealTimeAuditMonitor } from './components/RealTimeAuditMonitor.tsx';
import { TripartiteCockpit } from './components/TripartiteCockpit.tsx';
import { FleetReviewChamber } from './components/FleetReviewChamber.tsx';
import { CommandCodeSurface } from './components/CommandCodeSurface.tsx';
import { ArgonSyncModal } from './components/ArgonSyncModal.tsx';
import { AlwaysOnAidesHub } from './components/AlwaysOnAidesHub.tsx';
import { FounderWelcomeExperience } from './components/FounderWelcomeExperience.tsx';
import { ShieldAlert, AlertTriangle, GitBranch, ArrowUpRight } from 'lucide-react';

export default function App() {
  const [activeTab, setActiveTab] = useState<ActiveTab>('alien-ceo');
  const [isEmergencyHalt, setIsEmergencyHalt] = useState<boolean>(false);
  const [founderObservationActive, setFounderObservationActive] = useState<boolean>(true);
  const [isSyncModalOpen, setIsSyncModalOpen] = useState<boolean>(false);
  const [isWelcomeOpen, setIsWelcomeOpen] = useState<boolean>(false);
  const [unpushedCount, setUnpushedCount] = useState<number>(1);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-cyan-500/20 selection:text-cyan-200">
      
      {/* Top Bar Contract (Strict 3-zone contract) */}
      <TopNav
        activeTab={activeTab}
        onTabChange={setActiveTab}
        onOpenSync={() => setIsSyncModalOpen(true)}
        onOpenWelcome={() => setIsWelcomeOpen(true)}
        isEmergencyHalt={isEmergencyHalt}
        unpushedCount={unpushedCount}
      />

      {/* Emergency Halt Banner when active */}
      {isEmergencyHalt && (
        <div className="bg-rose-950 border-b border-rose-800 text-rose-200 px-6 py-2.5 text-xs font-mono flex items-center justify-between">
          <div className="flex items-center gap-2 max-w-7xl mx-auto w-full">
            <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
            <span className="font-bold">FLEET-WIDE EMERGENCY STOP ENGAGED:</span>
            <span>All background tasks for otto, concierge, and science-lead halted in 1.84ms. Zero agent state mutations allowed.</span>
            <button
              onClick={() => setIsEmergencyHalt(false)}
              className="ml-auto underline underline-offset-2 hover:text-white font-bold cursor-pointer"
            >
              Resume Execution
            </button>
          </div>
        </div>
      )}

      {/* Observation Disabled Warning Banner */}
      {!founderObservationActive && !isEmergencyHalt && (
        <div className="bg-amber-950 border-b border-amber-800 text-amber-200 px-6 py-2.5 text-xs font-mono flex items-center justify-between">
          <div className="flex items-center gap-2 max-w-7xl mx-auto w-full">
            <ShieldAlert className="w-4 h-4 text-amber-400 shrink-0" />
            <span className="font-bold">FOUNDER OBSERVATION MUTED (§1.3):</span>
            <span>Zero autonomous execution permitted while observation is disabled. Task execution suspended.</span>
            <button
              onClick={() => setFounderObservationActive(true)}
              className="ml-auto underline underline-offset-2 hover:text-white font-bold cursor-pointer"
            >
              Restore Presence
            </button>
          </div>
        </div>
      )}

      {/* Main Viewport Content */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 py-8">
        {activeTab === 'alien-ceo' && (
          <AlienCeoVisualSurface
            onSelectPacket={() => setActiveTab('ipn')}
            onNavigateToLane={() => setActiveTab('audit')}
            onNavigateToFprp={() => setActiveTab('flow-fprp')}
          />
        )}
        {activeTab === 'ccp' && <CommandCodeSurface />}
        {activeTab === 'fleet-review' && <FleetReviewChamber />}
        {activeTab === 'tripartite' && <TripartiteCockpit />}
        {activeTab === 'flow-fprp' && <FlowStateAndFprpSurface />}
        {activeTab === 'ipn' && <InstructionPocketNetworkSurface />}
        {activeTab === 'cdo' && <CdoLoopSurface />}
        {activeTab === 'klp' && <KeyLoanAndGuardrailSurface />}
        {activeTab === 'science' && <ScienceLaneAndHistoryBridge />}
        {activeTab === 'compounding' && <CompoundingEngineeringSurface />}
        {activeTab === 'cockpit' && (
          <FounderCockpit
            isEmergencyHalt={isEmergencyHalt}
            onToggleEmergencyHalt={() => setIsEmergencyHalt(!isEmergencyHalt)}
            founderObservationActive={founderObservationActive}
            onToggleFounderObservation={() => setFounderObservationActive(!founderObservationActive)}
          />
        )}
        {activeTab === 'audit' && <RealTimeAuditMonitor />}
      </main>

      {/* Sovereign Footer */}
      <footer className="border-t border-slate-900 bg-slate-950/80 py-6 px-6 text-xs text-slate-500 font-mono">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <span className="text-slate-400 font-semibold">GENESIS ESTATE CANON</span>
            <span>·</span>
            <span>ERA_1 Release v1.0.26</span>
            <span>·</span>
            <span>2100 Alien CEO Standard Enforced</span>
          </div>

          <div className="flex items-center gap-4 text-slate-400">
            <button
              onClick={() => setIsSyncModalOpen(true)}
              className="hover:text-cyan-400 transition-colors flex items-center gap-1 cursor-pointer"
            >
              <GitBranch className="w-3.5 h-3.5" />
              <span>chidionyema/argon</span>
              <ArrowUpRight className="w-3 h-3" />
            </button>
            <span>Ed25519 Beacon: 0x8f2d...5a4</span>
          </div>
        </div>
      </footer>

      {/* Argon Sync Modal */}
      <ArgonSyncModal
        isOpen={isSyncModalOpen}
        onClose={() => {
          setIsSyncModalOpen(false);
          setUnpushedCount(0);
        }}
      />

      {/* Perpetual Founder Aide Triumvirate Floating HUD (Always on tap §12) */}
      <AlwaysOnAidesHub
        onOpenSync={() => setIsSyncModalOpen(true)}
        onOpenWelcome={() => setIsWelcomeOpen(true)}
        onOpenFleetCouncil={() => setActiveTab('fleet-review')}
        onOpenCcp={() => setActiveTab('ccp')}
        isEmergencyHalt={isEmergencyHalt}
      />

      {/* Founder Executive Welcome & Operations Guide */}
      <FounderWelcomeExperience
        isOpen={isWelcomeOpen}
        onClose={() => setIsWelcomeOpen(false)}
        onNavigateToTab={(tab) => {
          setActiveTab(tab);
          setIsWelcomeOpen(false);
        }}
        onOpenSync={() => {
          setIsWelcomeOpen(false);
          setIsSyncModalOpen(true);
        }}
      />
    </div>
  );
}
