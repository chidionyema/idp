import React, { useState } from 'react';
import {
  GitBranch,
  Search,
  CheckCircle2,
  AlertTriangle,
  Clock,
  Shield,
  Layers,
  Activity,
  Tag
} from 'lucide-react';
import { ESTATE_CAPABILITIES } from '../core/registry';
import { EstateCapability } from '../core/types';

export const CapabilityCatalog: React.FC = () => {
  const [search, setSearch] = useState('');
  const [ownerFilter, setOwnerFilter] = useState<string>('ALL');
  const [selectedCap, setSelectedCap] = useState<EstateCapability | null>(null);

  const filtered = ESTATE_CAPABILITIES.filter((cap) => {
    const matchesOwner = ownerFilter === 'ALL' || cap.owner === ownerFilter;
    const matchesSearch =
      cap.name.toLowerCase().includes(search.toLowerCase()) ||
      cap.id.toLowerCase().includes(search.toLowerCase()) ||
      cap.tags.some((t) => t.toLowerCase().includes(search.toLowerCase())) ||
      cap.description.toLowerCase().includes(search.toLowerCase());

    return matchesOwner && matchesSearch;
  });

  const getReadinessBadge = (readiness: string) => {
    switch (readiness) {
      case 'operationally_verified':
        return 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30';
      case 'deployed':
      case 'tested':
        return 'bg-blue-500/20 text-blue-400 border-blue-500/30';
      case 'implemented':
      case 'discovered':
        return 'bg-amber-500/20 text-amber-400 border-amber-500/30';
      case 'degraded':
        return 'bg-rose-500/20 text-rose-400 border-rose-500/30';
      default:
        return 'bg-slate-800 text-slate-400 border-slate-700';
    }
  };

  return (
    <div className="space-y-6">
      {/* Banner */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-base font-bold text-white flex items-center gap-2">
            <GitBranch className="w-5 h-5 text-indigo-400" />
            Authoritative Estate Capability Catalog (IDP + Argon Genesis)
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Real capability inventory with strictly typed inputs/outputs, required RBAC permissions, and evidence-backed operational readiness.
          </p>
        </div>

        <div className="flex items-center gap-2 font-mono text-xs">
          <span className="px-2.5 py-1 rounded bg-slate-800 text-slate-300 border border-slate-700">
            Total Estate Capabilities: <strong className="text-white">{ESTATE_CAPABILITIES.length}</strong>
          </span>
          <span className="px-2.5 py-1 rounded bg-emerald-950 text-emerald-400 border border-emerald-800">
            Verified Ready: <strong>{ESTATE_CAPABILITIES.filter((c) => c.readiness === 'operationally_verified').length}</strong>
          </span>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 flex flex-col md:flex-row md:items-center justify-between gap-3 shadow-sm">
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="text-xs text-slate-400 mr-2">Owner Filter:</span>
          {['ALL', 'IDP_CORE', 'ARGON_GENESIS', 'INFRA_SECOPS', 'DATA_PLATFORM'].map((owner) => (
            <button
              key={owner}
              onClick={() => setOwnerFilter(owner)}
              className={`text-xs px-2.5 py-1 rounded-md font-mono transition-all cursor-pointer ${
                ownerFilter === owner
                  ? 'bg-blue-600 text-white font-semibold'
                  : 'bg-slate-800/60 text-slate-400 hover:text-white hover:bg-slate-800'
              }`}
            >
              {owner.replace(/_/g, ' ')}
            </button>
          ))}
        </div>

        <div className="relative">
          <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-slate-500" />
          <input
            type="text"
            placeholder="Search capabilities or tags..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="bg-slate-950 border border-slate-700 rounded-lg pl-8 pr-3 py-1 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-blue-500 w-full md:w-64"
          />
        </div>
      </div>

      {/* Catalog Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filtered.map((cap) => (
          <div
            key={cap.id}
            onClick={() => setSelectedCap(cap)}
            className="bg-slate-900/80 border border-slate-800 hover:border-slate-700 rounded-xl p-5 flex flex-col justify-between gap-4 transition-all hover:bg-slate-850 cursor-pointer shadow-sm"
          >
            <div className="space-y-2">
              <div className="flex items-start justify-between gap-2">
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                  {cap.owner}
                </span>
                <span className={`text-[10px] font-mono px-2 py-0.5 rounded border font-bold ${getReadinessBadge(cap.readiness)}`}>
                  {cap.readiness}
                </span>
              </div>

              <div>
                <h3 className="text-sm font-bold text-white group-hover:text-blue-400">{cap.name}</h3>
                <div className="text-[11px] font-mono text-blue-400 truncate mt-0.5">
                  {cap.id} <span className="text-slate-500">v{cap.version}</span>
                </div>
              </div>

              <p className="text-xs text-slate-400 line-clamp-2">{cap.description}</p>
            </div>

            <div className="space-y-3 pt-3 border-t border-slate-800/80">
              {/* Tags */}
              <div className="flex flex-wrap gap-1">
                {cap.tags.slice(0, 4).map((t) => (
                  <span key={t} className="text-[10px] font-mono px-1.5 py-0.2 bg-slate-950 text-slate-400 rounded border border-slate-800">
                    #{t}
                  </span>
                ))}
              </div>

              {/* Stats Footer */}
              <div className="flex items-center justify-between text-[11px] font-mono text-slate-400">
                <span className="flex items-center gap-1 text-emerald-400">
                  <Activity className="w-3 h-3" />
                  {cap.readinessEvidence.uptime90d}% Uptime
                </span>
                <span className="flex items-center gap-1 text-slate-300">
                  <Clock className="w-3 h-3 text-blue-400" />
                  +{cap.avoidedHoursOnReuse}h Yield
                </span>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Selected Capability Modal */}
      {selectedCap && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-xl max-w-2xl w-full p-6 space-y-4 shadow-2xl max-h-[90vh] overflow-y-auto">
            <div className="flex items-start justify-between">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700 font-bold">
                    {selectedCap.owner}
                  </span>
                  <span className={`text-[10px] font-mono px-2 py-0.5 rounded border font-bold ${getReadinessBadge(selectedCap.readiness)}`}>
                    {selectedCap.readiness}
                  </span>
                </div>
                <h3 className="text-lg font-bold text-white">{selectedCap.name}</h3>
                <div className="text-xs font-mono text-blue-400">
                  {selectedCap.id} <span className="text-slate-500">v{selectedCap.version}</span>
                </div>
              </div>
              <button
                onClick={() => setSelectedCap(null)}
                className="text-slate-400 hover:text-white text-sm font-mono p-1 rounded hover:bg-slate-800 cursor-pointer"
              >
                ✕
              </button>
            </div>

            <p className="text-xs text-slate-300 leading-relaxed font-sans">{selectedCap.description}</p>

            <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 font-mono text-xs text-slate-300">
              <span className="text-slate-500">Authoritative Source: </span>
              <code className="text-cyan-300">{selectedCap.authoritativeSource}</code>
            </div>

            {/* Inputs & Outputs */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 font-mono text-xs">
              <div className="bg-slate-950 p-3 rounded-lg border border-slate-800">
                <div className="font-bold text-blue-400 mb-2">Typed Inputs:</div>
                {selectedCap.inputs.map((inp) => (
                  <div key={inp.name} className="py-1 border-b border-slate-800/60">
                    <div className="flex justify-between">
                      <span className="text-slate-200">
                        {inp.name} {inp.required && <span className="text-rose-400">*</span>}
                      </span>
                      <span className="text-slate-500">{inp.type}</span>
                    </div>
                    <div className="text-[10px] text-slate-400 font-sans">{inp.description}</div>
                  </div>
                ))}
              </div>

              <div className="bg-slate-950 p-3 rounded-lg border border-slate-800">
                <div className="font-bold text-cyan-400 mb-2">Typed Outputs:</div>
                {selectedCap.outputs.map((out) => (
                  <div key={out.name} className="py-1 border-b border-slate-800/60">
                    <div className="flex justify-between">
                      <span className="text-slate-200">{out.name}</span>
                      <span className="text-slate-500">{out.type}</span>
                    </div>
                    <div className="text-[10px] text-slate-400 font-sans">{out.description}</div>
                  </div>
                ))}
              </div>
            </div>

            {/* Evidence & Permissions */}
            <div className="bg-slate-950 p-4 rounded-lg border border-slate-800 space-y-2 font-mono text-xs">
              <div className="font-bold text-emerald-400">Operational Evidence Metrics:</div>
              <div className="grid grid-cols-2 gap-2 text-[11px] text-slate-300">
                <div>90-Day Uptime: <strong className="text-white">{selectedCap.readinessEvidence.uptime90d}%</strong></div>
                <div>Verified Runs: <strong className="text-white">{selectedCap.readinessEvidence.verifiedExecutionCount}</strong></div>
                <div>Last Healthcheck: <span className="text-slate-400">{selectedCap.readinessEvidence.lastHealthCheck.split('T')[0]}</span></div>
                <div>SLA Target: <strong className="text-white">{selectedCap.slaMinutes} min</strong></div>
              </div>
              <div className="text-[11px] text-slate-400 pt-2 border-t border-slate-800">
                Required RBAC: <code className="text-amber-300">[{selectedCap.requiredPermissions.join(', ')}]</code>
              </div>
            </div>

            <div className="flex justify-end pt-2">
              <button
                onClick={() => setSelectedCap(null)}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-xs font-semibold cursor-pointer"
              >
                Close Inspector
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
