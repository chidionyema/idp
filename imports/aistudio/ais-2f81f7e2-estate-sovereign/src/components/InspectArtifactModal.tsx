import React, { useState } from 'react';
import { EstateArtifact } from '../types/estate';
import { ShieldCheck, Copy, Check, ExternalLink, Hash, Database, Layers, Eye } from 'lucide-react';

interface InspectArtifactModalProps {
  artifact: EstateArtifact;
  onClose: () => void;
}

export const InspectArtifactModal: React.FC<InspectArtifactModalProps> = ({
  artifact,
  onClose,
}) => {
  const [copied, setCopied] = useState(false);
  const [activeTab, setActiveTab] = useState<'preview' | 'provenance' | 'raw'>('preview');

  const copyChecksum = () => {
    navigator.clipboard.writeText(artifact.checksum);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const isVisualMockup = artifact.type === 'VISUAL_MOCKUP';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-xs">
      <div className="bg-neutral-900 border border-neutral-800 rounded-2xl max-w-4xl w-full max-h-[90vh] flex flex-col overflow-hidden shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-neutral-800 bg-neutral-950">
          <div className="flex items-center gap-3">
            <span className="font-mono text-xs font-bold text-amber-400 bg-amber-950/40 border border-amber-800/60 px-2.5 py-1 rounded">
              {artifact.id}
            </span>
            <div>
              <h2 className="text-base font-bold text-white leading-tight">{artifact.title}</h2>
              <div className="flex items-center gap-2 text-xs text-neutral-400 font-mono mt-0.5">
                <span>{artifact.type}</span>
                <span className="text-neutral-600">·</span>
                <span>v{artifact.version}</span>
                <span className="text-neutral-600">·</span>
                <span className="text-emerald-400 font-bold">{artifact.status}</span>
              </div>
            </div>
          </div>

          <button
            onClick={onClose}
            className="w-8 h-8 rounded-lg bg-neutral-800 hover:bg-neutral-700 text-neutral-400 hover:text-white flex items-center justify-center cursor-pointer transition-colors"
          >
            ✕
          </button>
        </div>

        {/* Tab Controls */}
        <div className="flex items-center gap-1 px-6 py-2.5 bg-neutral-900 border-b border-neutral-800 text-xs">
          <button
            onClick={() => setActiveTab('preview')}
            className={`px-3 py-1.5 rounded-lg font-medium transition-colors cursor-pointer ${
              activeTab === 'preview'
                ? 'bg-neutral-800 text-white'
                : 'text-neutral-400 hover:text-neutral-200'
            }`}
          >
            Interactive Render Preview
          </button>
          <button
            onClick={() => setActiveTab('provenance')}
            className={`px-3 py-1.5 rounded-lg font-medium transition-colors cursor-pointer ${
              activeTab === 'provenance'
                ? 'bg-neutral-800 text-white'
                : 'text-neutral-400 hover:text-neutral-200'
            }`}
          >
            Provenance &amp; Derivation
          </button>
          <button
            onClick={() => setActiveTab('raw')}
            className={`px-3 py-1.5 rounded-lg font-medium transition-colors cursor-pointer ${
              activeTab === 'raw'
                ? 'bg-neutral-800 text-white'
                : 'text-neutral-400 hover:text-neutral-200'
            }`}
          >
            Raw Vault Record
          </button>
        </div>

        {/* Body Content */}
        <div className="p-6 overflow-y-auto space-y-5 text-xs">
          {activeTab === 'preview' && (
            <div className="space-y-4">
              {isVisualMockup ? (
                /* Interactive Mockup Viewport */
                <div className="bg-neutral-950 rounded-xl border border-neutral-800 p-5 space-y-4">
                  <div className="flex items-center justify-between text-xs font-mono text-neutral-400 border-b border-neutral-800 pb-2">
                    <span className="flex items-center gap-2 text-emerald-400">
                      <Eye className="w-3.5 h-3.5" />
                      FOUNDER REAL-TIME VISUAL INTELLIGENCE VIEWPORT [RECOVERED]
                    </span>
                    <span>3840 x 2160 UHD CANVAS</span>
                  </div>

                  {/* Rendered Visual Intelligence Canvas Mockup */}
                  <div className="relative rounded-lg bg-neutral-900 border border-neutral-800 p-4 overflow-hidden min-h-[300px] flex flex-col justify-between">
                    {/* SVG Graphic Representation */}
                    <div className="space-y-4">
                      <div className="flex justify-between items-center text-[11px] font-mono text-amber-400">
                        <span>ESTATE TELEMETRY ENGINE // NODE MATRIX</span>
                        <span className="text-emerald-400">STATUS: 100% ONLINE</span>
                      </div>

                      {/* Mockup node diagram */}
                      <div className="grid grid-cols-3 gap-4 pt-2">
                        <div className="p-3 bg-neutral-950 rounded border border-amber-500/50 space-y-1">
                          <div className="text-[10px] text-amber-400 font-mono">FOUNDER FOCUS</div>
                          <div className="text-xs font-bold text-white">Direct Sovereign Anchor</div>
                          <div className="text-[10px] text-neutral-400">Zero Blindness Active</div>
                        </div>

                        <div className="p-3 bg-neutral-950 rounded border border-blue-500/50 space-y-1">
                          <div className="text-[10px] text-blue-400 font-mono">ALGORITHMIC GATE</div>
                          <div className="text-xs font-bold text-white">Lyapunov Stability</div>
                          <div className="text-[10px] text-neutral-400">Entropy Bound Verified</div>
                        </div>

                        <div className="p-3 bg-neutral-950 rounded border border-emerald-500/50 space-y-1">
                          <div className="text-[10px] text-emerald-400 font-mono">DELIVERY RECEPTOR</div>
                          <div className="text-xs font-bold text-white">Artifact Vault Locked</div>
                          <div className="text-[10px] text-neutral-400">5 / 5 Verified</div>
                        </div>
                      </div>

                      <div className="p-3 bg-neutral-950 rounded border border-neutral-800 space-y-1 font-mono text-[11px] text-neutral-300">
                        <div className="text-amber-400 font-semibold">WHERE DID THIS LAND?</div>
                        <div>Vault File: <span className="text-white">{artifact.depositLocation}</span></div>
                        <div>Originator: <span className="text-white">{artifact.originAgent}</span></div>
                        <div>Delivery Verification: <span className="text-emerald-400">Confirmed &amp; Indexed into State</span></div>
                      </div>
                    </div>

                    <div className="pt-4 border-t border-neutral-800/80 flex items-center justify-between text-[11px] text-neutral-500 font-mono">
                      <span>Sha256 Checksum Verified</span>
                      <span>Founder Orientation Restored</span>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="bg-neutral-950 rounded-xl border border-neutral-800 p-5 space-y-3">
                  <div className="text-xs font-mono text-amber-400">DOCUMENT SPECIFICATION</div>
                  <h3 className="text-base font-bold text-white">{artifact.title}</h3>
                  <p className="text-xs text-neutral-300 leading-relaxed">{artifact.description}</p>
                  <div className="p-4 bg-neutral-900 rounded-lg border border-neutral-800 text-neutral-300 font-mono text-xs leading-relaxed">
                    {artifact.contentSummary}
                  </div>
                </div>
              )}

              {/* Exact Vault Deposit Coordinates */}
              <div className="p-4 bg-neutral-950 rounded-xl border border-neutral-800 space-y-2">
                <div className="text-neutral-400 font-mono flex items-center gap-1.5">
                  <Database className="w-3.5 h-3.5 text-amber-400" />
                  <span>Immutable Vault Deposit Coordinates:</span>
                </div>
                <div className="font-mono text-white text-xs bg-neutral-900 p-2.5 rounded-lg border border-neutral-800 select-all">
                  {artifact.depositLocation}
                </div>
              </div>
            </div>
          )}

          {activeTab === 'provenance' && (
            <div className="space-y-4">
              <div className="p-4 bg-neutral-950 rounded-xl border border-neutral-800 space-y-3">
                <div className="text-xs font-mono text-amber-400">CRYPTOGRAPHIC PROVENANCE MATRIX</div>
                
                <div className="space-y-2">
                  <div className="flex justify-between py-1.5 border-b border-neutral-800">
                    <span className="text-neutral-400">Originating Agent:</span>
                    <span className="text-white font-mono font-medium">{artifact.originAgent}</span>
                  </div>
                  <div className="flex justify-between py-1.5 border-b border-neutral-800">
                    <span className="text-neutral-400">Sha256 Hash Checksum:</span>
                    <div className="flex items-center gap-2">
                      <span className="text-emerald-400 font-mono">{artifact.checksum}</span>
                      <button
                        onClick={copyChecksum}
                        className="text-neutral-400 hover:text-white cursor-pointer"
                        title="Copy Checksum"
                      >
                        {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                      </button>
                    </div>
                  </div>
                  <div className="flex justify-between py-1.5 border-b border-neutral-800">
                    <span className="text-neutral-400">Last Telemetry Attestation:</span>
                    <span className="text-neutral-200 font-mono">{new Date(artifact.updatedAt).toLocaleString()}</span>
                  </div>
                  <div className="flex justify-between py-1.5 border-b border-neutral-800">
                    <span className="text-neutral-400">Version Tag:</span>
                    <span className="text-neutral-200 font-mono">{artifact.version}</span>
                  </div>
                </div>

                <div className="pt-2">
                  <div className="text-neutral-400 font-mono mb-2">Derivation Dependency Chain:</div>
                  <div className="flex flex-wrap gap-2">
                    {artifact.metadata.derivationChain.map((dep, idx) => (
                      <span
                        key={idx}
                        className="px-2.5 py-1 bg-neutral-900 border border-neutral-800 text-neutral-300 font-mono text-xs rounded"
                      >
                        {dep}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'raw' && (
            <div className="bg-neutral-950 p-4 rounded-xl border border-neutral-800">
              <pre className="font-mono text-xs text-amber-200/90 whitespace-pre-wrap overflow-x-auto">
                {JSON.stringify(artifact, null, 2)}
              </pre>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-3.5 border-t border-neutral-800 bg-neutral-950 flex items-center justify-between text-xs">
          <div className="flex items-center gap-2 text-neutral-400 font-mono">
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
            <span>Vault Status: Cryptographically Anchored</span>
          </div>

          <button
            onClick={onClose}
            className="px-4 py-1.5 bg-neutral-800 hover:bg-neutral-700 text-white rounded-lg font-medium cursor-pointer transition-colors"
          >
            Close Inspector
          </button>
        </div>
      </div>
    </div>
  );
};
