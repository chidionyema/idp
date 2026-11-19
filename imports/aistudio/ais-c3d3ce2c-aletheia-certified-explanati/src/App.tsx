/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { useState } from 'react';
import { TopBar, type ActiveWorkspace } from './components/TopBar';
import { MeridianFlagshipView } from './components/MeridianFlagshipView';
import { DofGovernanceView } from './components/DofGovernanceView';
import { HumanProseEngineView } from './components/HumanProseEngineView';
import { RecordInspectorView } from './components/RecordInspectorView';
import { RecordCompilerView } from './components/RecordCompilerView';
import { MathematicalFoundationsView } from './components/MathematicalFoundationsView';
import { INITIAL_SCENARIOS } from './core/scenarios';
import type { ExplanationRecordInput } from './core/epistemicCalculus';

export default function App() {
  const [records, setRecords] = useState<ExplanationRecordInput[]>(INITIAL_SCENARIOS);
  const [selectedRecordId, setSelectedRecordId] = useState<string>('REC-2026-UGC-001');
  const [activeWorkspace, setActiveWorkspace] = useState<ActiveWorkspace>('flagship');
  const [compilerTemplate, setCompilerTemplate] = useState<ExplanationRecordInput>(
    INITIAL_SCENARIOS[0]
  );

  const handleSelectWorkspace = (workspace: ActiveWorkspace) => {
    setActiveWorkspace(workspace);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleOpenCompilerWithTemplate = (template: ExplanationRecordInput) => {
    setCompilerTemplate(template);
    setActiveWorkspace('compiler');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleCommitRecord = (newRecord: ExplanationRecordInput) => {
    setRecords((prev) => [newRecord, ...prev.filter((r) => r.id !== newRecord.id)]);
    setSelectedRecordId(newRecord.id);
    setActiveWorkspace('inspector');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleNavigateToInspector = (recordId?: string) => {
    if (recordId) {
      setSelectedRecordId(recordId);
    }
    setActiveWorkspace('inspector');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const isPublicSite = activeWorkspace === 'flagship';

  return (
    <div
      className={`min-h-screen flex flex-col ${
        isPublicSite
          ? 'bg-[#FBF9F5] text-[#141413]'
          : 'bg-[#07090E] text-slate-100'
      }`}
    >
      <TopBar
        activeWorkspace={activeWorkspace}
        onSelectWorkspace={handleSelectWorkspace}
        corpusCount={records.length}
      />

      <main className="flex-1">
        {activeWorkspace === 'flagship' && (
          <MeridianFlagshipView
            records={records}
            onNavigateToInspector={handleNavigateToInspector}
            onNavigateToProseEngine={() => handleSelectWorkspace('prose-engine')}
            onNavigateToCompiler={() => handleSelectWorkspace('compiler')}
          />
        )}

        {activeWorkspace === 'dof-governance' && (
          <DofGovernanceView
            onInspectDofRecord={() => handleNavigateToInspector('REC-2026-DOF-005')}
          />
        )}

        {activeWorkspace === 'prose-engine' && (
          <HumanProseEngineView
            onNavigateToFlagship={() => handleSelectWorkspace('flagship')}
          />
        )}

        {activeWorkspace === 'inspector' && (
          <RecordInspectorView
            records={records}
            selectedRecordId={selectedRecordId}
            onSelectRecordId={setSelectedRecordId}
            onOpenCompilerWithTemplate={handleOpenCompilerWithTemplate}
          />
        )}

        {activeWorkspace === 'compiler' && (
          <RecordCompilerView
            initialTemplate={compilerTemplate}
            existingIds={records.map((r) => r.id)}
            onCommitRecord={handleCommitRecord}
          />
        )}

        {(activeWorkspace === 'foundations' || activeWorkspace === 'strategy') && (
          <MathematicalFoundationsView
            mode={activeWorkspace}
            onSwitchToInspector={() => handleSelectWorkspace('inspector')}
          />
        )}
      </main>

      {isPublicSite ? (
        <footer className="border-t border-[#E2DDD5] bg-[#FBF9F5] px-6 sm:px-10 py-10 text-xs text-[#6E6A63]">
          <div className="max-w-5xl mx-auto flex flex-col sm:flex-row items-start sm:items-center justify-between gap-6">
            <div className="space-y-1">
              <div className="font-serif-editorial text-base text-[#141413]">
                Meridian Intelligence
              </div>
              <div className="text-xs text-[#6E6A63]">
                Applied AI Interpretability Research &amp; Four-Layer Explanation Records
              </div>
            </div>
            <div className="flex flex-wrap items-center gap-6">
              <a href="#the-premise" className="hover:text-[#141413] transition-colors">
                The Premise
              </a>
              <a href="#the-stack" className="hover:text-[#141413] transition-colors">
                The Four Layers
              </a>
              <a
                href="#explanation-record"
                className="hover:text-[#141413] transition-colors"
              >
                The Record
              </a>
              <a
                href="#open-weights"
                className="hover:text-[#141413] transition-colors"
              >
                Honest Limits
              </a>
              <button
                type="button"
                onClick={() => handleSelectWorkspace('inspector')}
                className="hover:text-[#141413] transition-colors cursor-pointer"
              >
                Research Workbench
              </button>
              <button
                type="button"
                onClick={() => handleSelectWorkspace('dof-governance')}
                className="hover:text-[#141413] transition-colors cursor-pointer"
              >
                Genesis &amp; IDP
              </button>
            </div>
          </div>
        </footer>
      ) : (
        <footer className="border-t border-slate-800 bg-[#090D16] px-6 py-4 text-xs font-mono text-slate-400 flex flex-col sm:flex-row items-center justify-between gap-2">
          <div>
            Meridian Verification Workbench · Genesis Rule Zero (GEN-DOF-001) · IDP History Ledger
          </div>
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => handleSelectWorkspace('inspector')}
              className="hover:text-slate-200 transition-colors cursor-pointer"
            >
              Record Inspector
            </button>
            <span aria-hidden="true">·</span>
            <button
              type="button"
              onClick={() => handleSelectWorkspace('prose-engine')}
              className="hover:text-slate-200 transition-colors cursor-pointer"
            >
              Prose Gate
            </button>
            <span aria-hidden="true">·</span>
            <button
              type="button"
              onClick={() => handleSelectWorkspace('dof-governance')}
              className="hover:text-slate-200 transition-colors cursor-pointer"
            >
              Genesis &amp; IDP (DoF-v1)
            </button>
            <span aria-hidden="true">·</span>
            <button
              type="button"
              onClick={() => handleSelectWorkspace('flagship')}
              className="text-cyan-300 hover:text-cyan-200 transition-colors cursor-pointer"
            >
              ← Meridian Public Site
            </button>
          </div>
        </footer>
      )}
    </div>
  );
}
