import React, { useState } from 'react';
import {
  ArchitecturalPlane,
  AsymmetryVector,
  HorizonId,
  MilestoneStatus,
  RoadmapMilestone,
} from '../data/idpDomainData';
import {
  computeRoadmapSummary,
  filterMilestones,
  RoadmapFilterState,
} from '../utils/roadmapLogic';
import { ArrowRight, CheckCircle2, Filter, Search } from 'lucide-react';

interface RoadmapMatrixViewProps {
  milestones: RoadmapMilestone[];
  initialPlaneFilter?: ArchitecturalPlane | 'ALL';
  onUpdateMilestoneStatus: (milestoneId: string, newStatus: MilestoneStatus) => void;
  onSelectRfc: (rfcId: string) => void;
  onSelectIncident: (incidentId: string) => void;
  onSelectLane: (laneId: string) => void;
}

const PLANE_TO_LANE: Record<ArchitecturalPlane, string> = {
  'Ingestion & Sensorium': 'LANE-01',
  'Bitemporal Ontology & Graph': 'LANE-02',
  'Asymmetry & Falsification Engine': 'LANE-04',
  'Convex Execution & Simulation': 'LANE-05',
  'Governance & Epistemic Audit': 'LANE-02',
};

const PLANES: ArchitecturalPlane[] = [
  'Ingestion & Sensorium',
  'Bitemporal Ontology & Graph',
  'Asymmetry & Falsification Engine',
  'Convex Execution & Simulation',
  'Governance & Epistemic Audit',
];

const VECTORS: AsymmetryVector[] = [
  'Information Latency Arbitrage',
  'Cross-Silo Structural Blindspot',
  'Narrative-vs-Telemetry Divergence',
  'Tail-Risk Convexity',
];

const HORIZONS: { id: HorizonId; label: string; window: string; theme: string }[] = [
  {
    id: 'H1',
    label: 'Horizon 1: Epistemic Stabilization & Bitemporal Spine',
    window: 'Days 0–90',
    theme: 'Eliminate look-ahead leakage, lock contention, and provenance heap amplification.',
  },
  {
    id: 'H2',
    label: 'Horizon 2: Sub-Second Streaming Divergence & Falsification',
    window: 'Days 90–180',
    theme: 'Decouple divergence kernels from batch windows and deploy Bayesian sensor-confounding gates.',
  },
  {
    id: 'H3',
    label: 'Horizon 3: Autonomous Red-Teaming & Contagion Cascades',
    window: 'Days 180–365',
    theme: 'Scale counterfactual shock synthesis and 2nd/3rd-order cross-market contagion execution.',
  },
];

const STATUS_OPTIONS: MilestoneStatus[] = [
  'Completed',
  'In Progress',
  'Blocked by RFC',
  'Planned',
];

