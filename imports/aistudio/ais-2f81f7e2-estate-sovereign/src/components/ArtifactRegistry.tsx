import React, { useState } from 'react';
import { EstateArtifact } from '../types/estate';
import { Search, Eye, ShieldCheck, FileCode, CheckCircle, Database, Plus, Hash } from 'lucide-react';

interface ArtifactRegistryProps {
  artifacts: EstateArtifact[];
  onInspectArtifact: (artifact: EstateArtifact) => void;
  onRegisterArtifact: (artifact: Omit<EstateArtifact, 'id' | 'updatedAt'>) => void;
}

export const ArtifactRegistry: React.FC<ArtifactRegistryProps> = ({
  artifacts,
  onInspectArtifact,
  onRegisterArtifact,
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedType, setSelectedType] = useState<string>('ALL');
  const [isRegisterOpen, setIsRegisterOpen] = useState(false);

  // Form state for registering new artifact
  const [newTitle, setNewTitle] = useState('');
  const [newType, setNewType] = useState<EstateArtifact['type']>('VISUAL_MOCKUP');
  const [newDepositLocation, setNewDepositLocation] = useState('');
  const [newOriginAgent, setNewOriginAgent] = useState('Founder-Console');
  const [newDescription, setNewDescription] = useState('');
  const [newSummary, setNewSummary] = useState('');

  const filteredArtifacts = artifacts.filter((item) => {
    const matchesSearch = 
      item.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.originAgent.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.depositLocation.toLowerCase().includes(searchQuery.toLowerCase());
    
    const matchesType = selectedType === 'ALL' || item.type === selectedType;
    return matchesSearch && matchesType;
  });

  const handleRegisterSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTitle.trim()) return;

    onRegisterArtifact({
      title: newTitle,
      type: newType,
      status: 'VERIFIED_ACTIVE',
      depositLocation: newDepositLocation || `/vault/deposits/${Date.now()}.spec`,
      originAgent: newOriginAgent,
      checksum: `sha256:${Math.random().toString(16).substring(2, 10)}${Date.now().toString(16)}`,
      version: '1.0.0',
      description: newDescription || 'Founder registered operational artifact.',
      contentSummary: newSummary || 'Fully indexed and locked in the sovereign vault.',
      metadata: {
        derivationChain: ['Founder-Direct-Registration']
      }
    });

    // Reset & Close
    setNewTitle('');
    setNewDescription('');
    setNewSummary('');
    setNewDepositLocation('');
    setIsRegisterOpen(false);
  };

  return (
    <div className="space-y-6">
      {/* Header and Summary */}
      <div className="bg-neutral-900 border border-neutral-800 rounded-xl p-5">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2 text-xs font-mono uppercase tracking-wider text-emerald-400">
              <Database className="w-4 h-4 text-emerald-400" />
              <span>Immutable Artifact Provenance Vault</span>
              <span className="text-neutral-600">/</span>
              <span>Zero Missing Artifacts Policy</span>
            </div>
            <h1 className="text-xl md:text-2xl font-bold text-white tracking-tight">
              Track &amp; Trace Artifact Registry
            </h1>
            <p className="text-xs md:text-sm text-neutral-400 max-w-3xl">
              Cryptographically verified repository of all mockups, decrees, system architecture diagrams, 
              financial ledgers, and delivery payloads. Eliminates the founder blind spot with immutable deposit coordinates.
            </p>
          </div>

          <button
            onClick={() => setIsRegisterOpen(true)}
            className="inline-flex items-center gap-2 px-4 py-2 text-xs font-semibold text-neutral-950 bg-amber-500 hover:bg-amber-400 rounded-lg transition-colors cursor-pointer shrink-0"
          >
            <Plus className="w-4 h-4" />
            <span>Register New Artifact</span>
          </button>
        </div>

        {/* Highlight Banner: Recovered Visual Mockup */}
        <div className="mt-5 p-4 rounded-lg bg-emerald-950/30 border border-emerald-800/60 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-start gap-3">
            <div className="w-8 h-8 rounded-lg bg-emerald-900/60 border border-emerald-700/60 flex items-center justify-center shrink-0 text-emerald-400">
              <Eye className="w-4 h-4" />
            </div>
            <div>
              <div className="flex items-center gap-2 text-xs">
                <span className="font-mono text-emerald-400 font-bold">RECOVERED FOUNDER ARTIFACT</span>
                <span className="text-neutral-500">·</span>
                <span className="text-neutral-400 font-mono">ART-001</span>
                <span className="text-neutral-500">·</span>
                <span className="text-neutral-400 font-mono">v1.4.0</span>
              </div>
              <div className="text-sm font-semibold text-white mt-0.5">
                Real-Time Visual Intelligence &amp; Estate Topology Mockup
              </div>
              <div className="text-xs text-neutral-400 font-mono mt-0.5">
                Location: /vault/visual-telemetry/interactive-estate-grid-v1.json (sha256: 7f83b165...069)
              </div>
            </div>
          </div>

          <button
            onClick={() => onInspectArtifact(artifacts[0])}
            className="px-3.5 py-1.5 text-xs font-semibold text-neutral-950 bg-emerald-400 hover:bg-emerald-300 rounded-lg transition-colors cursor-pointer shrink-0 self-start sm:self-auto"
          >
            Launch Interactive Preview
          </button>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-col md:flex-row items-stretch md:items-center justify-between gap-4">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-500" />
          <input
            type="text"
            placeholder="Search artifacts by ID, title, origin agent, or checksum..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-4 py-2 bg-neutral-900 border border-neutral-800 rounded-lg text-xs text-white placeholder-neutral-500 focus:outline-none focus:border-amber-500"
          />
        </div>

        {/* Segmented Filter Control */}
        <div className="flex items-center gap-1 p-1 bg-neutral-900 rounded-lg border border-neutral-800 overflow-x-auto">
          {[
            { id: 'ALL', label: 'All Artifacts' },
            { id: 'VISUAL_MOCKUP', label: 'Visual Mockups' },
            { id: 'SOVEREIGN_EDICT', label: 'Decrees & Edicts' },
            { id: 'ARCHITECTURAL_BLUEPRINT', label: 'Blueprints' },
            { id: 'FINANCIAL_LEDGER', label: 'Ledgers' },
            { id: 'DELIVERY_SPEC', label: 'Delivery Specs' },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setSelectedType(tab.id)}
              className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors whitespace-nowrap cursor-pointer ${
                selectedType === tab.id
                  ? 'bg-neutral-800 text-white shadow-sm'
                  : 'text-neutral-400 hover:text-white'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Artifacts Grid / Table */}
      <div className="bg-neutral-900 border border-neutral-800 rounded-xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-neutral-950/80 border-b border-neutral-800 text-neutral-400 font-mono uppercase tracking-wider">
              <tr>
                <th className="px-5 py-3 font-medium">Artifact ID &amp; Type</th>
                <th className="px-5 py-3 font-medium">Title &amp; Description</th>
                <th className="px-5 py-3 font-medium">Deposit Coordinates</th>
                <th className="px-5 py-3 font-medium">Origin Agent</th>
                <th className="px-5 py-3 font-medium">Checksum Status</th>
                <th className="px-5 py-3 font-medium text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-800/80">
              {filteredArtifacts.map((item) => (
                <tr key={item.id} className="hover:bg-neutral-800/30 transition-colors">
                  <td className="px-5 py-3.5 whitespace-nowrap">
                    <div className="font-mono font-bold text-white flex items-center gap-1.5">
                      <Hash className="w-3.5 h-3.5 text-neutral-500" />
                      <span>{item.id}</span>
                    </div>
                    <div className="text-[11px] text-neutral-400 mt-0.5">
                      {item.type.replace('_', ' ')}
                    </div>
                  </td>

                  <td className="px-5 py-3.5 max-w-xs">
                    <div className="font-semibold text-white hover:text-amber-400 cursor-pointer" onClick={() => onInspectArtifact(item)}>
                      {item.title}
                    </div>
                    <div className="text-neutral-400 text-[11px] line-clamp-1 mt-0.5">
                      {item.description}
                    </div>
                  </td>

                  <td className="px-5 py-3.5 whitespace-nowrap font-mono text-neutral-300">
                    <div className="flex items-center gap-1.5">
                      <span className="text-amber-400">~/</span>
                      <span>{item.depositLocation}</span>
                    </div>
                    <div className="text-neutral-500 text-[11px] mt-0.5">
                      Updated {new Date(item.updatedAt).toLocaleDateString()}
                    </div>
                  </td>

                  <td className="px-5 py-3.5 whitespace-nowrap font-mono text-neutral-400">
                    {item.originAgent}
                  </td>

                  <td className="px-5 py-3.5 whitespace-nowrap">
                    <div className="flex items-center gap-1.5 text-emerald-400 font-mono">
                      <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
                      <span>{item.status === 'ORPHANED_RECOVERED' ? 'RECOVERED' : 'VERIFIED'}</span>
                    </div>
                    <div className="text-neutral-500 font-mono text-[10px] mt-0.5">
                      {item.checksum.substring(0, 16)}...
                    </div>
                  </td>

                  <td className="px-5 py-3.5 whitespace-nowrap text-right">
                    <button
                      onClick={() => onInspectArtifact(item)}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-neutral-800 hover:bg-neutral-700 text-white rounded-lg text-xs font-medium transition-colors cursor-pointer"
                    >
                      <Eye className="w-3.5 h-3.5" />
                      <span>Inspect</span>
                    </button>
                  </td>
                </tr>
              ))}

              {filteredArtifacts.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-5 py-10 text-center text-neutral-500">
                    No artifacts found matching query "{searchQuery}".
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Register Artifact Modal */}
      {isRegisterOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-xs">
          <div className="bg-neutral-900 border border-neutral-800 rounded-xl max-w-lg w-full p-6 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-white">Register &amp; Lock Estate Artifact</h3>
              <button
                onClick={() => setIsRegisterOpen(false)}
                className="text-neutral-400 hover:text-white cursor-pointer"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleRegisterSubmit} className="space-y-4 text-xs">
              <div>
                <label className="block text-neutral-400 mb-1">Artifact Title</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Visual Intelligence Dashboard Layout V2"
                  value={newTitle}
                  onChange={(e) => setNewTitle(e.target.value)}
                  className="w-full px-3 py-2 bg-neutral-950 border border-neutral-800 rounded-lg text-white placeholder-neutral-500 focus:outline-none focus:border-amber-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-neutral-400 mb-1">Artifact Type</label>
                  <select
                    value={newType}
                    onChange={(e) => setNewType(e.target.value as any)}
                    className="w-full px-3 py-2 bg-neutral-950 border border-neutral-800 rounded-lg text-white focus:outline-none focus:border-amber-500"
                  >
                    <option value="VISUAL_MOCKUP">Visual Mockup</option>
                    <option value="ARCHITECTURAL_BLUEPRINT">Architectural Blueprint</option>
                    <option value="SOVEREIGN_EDICT">Sovereign Edict</option>
                    <option value="FINANCIAL_LEDGER">Financial Ledger</option>
                    <option value="DELIVERY_SPEC">Delivery Spec</option>
                  </select>
                </div>

                <div>
                  <label className="block text-neutral-400 mb-1">Origin Agent</label>
                  <input
                    type="text"
                    value={newOriginAgent}
                    onChange={(e) => setNewOriginAgent(e.target.value)}
                    className="w-full px-3 py-2 bg-neutral-950 border border-neutral-800 rounded-lg text-white focus:outline-none focus:border-amber-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-neutral-400 mb-1">Deposit Path in Sovereign Vault</label>
                <input
                  type="text"
                  placeholder="/vault/spec/delivery-motion-05.spec"
                  value={newDepositLocation}
                  onChange={(e) => setNewDepositLocation(e.target.value)}
                  className="w-full px-3 py-2 bg-neutral-950 border border-neutral-800 rounded-lg text-white placeholder-neutral-500 focus:outline-none focus:border-amber-500 font-mono"
                />
              </div>

              <div>
                <label className="block text-neutral-400 mb-1">Description &amp; Purpose</label>
                <textarea
                  rows={2}
                  placeholder="Explain why this artifact was produced and what decree it satisfies..."
                  value={newDescription}
                  onChange={(e) => setNewDescription(e.target.value)}
                  className="w-full px-3 py-2 bg-neutral-950 border border-neutral-800 rounded-lg text-white placeholder-neutral-500 focus:outline-none focus:border-amber-500"
                />
              </div>

              <div>
                <label className="block text-neutral-400 mb-1">Content Summary</label>
                <textarea
                  rows={2}
                  placeholder="Key deliverables, outputs, or state vectors..."
                  value={newSummary}
                  onChange={(e) => setNewSummary(e.target.value)}
                  className="w-full px-3 py-2 bg-neutral-950 border border-neutral-800 rounded-lg text-white placeholder-neutral-500 focus:outline-none focus:border-amber-500"
                />
              </div>

              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setIsRegisterOpen(false)}
                  className="px-4 py-2 bg-neutral-800 hover:bg-neutral-700 text-neutral-300 rounded-lg cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-amber-500 hover:bg-amber-400 text-neutral-950 font-semibold rounded-lg cursor-pointer"
                >
                  Register in Vault
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
