import React, { useState } from 'react';
import {
  ArchitectureProposalRfc,
  ConsultantQuestion,
  IncidentRecord,
  RoadmapMilestone,
} from '../data/idpDomainData';
import {
  ArchitectureSimulationResult,
  generateConsultantBriefMarkdown,
} from '../utils/roadmapLogic';
import { Check, Copy, Download, FileText, Plus } from 'lucide-react';

interface ConsultantBriefViewProps {
  rfcs: ArchitectureProposalRfc[];
  incidents: IncidentRecord[];
  milestones: RoadmapMilestone[];
  questions: ConsultantQuestion[];
  simResult: ArchitectureSimulationResult;
  onToggleQuestion: (id: string) => void;
  onAddQuestion: (q: ConsultantQuestion) => void;
}

export const ConsultantBriefView: React.FC<ConsultantBriefViewProps> = ({
  rfcs,
  incidents,
  milestones,
  questions,
  simResult,
  onToggleQuestion,
  onAddQuestion,
}) => {
  const [consultantRoleTitle, setConsultantRoleTitle] = useState(
    'Principal Distributed Systems & Quantitative Reality-Research Architect'
  );
  const [engagementWeeks, setEngagementWeeks] = useState<number>(6);
  const [founderNotes, setFounderNotes] = useState<string>(
    'Focus Weeks 1–2 strictly on locking the Apache Iceberg bitemporal spine (RFC-01) and RocksDB CSR snapshot concurrency model (RFC-02) so Horizon 1 engineering is unblocked immediately.'
  );
  const [copiedState, setCopiedState] = useState<boolean>(false);

  // Add custom consultant question form
  const [newDomain, setNewDomain] = useState('');
  const [newPriority, setNewPriority] =
    useState<ConsultantQuestion['priority']>('P1 — Architecture Sign-off');
  const [newQuestionText, setNewQuestionText] = useState('');
  const [newDeliverable, setNewDeliverable] = useState('');
  const [questionError, setQuestionError] = useState<string | null>(null);

  const briefMarkdown = generateConsultantBriefMarkdown({
    rfcs,
    incidents,
    milestones,
    questions,
    simResult,
    consultantRoleTitle,
    engagementWeeks,
    founderNotes,
  });

  const handleCopyMarkdown = async () => {
    try {
      await navigator.clipboard.writeText(briefMarkdown);
      setCopiedState(true);
      setTimeout(() => setCopiedState(false), 2500);
    } catch {
      setCopiedState(true);
      setTimeout(() => setCopiedState(false), 2500);
    }
  };

  const handleDownloadMarkdown = () => {
    const blob = new Blob([briefMarkdown], { type: 'text/markdown;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'IDP-Architecture-Consultant-Briefing-Dossier.md';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const handleAddQuestionSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (newDomain.trim().length < 3 || newQuestionText.trim().length < 10) {
      setQuestionError(
        'Please provide a valid architectural domain and a specific technical question (at least 10 characters).'
      );
      return;
    }

    const nextIdx = questions.length + 1;
    onAddQuestion({
      id: `CQ-0${nextIdx}`,
      domain: newDomain.trim(),
      priority: newPriority,
      question: newQuestionText.trim(),
      contextRef: 'Founder Custom Inquiry · Master Spec v3.4',
      expectedDeliverable:
        newDeliverable.trim() || 'Written architectural trade-off memo & reference prototype.',
      includedInBrief: true,
    });

    setNewDomain('');
    setNewQuestionText('');
    setNewDeliverable('');
    setQuestionError(null);
  };

  return (
    <div className="space-y-10">
      {/* Header */}
      <section className="border-b border-stone-200 pb-8 flex flex-col lg:flex-row lg:items-end justify-between gap-6">
        <div className="space-y-2 max-w-2xl">
          <div className="text-xs uppercase tracking-widest text-stone-500">
            External Consultant Engagement Package · SOW & Technical Context Dossier
          </div>
          <h1
            className="text-3xl sm:text-4xl font-display font-medium text-stone-900 leading-tight"
            style={{ textWrap: 'balance' }}
          >
            External Consultant Architecture Briefing & SOW Dossier
          </h1>
          <p className="text-sm text-stone-600 leading-relaxed">
            Synthesizes the Founder Vision, Master Spec invariants, recent production incident
            forensics, active RFC option selections, and prioritized technical review questions into
            a self-contained briefing package for external consultation.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3 self-start">
          <button
            type="button"
            onClick={handleCopyMarkdown}
            className="px-4 py-2.5 text-xs font-medium text-stone-900 bg-white border border-stone-300 hover:bg-stone-100 transition-colors flex items-center gap-2 cursor-pointer whitespace-nowrap"
          >
            {copiedState ? <Check className="w-4 h-4 text-emerald-800" /> : <Copy className="w-4 h-4" />}
            <span>{copiedState ? 'Copied Dossier Markdown' : 'Copy Brief Markdown'}</span>
          </button>

          <button
            type="button"
            onClick={handleDownloadMarkdown}
            className="px-4 py-2.5 text-xs font-medium text-white bg-stone-900 hover:bg-stone-800 transition-colors flex items-center gap-2 cursor-pointer whitespace-nowrap"
          >
            <Download className="w-4 h-4" />
            <span>Download .MD Dossier</span>
          </button>
        </div>
      </section>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Left 6 Cols: Engagement Configuration & Prioritized Questions Checklist */}
        <div className="lg:col-span-6 space-y-8">
          {/* Engagement Parameters */}
          <div className="bg-white border border-stone-200 p-6 space-y-4">
            <h2 className="text-lg font-display font-medium text-stone-900 border-b border-stone-200 pb-3">
              01. Consultant Engagement Scope & Founder Directives
            </h2>

            <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
              <div className="sm:col-span-3">
                <label
                  htmlFor="consultant-role"
                  className="block text-xs font-medium text-stone-700 mb-1"
                >
                  Target Consultant Profile
                </label>
                <input
                  id="consultant-role"
                  type="text"
                  value={consultantRoleTitle}
                  onChange={(e) => setConsultantRoleTitle(e.target.value)}
                  className="w-full px-3 py-2 text-xs bg-stone-50 border border-stone-300 text-stone-900"
                />
              </div>

              <div>
                <label
                  htmlFor="engagement-weeks"
                  className="block text-xs font-medium text-stone-700 mb-1"
                >
                  SOW Duration (Wks)
                </label>
                <input
                  id="engagement-weeks"
                  type="number"
                  min={1}
                  max={24}
                  value={engagementWeeks}
                  onChange={(e) => setEngagementWeeks(Number(e.target.value) || 6)}
                  className="w-full px-3 py-2 text-xs bg-stone-50 border border-stone-300 text-stone-900 font-mono"
                />
              </div>
            </div>

            <div>
              <label
                htmlFor="founder-notes"
                className="block text-xs font-medium text-stone-700 mb-1"
              >
                Executive Briefing Notes & Non-Negotiable Constraints
              </label>
              <textarea
                id="founder-notes"
                rows={3}
                value={founderNotes}
                onChange={(e) => setFounderNotes(e.target.value)}
                className="w-full px-3 py-2 text-xs bg-stone-50 border border-stone-300 text-stone-900 leading-relaxed"
              />
            </div>
          </div>

          {/* Technical Review Agenda Checklist */}
          <div className="bg-white border border-stone-200 p-6 space-y-5">
            <div className="border-b border-stone-200 pb-3 flex items-center justify-between">
              <h2 className="text-lg font-display font-medium text-stone-900">
                02. Technical Review Questions & SOW Deliverables
              </h2>
              <span className="text-xs font-mono text-stone-500">
                {questions.filter((q) => q.includedInBrief).length} of {questions.length} included
              </span>
            </div>

            <div className="divide-y divide-stone-200">
              {questions.map((q) => (
                <div key={q.id} className="py-4 first:pt-0 last:pb-0 space-y-2">
                  <div className="flex items-start justify-between gap-3">
                    <label className="flex items-start gap-2.5 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={q.includedInBrief}
                        onChange={() => onToggleQuestion(q.id)}
                        className="mt-1 accent-stone-900 cursor-pointer"
                      />
                      <div>
                        <div className="text-xs font-mono text-stone-500">
                          {q.id} · {q.priority} · {q.contextRef}
                        </div>
                        <div className="text-sm font-semibold text-stone-900 mt-0.5">
                          {q.domain}
                        </div>
                      </div>
                    </label>
                  </div>

                  <p className="text-xs text-stone-700 leading-relaxed pl-6">{q.question}</p>
                  <div className="text-xs text-stone-500 pl-6">
                    <span className="font-medium text-stone-800">Required Deliverable: </span>
                    {q.expectedDeliverable}
                  </div>
                </div>
              ))}
            </div>

            {/* Append Custom Consultant Question */}
            <form
              onSubmit={handleAddQuestionSubmit}
              className="border-t border-stone-200 pt-5 space-y-3"
            >
              <div className="text-xs font-semibold uppercase tracking-wider text-stone-600 flex items-center gap-1.5">
                <Plus className="w-3.5 h-3.5" />
                <span>Add Custom Question for External Consultant</span>
              </div>

              {questionError && (
                <div
                  role="alert"
                  className="p-2.5 bg-red-50 border border-red-200 text-xs text-red-900"
                >
                  {questionError}
                </div>
              )}

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label htmlFor="cq-domain" className="block text-xs text-stone-600 mb-1">
                    Domain / Subsystem
                  </label>
                  <input
                    id="cq-domain"
                    type="text"
                    value={newDomain}
                    onChange={(e) => setNewDomain(e.target.value)}
                    placeholder="e.g. Zero-Copy Arrow IPC Serialization"
                    className="w-full px-3 py-1.5 text-xs bg-stone-50 border border-stone-300 text-stone-900"
                  />
                </div>
                <div>
                  <label htmlFor="cq-priority" className="block text-xs text-stone-600 mb-1">
                    Priority Level
                  </label>
                  <select
                    id="cq-priority"
                    value={newPriority}
                    onChange={(e) =>
                      setNewPriority(e.target.value as ConsultantQuestion['priority'])
                    }
                    className="w-full px-3 py-1.5 text-xs bg-stone-50 border border-stone-300 text-stone-900"
                  >
                    <option value="P0 — Blocking H1">P0 — Blocking H1</option>
                    <option value="P1 — Architecture Sign-off">P1 — Architecture Sign-off</option>
                    <option value="P2 — Optimization">P2 — Optimization</option>
                  </select>
                </div>
              </div>

              <div>
                <label htmlFor="cq-text" className="block text-xs text-stone-600 mb-1">
                  Technical Inquiry
                </label>
                <textarea
                  id="cq-text"
                  rows={2}
                  value={newQuestionText}
                  onChange={(e) => setNewQuestionText(e.target.value)}
                  placeholder="Specify the exact architectural trade-off or failure mode for consultant review..."
                  className="w-full px-3 py-1.5 text-xs bg-stone-50 border border-stone-300 text-stone-900"
                />
              </div>

              <div className="flex items-center justify-between gap-3">
                <input
                  type="text"
                  aria-label="Expected Deliverable"
                  value={newDeliverable}
                  onChange={(e) => setNewDeliverable(e.target.value)}
                  placeholder="Expected deliverable (e.g. Benchmark + ADR sign-off)"
                  className="flex-1 px-3 py-1.5 text-xs bg-stone-50 border border-stone-300 text-stone-900"
                />
                <button
                  type="submit"
                  className="px-3.5 py-1.5 text-xs font-medium text-white bg-stone-900 hover:bg-stone-800 cursor-pointer whitespace-nowrap"
                >
                  Append Question
                </button>
              </div>
            </form>
          </div>
        </div>

        {/* Right 6 Cols: Live Compiled Markdown Dossier Preview */}
        <div className="lg:col-span-6 bg-white border border-stone-200 p-6 space-y-4 lg:sticky lg:top-6">
          <div className="border-b border-stone-200 pb-3 flex items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              <FileText className="w-4 h-4 text-stone-700 shrink-0" />
              <h2 className="text-base font-display font-medium text-stone-900">
                Compiled External Consultant Briefing Dossier
              </h2>
            </div>
            <span className="text-xs font-mono text-stone-500 whitespace-nowrap shrink-0">
              Markdown Export Ready
            </span>
          </div>

          <pre
            data-testid="consultant-dossier-preview"
            className="p-4 bg-stone-950 text-stone-100 font-mono text-xs leading-relaxed overflow-x-auto max-h-[680px] overflow-y-auto whitespace-pre-wrap"
          >
            {briefMarkdown}
          </pre>
        </div>
      </div>
    </div>
  );
};