export const RoadmapMatrixView: React.FC<RoadmapMatrixViewProps> = ({
  milestones,
  initialPlaneFilter = 'ALL',
  onUpdateMilestoneStatus,
  onSelectRfc,
  onSelectIncident,
  onSelectLane,
}) => {
  const [filters, setFilters] = useState<RoadmapFilterState>({
    horizon: 'ALL',
    plane: initialPlaneFilter,
    vector: 'ALL',
    searchQuery: '',
  });

  const [selectedMilestoneId, setSelectedMilestoneId] = useState<string>(milestones[0]?.id || '');
  const [viewMode, setViewMode] = useState<'matrix' | 'ledger'>('matrix');

  React.useEffect(() => {
    setFilters((prev) => ({ ...prev, plane: initialPlaneFilter }));
  }, [initialPlaneFilter]);

  const filteredMilestones = filterMilestones(milestones, filters);
  const summary = computeRoadmapSummary(filteredMilestones);

  const activeMilestone =
    milestones.find((m) => m.id === selectedMilestoneId) ||
    filteredMilestones[0] ||
    milestones[0];

  const handleResetFilters = () => {
    setFilters({
      horizon: 'ALL',
      plane: 'ALL',
      vector: 'ALL',
      searchQuery: '',
    });
  };

  return (
    <div className="space-y-10">
      {/* Header & Quantitative Summary Strip */}
      <section className="border-b border-stone-200 pb-8 space-y-6">
        <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-6">
          <div className="space-y-2">
            <div className="text-xs uppercase tracking-widest text-stone-500">
              Multi-Dimensional Architecture Roadmap · 3 Horizons × 5 Planes × 4 Vectors
            </div>
            <h1 className="text-3xl sm:text-4xl font-display font-medium text-stone-900">
              Systemic Asymmetry Engineering Roadmap
            </h1>
          </div>

          {/* View Mode Segmented Switch */}
          <div className="flex items-center gap-1 p-1 bg-stone-200/70 self-start">
            <button
              type="button"
              onClick={() => setViewMode('matrix')}
              className={`px-3.5 py-1.5 text-xs font-medium transition-colors cursor-pointer whitespace-nowrap ${
                viewMode === 'matrix'
                  ? 'bg-white text-stone-900 shadow-xs'
                  : 'text-stone-600 hover:text-stone-900'
              }`}
            >
              Plane × Horizon Matrix
            </button>
            <button
              type="button"
              onClick={() => setViewMode('ledger')}
              className={`px-3.5 py-1.5 text-xs font-medium transition-colors cursor-pointer whitespace-nowrap ${
                viewMode === 'ledger'
                  ? 'bg-white text-stone-900 shadow-xs'
                  : 'text-stone-600 hover:text-stone-900'
              }`}
            >
              Detailed Milestone Ledger
            </button>
          </div>
        </div>

        {/* Summary Metrics Bar */}
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-4 pt-2">
          <div className="bg-white border border-stone-200 p-4">
            <div className="text-xs text-stone-500">Visible Milestones</div>
            <div className="text-2xl font-mono font-semibold text-stone-900 tabular-nums mt-1">
              {summary.total}
            </div>
            <div className="text-xs text-stone-500 mt-1 font-mono tabular-nums">
              {summary.totalEffortWeeks} eng-weeks total
            </div>
          </div>

          <div className="bg-white border border-stone-200 p-4">
            <div className="text-xs text-stone-500">In Progress / Active</div>
            <div className="text-2xl font-mono font-semibold text-blue-900 tabular-nums mt-1">
              {summary.inProgress}
            </div>
            <div className="text-xs text-stone-500 mt-1">H1 stabilization focus</div>
          </div>

          <div className="bg-white border border-stone-200 p-4">
            <div className="text-xs text-stone-500">Blocked by RFC Sign-Off</div>
            <div className="text-2xl font-mono font-semibold text-amber-800 tabular-nums mt-1">
              {summary.blocked}
            </div>
            <div className="text-xs text-stone-500 mt-1">Awaiting consultant review</div>
          </div>

          <div className="bg-white border border-stone-200 p-4">
            <div className="text-xs text-stone-500">Completed</div>
            <div className="text-2xl font-mono font-semibold text-emerald-800 tabular-nums mt-1">
              {summary.completed}
            </div>
            <div className="text-xs text-stone-500 mt-1">Verified in production</div>
          </div>

          <div className="bg-white border border-stone-200 p-4 col-span-2 sm:col-span-1">
            <div className="text-xs text-stone-500">Effort Distribution</div>
            <div className="text-xs font-mono text-stone-800 space-y-1 mt-2 tabular-nums">
              <div className="flex justify-between">
                <span>H1 (0–90d):</span>
                <span>{summary.byHorizon.H1.weeks}w</span>
              </div>
              <div className="flex justify-between">
                <span>H2 (90–180d):</span>
                <span>{summary.byHorizon.H2.weeks}w</span>
              </div>
              <div className="flex justify-between">
                <span>H3 (180–365d):</span>
                <span>{summary.byHorizon.H3.weeks}w</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Multi-Dimensional Filter Controls */}
      <section className="bg-white border border-stone-200 p-5 space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wider text-stone-600">
            <Filter className="w-3.5 h-3.5" />
            <span>Filter Architecture Dimensions</span>
          </div>
          {(filters.horizon !== 'ALL' ||
            filters.plane !== 'ALL' ||
            filters.vector !== 'ALL' ||
            filters.searchQuery !== '') && (
            <button
              type="button"
              onClick={handleResetFilters}
              className="text-xs font-medium text-blue-900 hover:underline cursor-pointer"
            >
              Reset All Dimension Filters
            </button>
          )}
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Horizon Selector */}
          <div>
            <label
              htmlFor="filter-horizon"
              className="block text-xs font-medium text-stone-600 mb-1.5"
            >
              Horizon Dimension
            </label>
            <select
              id="filter-horizon"
              value={filters.horizon}
              onChange={(e) =>
                setFilters((prev) => ({
                  ...prev,
                  horizon: e.target.value as HorizonId | 'ALL',
                }))
              }
              className="w-full px-3 py-2 text-xs bg-stone-50 border border-stone-300 text-stone-900 focus:outline-none focus:border-stone-900"
            >
              <option value="ALL">All Horizons (H1 · H2 · H3)</option>
              <option value="H1">H1 — Days 0–90 (Stabilization & Spine)</option>
              <option value="H2">H2 — Days 90–180 (Streaming & Falsification)</option>
              <option value="H3">H3 — Days 180–365 (Autonomous Red-Team)</option>
            </select>
          </div>

          {/* Plane Selector */}
          <div>
            <label
              htmlFor="filter-plane"
              className="block text-xs font-medium text-stone-600 mb-1.5"
            >
              Architectural Plane
            </label>
            <select
              id="filter-plane"
              value={filters.plane}
              onChange={(e) =>
                setFilters((prev) => ({
                  ...prev,
                  plane: e.target.value as ArchitecturalPlane | 'ALL',
                }))
              }
              className="w-full px-3 py-2 text-xs bg-stone-50 border border-stone-300 text-stone-900 focus:outline-none focus:border-stone-900"
            >
              <option value="ALL">All 5 Architectural Planes</option>
              {PLANES.map((p) => (
                <option key={p} value={p}>
                  {p}
                </option>
              ))}
            </select>
          </div>

          {/* Asymmetry Vector Selector */}
          <div>
            <label
              htmlFor="filter-vector"
              className="block text-xs font-medium text-stone-600 mb-1.5"
            >
              Asymmetry Exploitation Vector
            </label>
            <select
              id="filter-vector"
              value={filters.vector}
              onChange={(e) =>
                setFilters((prev) => ({
                  ...prev,
                  vector: e.target.value as AsymmetryVector | 'ALL',
                }))
              }
              className="w-full px-3 py-2 text-xs bg-stone-50 border border-stone-300 text-stone-900 focus:outline-none focus:border-stone-900"
            >
              <option value="ALL">All Asymmetry Vectors</option>
              {VECTORS.map((v) => (
                <option key={v} value={v}>
                  {v}
                </option>
              ))}
            </select>
          </div>

          {/* Search Input */}
          <div>
            <label
              htmlFor="filter-search"
              className="block text-xs font-medium text-stone-600 mb-1.5"
            >
              Search Milestone, Incident, or RFC
            </label>
            <div className="relative">
              <Search className="w-3.5 h-3.5 text-stone-400 absolute left-3 top-2.5" />
              <input
                id="filter-search"
                type="text"
                value={filters.searchQuery}
                onChange={(e) =>
                  setFilters((prev) => ({ ...prev, searchQuery: e.target.value }))
                }
                placeholder="e.g. Iceberg, INC-2026-089, RFC-02"
                className="w-full pl-8 pr-3 py-2 text-xs bg-stone-50 border border-stone-300 text-stone-900 focus:outline-none focus:border-stone-900"
              />
            </div>
          </div>
        </div>
      </section>

      {/* Main Content: Matrix or Ledger + Selected Milestone Inspector */}
      {filteredMilestones.length === 0 ? (
        <div className="bg-white border border-stone-200 p-12 text-center space-y-3">
          <div className="text-base font-medium text-stone-900">
            No roadmap milestones match the active dimensional filters.
          </div>
          <p className="text-xs text-stone-600 max-w-md mx-auto">
            Try clearing one of the plane, horizon, or asymmetry vector filters to inspect the full
            multi-dimensional architecture matrix.
          </p>
          <button
            type="button"
            onClick={handleResetFilters}
            className="px-4 py-2 text-xs font-medium text-white bg-stone-900 hover:bg-stone-800 transition-colors cursor-pointer"
          >
            Reset Filters
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
          {/* Left 7 Cols: Matrix or Ledger */}
          <div className="lg:col-span-7 space-y-6">
            {viewMode === 'matrix' ? (
              <div className="space-y-6">
                {HORIZONS.filter(
                  (h) => filters.horizon === 'ALL' || filters.horizon === h.id
                ).map((horizon) => {
                  const horizonMilestones = filteredMilestones.filter(
                    (m) => m.horizon === horizon.id
                  );
                  return (
                    <div
                      key={horizon.id}
                      className="bg-white border border-stone-200 p-6 space-y-4"
                    >
                      <div className="border-b border-stone-200 pb-3 flex flex-wrap items-baseline justify-between gap-2">
                        <div>
                          <div className="text-xs font-mono text-stone-500">
                            {horizon.id} · {horizon.window}
                          </div>
                          <h2 className="text-lg font-display font-medium text-stone-900">
                            {horizon.label}
                          </h2>
                        </div>
                        <span className="text-xs font-mono text-stone-600 tabular-nums">
                          {horizonMilestones.length} milestones
                        </span>
                      </div>
                      <p className="text-xs text-stone-600">{horizon.theme}</p>

                      <div className="divide-y divide-stone-200 border-t border-stone-200">
                        {horizonMilestones.map((ms) => {
                          const isSelected = ms.id === activeMilestone?.id;
                          return (
                            <div
                              key={ms.id}
                              onClick={() => setSelectedMilestoneId(ms.id)}
                              className={`py-4 px-3 transition-colors cursor-pointer ${
                                isSelected ? 'bg-blue-50/70' : 'hover:bg-stone-50'
                              }`}
                            >
                              <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-stone-500 font-mono mb-1">
                                <span>
                                  {ms.id} · {ms.plane}
                                </span>
                                <span
                                  className={
                                    ms.status === 'Completed'
                                      ? 'text-emerald-800 font-semibold'
                                      : ms.status === 'Blocked by RFC'
                                      ? 'text-amber-800 font-semibold'
                                      : ms.status === 'In Progress'
                                      ? 'text-blue-900 font-semibold'
                                      : 'text-stone-600'
                                  }
                                >
                                  {ms.status} · {ms.effortWeeks}w
                                </span>
                              </div>
                              <div className="flex items-center justify-between gap-4">
                                <button
                                  type="button"
                                  onClick={() => setSelectedMilestoneId(ms.id)}
                                  className="text-sm font-semibold text-stone-900 text-left hover:underline cursor-pointer"
                                >
                                  {ms.title}
                                </button>
                                <ArrowRight className="w-4 h-4 text-stone-400 shrink-0" />
                              </div>
                              <div className="mt-1.5 flex flex-wrap items-center gap-2 text-xs text-stone-500">
                                <span>Vector: {ms.asymmetryVector}</span>
                                <span aria-hidden="true">·</span>
                                <span>Proposal: {ms.linkedRfcId}</span>
                                {ms.linkedIncidentIds.length > 0 && (
                                  <>
                                    <span aria-hidden="true">·</span>
                                    <span>Fixes: {ms.linkedIncidentIds.join(', ')}</span>
                                  </>
                                )}
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="bg-white border border-stone-200 overflow-x-auto">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="border-b border-stone-200 text-xs text-stone-500 uppercase tracking-wider bg-stone-50">
                      <th className="py-3 px-4 font-medium">ID / Horizon</th>
                      <th className="py-3 px-4 font-medium">Milestone & Plane</th>
                      <th className="py-3 px-4 font-medium">Status</th>
                      <th className="py-3 px-4 font-medium text-right">Effort</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-stone-200 text-sm">
                    {filteredMilestones.map((ms) => {
                      const isSelected = ms.id === activeMilestone?.id;
                      return (
                        <tr
                          key={ms.id}
                          onClick={() => setSelectedMilestoneId(ms.id)}
                          className={`cursor-pointer transition-colors ${
                            isSelected ? 'bg-blue-50/70' : 'hover:bg-stone-50'
                          }`}
                        >
                          <td className="py-3.5 px-4 font-mono text-xs text-stone-700 whitespace-nowrap">
                            {ms.id} · {ms.horizon}
                          </td>
                          <td className="py-3.5 px-4">
                            <div className="font-medium text-stone-900 text-xs">{ms.title}</div>
                            <div className="text-xs text-stone-500 mt-0.5">
                              {ms.plane} · {ms.asymmetryVector}
                            </div>
                          </td>
                          <td className="py-3.5 px-4 text-xs font-mono whitespace-nowrap">
                            {ms.status}
                          </td>
                          <td className="py-3.5 px-4 text-right font-mono text-xs tabular-nums whitespace-nowrap">
                            {ms.effortWeeks}w
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Right 5 Cols: Active Milestone Specification & Status Controller */}
          {activeMilestone && (
            <aside className="lg:col-span-5 bg-white border border-stone-200 p-6 space-y-6 lg:sticky lg:top-6">
              <div className="border-b border-stone-200 pb-4 space-y-2">
                <div className="flex items-center justify-between text-xs font-mono text-stone-500">
                  <span>
                    {activeMilestone.id} · Horizon {activeMilestone.horizon}
                  </span>
                  <span>{activeMilestone.effortWeeks} Eng-Weeks</span>
                </div>
                <h3 className="text-xl font-display font-medium text-stone-900">
                  {activeMilestone.title}
                </h3>
                <div className="text-xs text-stone-600">
                  {activeMilestone.plane} · {activeMilestone.ownerTrack}
                </div>
              </div>

              {/* Interactive Status Control */}
              <div className="space-y-2">
                <label
                  htmlFor="milestone-status-select"
                  className="block text-xs font-medium uppercase tracking-wider text-stone-500"
                >
                  Update Milestone Execution Status
                </label>
                <div className="grid grid-cols-2 gap-1.5">
                  {STATUS_OPTIONS.map((st) => {
                    const active = activeMilestone.status === st;
                    return (
                      <button
                        key={st}
                        type="button"
                        onClick={() => onUpdateMilestoneStatus(activeMilestone.id, st)}
                        className={`px-3 py-2 text-xs font-medium border text-left transition-colors cursor-pointer flex items-center justify-between ${
                          active
                            ? 'bg-stone-900 text-white border-stone-900'
                            : 'bg-stone-50 text-stone-700 border-stone-200 hover:bg-stone-100'
                        }`}
                      >
                        <span className="truncate">{st}</span>
                        {active && <CheckCircle2 className="w-3.5 h-3.5 shrink-0" />}
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Systemic Asymmetry Thesis Impact */}
              <div className="space-y-1.5 border-t border-stone-200 pt-4">
                <div className="text-xs font-medium uppercase tracking-wider text-stone-500">
                  Asymmetry Exploitation Rationale ({activeMilestone.asymmetryVector})
                </div>
                <p className="text-xs text-stone-700 leading-relaxed">
                  {activeMilestone.thesisImpact}
                </p>
              </div>

              {/* Concrete Engineering Deliverables */}
              <div className="space-y-2 border-t border-stone-200 pt-4">
                <div className="text-xs font-medium uppercase tracking-wider text-stone-500">
                  Key Engineering Deliverables
                </div>
                <ul className="space-y-1.5 text-xs text-stone-700 list-disc pl-4">
                  {activeMilestone.deliverables.map((deliv, i) => (
                    <li key={i} className="leading-relaxed">
                      {deliv}
                    </li>
                  ))}
                </ul>
              </div>

              {/* Quantitative Acceptance Gate */}
              <div className="space-y-1.5 border-t border-stone-200 pt-4">
                <div className="text-xs font-medium uppercase tracking-wider text-stone-500">
                  Quantitative Acceptance Criterion
                </div>
                <div className="p-3 bg-stone-50 border border-stone-200 font-mono text-xs text-stone-900">
                  {activeMilestone.acceptanceMetric}
                </div>
              </div>

              {/* Cross-References to Critical Lane, RFCs, Incidents, and Dependencies */}
              <div className="space-y-3 border-t border-stone-200 pt-4 text-xs">
                <div className="flex items-center justify-between">
                  <span className="text-stone-500">Critical Agent Build Lane:</span>
                  <button
                    type="button"
                    onClick={() =>
                      onSelectLane(
                        activeMilestone.linkedRfcId === 'RFC-02'
                          ? 'LANE-03'
                          : PLANE_TO_LANE[activeMilestone.plane]
                      )
                    }
                    className="font-mono font-semibold text-emerald-900 hover:underline cursor-pointer"
                  >
                    Open{' '}
                    {activeMilestone.linkedRfcId === 'RFC-02'
                      ? 'LANE-03'
                      : PLANE_TO_LANE[activeMilestone.plane]}{' '}
                    Spec & Code →
                  </button>
                </div>

                <div className="flex items-center justify-between">
                  <span className="text-stone-500">Governing Architecture RFC:</span>
                  <button
                    type="button"
                    onClick={() => onSelectRfc(activeMilestone.linkedRfcId)}
                    className="font-mono font-semibold text-blue-900 hover:underline cursor-pointer"
                  >
                    Inspect {activeMilestone.linkedRfcId} →
                  </button>
                </div>

                <div className="flex items-center justify-between">
                  <span className="text-stone-500">Remediated Incidents:</span>
                  <div className="flex items-center gap-2">
                    {activeMilestone.linkedIncidentIds.map((incId) => (
                      <button
                        key={incId}
                        type="button"
                        onClick={() => onSelectIncident(incId)}
                        className="font-mono font-medium text-red-900 hover:underline cursor-pointer"
                      >
                        {incId}
                      </button>
                    ))}
                  </div>
                </div>

                {activeMilestone.dependencies.length > 0 && (
                  <div className="flex items-center justify-between">
                    <span className="text-stone-500">Upstream Prerequisites:</span>
                    <span className="font-mono text-stone-800">
                      {activeMilestone.dependencies.join(', ')}
                    </span>
                  </div>
                )}
              </div>
            </aside>
          )}
        </div>
      )}
    </div>
  );
};
