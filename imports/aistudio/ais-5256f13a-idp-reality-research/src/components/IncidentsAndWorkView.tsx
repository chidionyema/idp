import React, { useState } from 'react';
import {
  ArchitecturalPlane,
  IncidentRecord,
  REPO_MODULE_SPECS,
} from '../data/idpDomainData';
import { validateNewIncidentInput } from '../utils/roadmapLogic';
import { AlertTriangle, Plus, ShieldAlert } from 'lucide-react';

interface IncidentsAndWorkViewProps {
  incidents: IncidentRecord[];
  initialModuleFilter?: string;
  onAddIncident: (newInc: IncidentRecord) => void;
  onSelectRfc: (rfcId: string) => void;
  onSelectLane: (laneId: string) => void;
}

const RFC_TO_LANE: Record<string, string> = {
  'RFC-01': 'LANE-02',
  'RFC-02': 'LANE-03',
  'RFC-03': 'LANE-04',
  'RFC-04': 'LANE-01',
  'RFC-05': 'LANE-04',
};

export const IncidentsAndWorkView: React.FC<IncidentsAndWorkViewProps> = ({
  incidents,
  initialModuleFilter = '',
  onAddIncident,
  onSelectRfc,
  onSelectLane,
}) => {
  const [moduleFilter, setModuleFilter] = useState<string>(initialModuleFilter);
  const [severityFilter, setSeverityFilter] = useState<string>('ALL');
  const [showNewForm, setShowNewForm] = useState<boolean>(false);

  // New incident form state
  const [title, setTitle] = useState('');
  const [severity, setSeverity] = useState<IncidentRecord['severity']>('High');
  const [plane, setPlane] = useState<ArchitecturalPlane>('Ingestion & Sensorium');
  const [affectedModule, setAffectedModule] = useState('packages/epistemic-intake');
  const [blastRadiusMetric, setBlastRadiusMetric] = useState('');
  const [rootCause, setRootCause] = useState('');
  const [immediateMitigation, setImmediateMitigation] = useState('');
  const [linkedRfcId, setLinkedRfcId] = useState('RFC-01');
  const [formError, setFormError] = useState<string | null>(null);

  React.useEffect(() => {
    if (initialModuleFilter) {
      setModuleFilter(initialModuleFilter);
    }
  }, [initialModuleFilter]);

  const filteredIncidents = incidents.filter((inc) => {
    if (moduleFilter && inc.affectedModule !== moduleFilter) return false;
    if (severityFilter !== 'ALL' && inc.severity !== severityFilter) return false;
    return true;
  });

  const handleSubmitIncident = (e: React.FormEvent) => {
    e.preventDefault();
    const validation = validateNewIncidentInput({
      title,
      affectedModule,
      rootCause,
      blastRadiusMetric,
    });
    if (!validation.valid) {
      setFormError(validation.error || 'Please fill in all required fields.');
      return;
    }

    const nextNum = 112 + incidents.length;
    const newRecord: IncidentRecord = {
      id: `INC-2026-${nextNum}`,
      date: '2026-10-29',
      title: title.trim(),
      severity,
      plane,
      affectedModule,
      status: 'Active Bottleneck',
      blastRadiusMetric: blastRadiusMetric.trim(),
      rootCause: rootCause.trim(),
      immediateMitigation:
        immediateMitigation.trim() ||
        'Manual circuit-breaker applied pending consultant RFC review.',
      linkedRfcId,
      linkedMilestoneIds: ['MS-H1-01'],
    };

    onAddIncident(newRecord);
    setTitle('');
    setBlastRadiusMetric('');
    setRootCause('');
    setImmediateMitigation('');
    setFormError(null);
    setShowNewForm(false);
  };

  return (
    <div className="space-y-10">
      {/* Header */}
      <section className="border-b border-stone-200 pb-8 flex flex-col lg:flex-row lg:items-end justify-between gap-6">
        <div className="space-y-2 max-w-2xl">
          <div className="text-xs uppercase tracking-widest text-stone-500">
            Programme Forensics · Recent Work & Production Bottlenecks
          </div>
          <h1
            className="text-3xl sm:text-4xl font-display font-medium text-stone-900 leading-tight"
            style={{ textWrap: 'balance' }}
          >
            Recent Work Incidents & Epistemic Post-Mortem Ledger
          </h1>
          <p className="text-sm text-stone-600 leading-relaxed">
            Every architectural proposal in the IDP roadmap is grounded in empirical failure modes
            observed during recent high-velocity reality ingestion and historical simulation runs.
          </p>
        </div>

        <button
          type="button"
          onClick={() => setShowNewForm((prev) => !prev)}
          className="px-4 py-2.5 text-xs font-medium text-white bg-stone-900 hover:bg-stone-800 transition-colors flex items-center gap-2 self-start cursor-pointer whitespace-nowrap"
        >
          <Plus className="w-4 h-4" />
          <span>{showNewForm ? 'Close Incident Form' : 'Log New Incident / Bottleneck'}</span>
        </button>
      </section>

      {/* Optional Add Incident Form */}
      {showNewForm && (
        <section className="bg-white border border-stone-300 p-6 space-y-5">
          <div className="border-b border-stone-200 pb-3 flex items-center justify-between">
            <h2 className="text-lg font-display font-medium text-stone-900">
              Record Programme Incident or Architectural Bottleneck
            </h2>
            <span className="text-xs font-mono text-stone-500">Links directly to Consultant Dossier</span>
          </div>

          {formError && (
            <div
              role="alert"
              className="p-3 bg-red-50 border border-red-200 text-xs text-red-900 font-medium"
            >
              {formError}
            </div>
          )}

          <form onSubmit={handleSubmitIncident} className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div className="sm:col-span-2">
                <label
                  htmlFor="inc-title"
                  className="block text-xs font-medium text-stone-700 mb-1"
                >
                  Incident Title
                </label>
                <input
                  id="inc-title"
                  type="text"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="e.g. Late AIS Satellite Frame Watermark Drift"
                  className="w-full px-3 py-2 text-xs bg-stone-50 border border-stone-300 text-stone-900 focus:outline-none focus:border-stone-900"
                />
              </div>

              <div>
                <label
                  htmlFor="inc-severity"
                  className="block text-xs font-medium text-stone-700 mb-1"
                >
                  Severity Classification
                </label>
                <select
                  id="inc-severity"
                  value={severity}
                  onChange={(e) => setSeverity(e.target.value as IncidentRecord['severity'])}
                  className="w-full px-3 py-2 text-xs bg-stone-50 border border-stone-300 text-stone-900"
                >
                  <option value="Critical">Critical</option>
                  <option value="High">High</option>
                  <option value="Moderate">Moderate</option>
                </select>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div>
                <label
                  htmlFor="inc-module"
                  className="block text-xs font-medium text-stone-700 mb-1"
                >
                  Affected Repo Package
                </label>
                <select
                  id="inc-module"
                  value={affectedModule}
                  onChange={(e) => setAffectedModule(e.target.value)}
                  className="w-full px-3 py-2 text-xs bg-stone-50 border border-stone-300 text-stone-900 font-mono"
                >
                  {REPO_MODULE_SPECS.map((m) => (
                    <option key={m.id} value={m.path}>
                      {m.path}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label
                  htmlFor="inc-plane"
                  className="block text-xs font-medium text-stone-700 mb-1"
                >
                  Architectural Plane
                </label>
                <select
                  id="inc-plane"
                  value={plane}
                  onChange={(e) => setPlane(e.target.value as ArchitecturalPlane)}
                  className="w-full px-3 py-2 text-xs bg-stone-50 border border-stone-300 text-stone-900"
                >
                  <option value="Ingestion & Sensorium">Ingestion & Sensorium</option>
                  <option value="Bitemporal Ontology & Graph">Bitemporal Ontology & Graph</option>
                  <option value="Asymmetry & Falsification Engine">
                    Asymmetry & Falsification Engine
                  </option>
                  <option value="Convex Execution & Simulation">
                    Convex Execution & Simulation
                  </option>
                  <option value="Governance & Epistemic Audit">Governance & Epistemic Audit</option>
                </select>
              </div>

              <div>
                <label
                  htmlFor="inc-rfc"
                  className="block text-xs font-medium text-stone-700 mb-1"
                >
                  Linked Architecture Proposal
                </label>
                <select
                  id="inc-rfc"
                  value={linkedRfcId}
                  onChange={(e) => setLinkedRfcId(e.target.value)}
                  className="w-full px-3 py-2 text-xs bg-stone-50 border border-stone-300 text-stone-900 font-mono"
                >
                  <option value="RFC-01">RFC-01 (Bitemporal Spine)</option>
                  <option value="RFC-02">RFC-02 (Lock-Free Causal Graph)</option>
                  <option value="RFC-03">RFC-03 (Streaming Divergence)</option>
                  <option value="RFC-04">RFC-04 (Merkle Provenance)</option>
                  <option value="RFC-05">RFC-05 (Bayesian Falsification)</option>
                </select>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label
                  htmlFor="inc-blast"
                  className="block text-xs font-medium text-stone-700 mb-1"
                >
                  Quantitative Blast Radius Metric
                </label>
                <input
                  id="inc-blast"
                  type="text"
                  value={blastRadiusMetric}
                  onChange={(e) => setBlastRadiusMetric(e.target.value)}
                  placeholder="e.g. 38-min blindspot on 14 LNG vessel draught feeds"
                  className="w-full px-3 py-2 text-xs bg-stone-50 border border-stone-300 text-stone-900"
                />
              </div>

              <div>
                <label
                  htmlFor="inc-mitigation"
                  className="block text-xs font-medium text-stone-700 mb-1"
                >
                  Immediate Tactical Mitigation
                </label>
                <input
                  id="inc-mitigation"
                  type="text"
                  value={immediateMitigation}
                  onChange={(e) => setImmediateMitigation(e.target.value)}
                  placeholder="e.g. Increased watermark buffer to 120s"
                  className="w-full px-3 py-2 text-xs bg-stone-50 border border-stone-300 text-stone-900"
                />
              </div>
            </div>

            <div>
              <label
                htmlFor="inc-root-cause"
                className="block text-xs font-medium text-stone-700 mb-1"
              >
                Technical Root Cause Analysis
              </label>
              <textarea
                id="inc-root-cause"
                rows={2}
                value={rootCause}
                onChange={(e) => setRootCause(e.target.value)}
                placeholder="Describe the underlying systems or epistemic failure mechanism..."
                className="w-full px-3 py-2 text-xs bg-stone-50 border border-stone-300 text-stone-900"
              />
            </div>

            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={() => setShowNewForm(false)}
                className="px-4 py-2 text-xs font-medium text-stone-700 bg-stone-100 hover:bg-stone-200 cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="px-4 py-2 text-xs font-medium text-white bg-stone-900 hover:bg-stone-800 cursor-pointer"
              >
                Save Incident to Post-Mortem Ledger
              </button>
            </div>
          </form>
        </section>
      )}

      {/* Filter Bar */}
      <section className="flex flex-wrap items-center justify-between gap-4 bg-white border border-stone-200 p-4">
        <div className="flex flex-wrap items-center gap-4">
          <div className="flex items-center gap-2">
            <label htmlFor="mod-filter" className="text-xs font-medium text-stone-600">
              Module:
            </label>
            <select
              id="mod-filter"
              value={moduleFilter}
              onChange={(e) => setModuleFilter(e.target.value)}
              className="px-2.5 py-1.5 text-xs bg-stone-50 border border-stone-300 text-stone-900 font-mono"
            >
              <option value="">All Repository Packages</option>
              {REPO_MODULE_SPECS.map((m) => (
                <option key={m.id} value={m.path}>
                  {m.path}
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-center gap-2">
            <label htmlFor="sev-filter" className="text-xs font-medium text-stone-600">
              Severity:
            </label>
            <select
              id="sev-filter"
              value={severityFilter}
              onChange={(e) => setSeverityFilter(e.target.value)}
              className="px-2.5 py-1.5 text-xs bg-stone-50 border border-stone-300 text-stone-900"
            >
              <option value="ALL">All Severities</option>
              <option value="Critical">Critical</option>
              <option value="High">High</option>
              <option value="Moderate">Moderate</option>
            </select>
          </div>
        </div>

        <div className="text-xs font-mono text-stone-600 tabular-nums">
          Showing {filteredIncidents.length} of {incidents.length} recorded incidents
        </div>
      </section>

      {/* Incident Post-Mortem Cards */}
      <section className="space-y-6">
        {filteredIncidents.map((inc) => (
          <article key={inc.id} className="bg-white border border-stone-200 p-6 space-y-5">
            <div className="flex flex-wrap items-baseline justify-between gap-2 border-b border-stone-200 pb-4">
              <div className="space-y-1">
                <div className="flex flex-wrap items-center gap-2 text-xs font-mono text-stone-500">
                  <span className="font-semibold text-stone-900">{inc.id}</span>
                  <span aria-hidden="true">·</span>
                  <span>{inc.date}</span>
                  <span aria-hidden="true">·</span>
                  <span
                    className={
                      inc.severity === 'Critical'
                        ? 'text-red-800 font-semibold'
                        : inc.severity === 'High'
                        ? 'text-amber-800 font-semibold'
                        : 'text-stone-700 font-semibold'
                    }
                  >
                    {inc.severity} Severity
                  </span>
                  <span aria-hidden="true">·</span>
                  <span>{inc.affectedModule}</span>
                </div>
                <h2 className="text-xl font-display font-medium text-stone-900">{inc.title}</h2>
              </div>

              <div className="text-xs font-mono text-stone-600">{inc.status}</div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 text-xs">
              <div className="space-y-1.5">
                <div className="font-semibold uppercase tracking-wider text-red-900 flex items-center gap-1.5">
                  <ShieldAlert className="w-3.5 h-3.5" />
                  <span>Observed Blast Radius</span>
                </div>
                <p className="text-stone-800 font-medium leading-relaxed">
                  {inc.blastRadiusMetric}
                </p>
              </div>

              <div className="space-y-1.5">
                <div className="font-semibold uppercase tracking-wider text-stone-500 flex items-center gap-1.5">
                  <AlertTriangle className="w-3.5 h-3.5" />
                  <span>Root Cause Mechanism</span>
                </div>
                <p className="text-stone-700 leading-relaxed">{inc.rootCause}</p>
              </div>

              <div className="space-y-1.5">
                <div className="font-semibold uppercase tracking-wider text-stone-500">
                  Immediate Tactical Mitigation
                </div>
                <p className="text-stone-700 leading-relaxed">{inc.immediateMitigation}</p>
              </div>
            </div>

            <div className="pt-4 border-t border-stone-200 flex flex-wrap items-center justify-between gap-4 text-xs">
              <div className="text-stone-600">
                <span>Architectural Plane: </span>
                <span className="font-medium text-stone-900">{inc.plane}</span>
                <span className="mx-2" aria-hidden="true">
                  ·
                </span>
                <span>Remediating Milestones: </span>
                <span className="font-mono text-stone-900">
                  {inc.linkedMilestoneIds.join(', ')}
                </span>
              </div>

              <div className="flex flex-wrap items-center gap-4">
                <button
                  type="button"
                  onClick={() => onSelectLane(RFC_TO_LANE[inc.linkedRfcId] || 'LANE-01')}
                  className="font-mono font-semibold text-emerald-900 hover:underline cursor-pointer"
                >
                  Open {RFC_TO_LANE[inc.linkedRfcId] || 'LANE-01'} Spec & Kernel →
                </button>
                <button
                  type="button"
                  onClick={() => onSelectRfc(inc.linkedRfcId)}
                  className="font-mono font-semibold text-blue-900 hover:underline cursor-pointer"
                >
                  Review RFC ({inc.linkedRfcId}) →
                </button>
              </div>
            </div>
          </article>
        ))}
      </section>
    </div>
  );
};
