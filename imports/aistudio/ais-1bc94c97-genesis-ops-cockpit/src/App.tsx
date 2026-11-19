import React, { useState } from 'react';
import { Header } from './components/Header';
import { VoiceBar } from './components/VoiceBar';
import { LegionGrid } from './components/LegionGrid';
import { LegionDetailModal } from './components/LegionDetailModal';
import { ExtractiveLabTab } from './components/ExtractiveLabTab';
import { TelegramSpoolerTab } from './components/TelegramSpoolerTab';
import { ReceiptLedgerTab } from './components/ReceiptLedgerTab';
import { DofGateModal } from './components/DofGateModal';
import { ReceiptVerificationModal } from './components/ReceiptVerificationModal';
import {
  INITIAL_LEGIONS,
  INITIAL_BRIEFS,
  INITIAL_TELEGRAM_NOTES,
  INITIAL_TELEMETRY,
} from './data/mockLegions';
import { Legion, SpokenBrief, TelegramVoiceNote, EstateTelemetry } from './types';
import { audioEngine } from './utils/audioEngine';

export default function App() {
  const [telemetry, setTelemetry] = useState<EstateTelemetry>(INITIAL_TELEMETRY);
  const [legions, setLegions] = useState<Legion[]>(INITIAL_LEGIONS);
  const [briefs, setBriefs] = useState<Record<string, SpokenBrief>>(INITIAL_BRIEFS);
  const [telegramNotes, setTelegramNotes] = useState<TelegramVoiceNote[]>(INITIAL_TELEGRAM_NOTES);
  const [activeTab, setActiveTab] = useState<'cockpit' | 'lab' | 'telegram' | 'ledger'>('cockpit');

  // Currently loaded brief in bottom Voice Bar
  const [activeBrief, setActiveBrief] = useState<SpokenBrief | null>(INITIAL_BRIEFS['brief-alpha']);

  // Gemini Enrichment Toggle & Spend Meter
  const [geminiEnrichmentEnabled, setGeminiEnrichmentEnabled] = useState<boolean>(false);
  const [totalModelSpendUsd, setTotalModelSpendUsd] = useState<number>(0.0);
  const [totalTokensEnriched, setTotalTokensEnriched] = useState<number>(0);

  // Modals & Drawers
  const [selectedTriageBrief, setSelectedTriageBrief] = useState<SpokenBrief | null>(null);
  const [selectedReceiptBrief, setSelectedReceiptBrief] = useState<SpokenBrief | null>(null);
  const [isDofGateModalOpen, setIsDofGateModalOpen] = useState<boolean>(false);

  // Notifications / Toast
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3000);
  };

  // 1-Click Founder Action Approval
  const handleApproveFounderAction = (briefId: string, actionId: string) => {
    setBriefs((prev) => {
      const target = prev[briefId];
      if (!target) return prev;

      const updatedActions = target.sections.needsFounder.map((a) =>
        a.id === actionId
          ? { ...a, status: 'approved' as const, resolvedAt: new Date().toISOString() }
          : a
      );

      const updatedBrief: SpokenBrief = {
        ...target,
        sections: {
          ...target.sections,
          needsFounder: updatedActions,
        },
      };

      if (selectedTriageBrief?.id === briefId) {
        setSelectedTriageBrief(updatedBrief);
      }
      if (activeBrief?.id === briefId) {
        setActiveBrief(updatedBrief);
      }

      return {
        ...prev,
        [briefId]: updatedBrief,
      };
    });

    audioEngine.playTacticalCue('action');
    showToast('Founder action approved & dispatched to legion spooler!');
  };

  // Reopen DOF-Gate
  const handleUnblockDofGate = () => {
    setTelemetry((prev) => ({
      ...prev,
      dofGate: {
        status: 'UNBLOCKED_MERGING',
        queueCount: 0,
        nextInQueue: 'None (All Lanes Merging)',
      },
    }));

    // Update Legions Alpha & Gamma status
    setLegions((prev) =>
      prev.map((l) => {
        if (l.id === 'legion-alpha') {
          return { ...l, status: 'active', statusLabel: 'PR #412 Merged & Active' };
        }
        if (l.id === 'legion-gamma') {
          return { ...l, status: 'active', statusLabel: 'Voice Bar Live' };
        }
        if (l.id === 'legion-epsilon') {
          return { ...l, status: 'active', statusLabel: 'Gate Credential Rotated' };
        }
        return l;
      })
    );

    showToast('DOF-Gate unblocked! PR #412 (Piper ARM VM) and PR #415 (Voice Bar) promoted to main.');
  };

  // Push Brief to Telegram Spooler
  const handleSendToTelegram = (brief: SpokenBrief) => {
    const newNote: TelegramVoiceNote = {
      id: `tg-${Date.now()}`,
      legionId: brief.legionId,
      legionName: brief.legionName,
      voiceFileSha256: brief.sha256Receipt,
      durationSec: brief.recordedDurationSec,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      isHeard: false,
      deliveredStatus: 'delivered',
      spoolerLatencyMs: 110,
      summarySnippet: brief.spokenScript.slice(0, 110) + '...',
      spokenScript: brief.spokenScript,
      survivesDeadSession: true,
    };

    setTelegramNotes((prev) => [newNote, ...prev]);
    audioEngine.playTacticalCue('open');
    showToast(`Voice brief spooled to Telegram via genesis-host-spooler!`);
  };

  // Founder voice memo response from Telegram
  const handleSendFounderVoiceMemo = (text: string) => {
    showToast('Founder voice directive dispatched to legion ring buffer!');
  };

  // Spend Tracking
  const handleSpendIncurred = (usd: number, tokens: number) => {
    setTotalModelSpendUsd((prev) => prev + usd);
    setTotalTokensEnriched((prev) => prev + tokens);
  };

  return (
    <div className="min-h-screen bg-[#090d16] text-zinc-100 flex flex-col font-sans selection:bg-sky-500/30 selection:text-sky-200">
      {/* Toast Notification */}
      {toastMessage && (
        <div className="fixed top-16 left-1/2 -translate-x-1/2 z-50 px-4 py-2 rounded-xl bg-zinc-900 border border-emerald-500/50 text-emerald-300 text-xs font-mono shadow-2xl flex items-center gap-2 animate-bounce">
          <span className="h-2 w-2 rounded-full bg-emerald-400" />
          <span>{toastMessage}</span>
        </div>
      )}

      {/* Header */}
      <Header
        telemetry={telemetry}
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        geminiEnrichmentEnabled={geminiEnrichmentEnabled}
        setGeminiEnrichmentEnabled={setGeminiEnrichmentEnabled}
        totalModelSpendUsd={totalModelSpendUsd}
        totalTokensEnriched={totalTokensEnriched}
        onOpenDofGateModal={() => setIsDofGateModalOpen(true)}
      />

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 pb-28">
        {activeTab === 'cockpit' && (
          <LegionGrid
            legions={legions}
            briefs={briefs}
            activeBriefId={activeBrief?.id || null}
            onSelectLegionBrief={(brief) => setActiveBrief(brief)}
            onOpenTriage={(brief) => setSelectedTriageBrief(brief)}
            onOpenReceipt={(brief) => setSelectedReceiptBrief(brief)}
            geminiEnrichmentEnabled={geminiEnrichmentEnabled}
          />
        )}

        {activeTab === 'lab' && (
          <ExtractiveLabTab
            onLoadBriefIntoVoiceBar={(brief) => setActiveBrief(brief)}
            onSendToTelegram={handleSendToTelegram}
            geminiEnrichmentEnabled={geminiEnrichmentEnabled}
            setGeminiEnrichmentEnabled={setGeminiEnrichmentEnabled}
            onSpendIncurred={handleSpendIncurred}
          />
        )}

        {activeTab === 'telegram' && (
          <TelegramSpoolerTab
            voiceNotes={telegramNotes}
            onPlayVoiceNote={(note) => {
              const matchedBrief = Object.values(briefs).find((b) => b.sha256Receipt === note.voiceFileSha256);
              if (matchedBrief) {
                setActiveBrief(matchedBrief);
              }
            }}
            onSendFounderVoiceMemo={handleSendFounderVoiceMemo}
          />
        )}

        {activeTab === 'ledger' && (
          <ReceiptLedgerTab
            briefs={Object.values(briefs)}
            onPlayBrief={(brief) => setActiveBrief(brief)}
          />
        )}
      </main>

      {/* Bottom Pinned Voice Bar */}
      <VoiceBar
        currentBrief={activeBrief}
        onOpenReceiptModal={(b) => setSelectedReceiptBrief(b)}
        onOpenTriageDrawer={(b) => setSelectedTriageBrief(b)}
        geminiEnrichmentActive={geminiEnrichmentEnabled}
      />

      {/* Founder Triage & Action Drawer Modal */}
      {selectedTriageBrief && (
        <LegionDetailModal
          brief={selectedTriageBrief}
          onClose={() => setSelectedTriageBrief(null)}
          onApproveFounderAction={handleApproveFounderAction}
          onSendToTelegram={handleSendToTelegram}
          geminiEnrichmentEnabled={geminiEnrichmentEnabled}
        />
      )}

      {/* Cryptographic Receipt Verification Modal */}
      {selectedReceiptBrief && (
        <ReceiptVerificationModal
          brief={selectedReceiptBrief}
          onClose={() => setSelectedReceiptBrief(null)}
        />
      )}

      {/* DOF-Gate Status & Unblock Modal */}
      <DofGateModal
        telemetry={telemetry}
        isOpen={isDofGateModalOpen}
        onClose={() => setIsDofGateModalOpen(false)}
        onUnblockGate={handleUnblockDofGate}
      />
    </div>
  );
}
