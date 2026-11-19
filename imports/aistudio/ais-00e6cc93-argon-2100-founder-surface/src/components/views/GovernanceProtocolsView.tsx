import React, { useState } from 'react';
import { Shield, CheckCircle2, AlertOctagon, Terminal, FileCode, Check, RefreshCw } from 'lucide-react';
import { validateAsciiFirewall, EstateState } from '../../utils/estateLogic';

interface GovernanceProtocolsViewProps {
  estateState: EstateState;
  onRemediateLegion: () => void;
}

export const GovernanceProtocolsView: React.FC<GovernanceProtocolsViewProps> = ({
  estateState,
  onRemediateLegion,
}) => {
  const sampleCorruptedFile = `// founder-gateway/src/index.ts
// Estate Gateway Orchestrator — Genesis Spine Link
import { initializeSpine } from './spine';

export const gateway = {
  version: "2.1.0",
  author: "Argon Team",
  description: "Synchronous founder gateway – zero non-ASCII",
};`;

  const [testCode, setTestCode] = useState(sampleCorruptedFile);
  const [validationResult, setValidationResult] = useState(() => validateAsciiFirewall(sampleCorruptedFile));
  const [sanitizedMessage, setSanitizedMessage] = useState(false);

  const handleTestCodeChange = (newCode: string) => {
    setTestCode(newCode);
    setValidationResult(validateAsciiFirewall(newCode));
    setSanitizedMessage(false);
  };

  const handleSanitizeCode = () => {
    // Replace non-ASCII chars with ASCII equivalents
    const cleaned = testCode
      .replace(/[\u2014\u2013]/g, '-')
      .replace(/[\u2018\u2019]/g, "'")
      .replace(/[\u201C\u201D]/g, '"')
      .replace(/[^\x00-\x7F]/g, '');

    setTestCode(cleaned);
    setValidationResult(validateAsciiFirewall(cleaned));
    setSanitizedMessage(true);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <div className="flex items-center gap-2 text-xs font-mono text-slate-400">
            <span>Estate Operations</span>
            <span>/</span>
            <span className="text-sky-400">Protocols &amp; Governance</span>
          </div>
          <h2 className="text-xl font-bold text-white tracking-tight mt-1">
            Governance, Transcript Firewall &amp; Trusted Push Gate
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Enforcing strict coding standards, Ruff validation, transcript firewall containment, and ASCII character integrity across all agent merges.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs font-mono">
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>Ruff Linter: Clean</span>
          </div>
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs font-mono">
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>Transcript Firewall: Sealed</span>
          </div>
        </div>
      </div>

      {/* Protocols Status Matrix */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/60">
          <div className="flex items-center justify-between">
            <h4 className="text-xs font-bold text-white">Ruff Formatter &amp; Linter</h4>
            <span className="text-xs font-mono text-emerald-400">100% Passing</span>
          </div>
          <p className="text-xs text-slate-400 mt-2">
            Automated Python and TypeScript AST verification. All syntax rules, import ordering, and type safety constraints validated.
          </p>
        </div>

        <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/60">
          <div className="flex items-center justify-between">
            <h4 className="text-xs font-bold text-white">Transcript Firewall</h4>
            <span className="text-xs font-mono text-emerald-400">Active Strict</span>
          </div>
          <p className="text-xs text-slate-400 mt-2">
            Prevents leaking internal agent thought chains, private tokens, or unverified instructions across boundary borders.
          </p>
        </div>

        <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/60">
          <div className="flex items-center justify-between">
            <h4 className="text-xs font-bold text-white">Trusted Push Encoding Gate</h4>
            <span className={`text-xs font-mono ${validationResult.valid ? 'text-emerald-400' : 'text-amber-400'}`}>
              {validationResult.valid ? 'Enforced & Clean' : 'Violations Detected'}
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-2">
            Blocks non-ASCII characters (&gt; 127 char code) from entering production repositories to avoid deployment pipeline crashes.
          </p>
        </div>
      </div>

      {/* Interactive ASCII / Encoding Firewall Validator */}
      <div className="rounded-2xl border border-slate-800 bg-slate-950/80 p-5 spatial-grid">
        <div className="flex flex-wrap items-center justify-between gap-4 pb-3 border-b border-slate-800">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-mono text-sky-400 uppercase tracking-wider">Trusted Push Gate Console</span>
              <span className="text-xs text-slate-500">·</span>
              <span className="text-xs font-mono text-slate-400">Legion Recovery #42412348112 Remediation Lab</span>
            </div>
            <h3 className="text-sm font-semibold text-white mt-0.5">
              Source Code ASCII Range Verifier (&le; 127)
            </h3>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleSanitizeCode}
              disabled={validationResult.valid}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-sky-600 hover:bg-sky-500 disabled:opacity-40 text-white transition-colors"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Sanitize Non-ASCII Chars</span>
            </button>
            <button
              onClick={() => onRemediateLegion()}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white transition-colors"
            >
              <Check className="w-3.5 h-3.5" />
              <span>Certify &amp; Push to Fleet</span>
            </button>
          </div>
        </div>

        {sanitizedMessage && (
          <div className="p-3 my-3 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4" />
            <span>Code successfully sanitized to 100% clean ASCII! Trusted push verification passed.</span>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 mt-4">
          <div className="lg:col-span-7">
            <div className="flex justify-between items-center text-xs font-mono text-slate-400 mb-2">
              <span>Source File Buffer (founder-gateway/src/index.ts)</span>
              <span>{testCode.length} bytes</span>
            </div>
            <textarea
              value={testCode}
              onChange={(e) => handleTestCodeChange(e.target.value)}
              rows={9}
              className="w-full rounded-xl bg-slate-900 border border-slate-700 p-3 font-mono text-xs text-slate-200 focus:outline-none focus:border-sky-500"
            />
          </div>

          <div className="lg:col-span-5 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between pb-2 border-b border-slate-800">
                <span className="text-xs font-mono text-slate-400">Firewall Gate Status</span>
                <span className={`text-xs font-mono font-bold ${validationResult.valid ? 'text-emerald-400' : 'text-red-400'}`}>
                  {validationResult.valid ? 'PASSED CLEAN' : 'PUSH BLOCKED'}
                </span>
              </div>

              {validationResult.valid ? (
                <div className="p-4 rounded-xl bg-slate-900/40 border border-slate-800 text-center my-4">
                  <CheckCircle2 className="w-8 h-8 text-emerald-400 mx-auto" />
                  <p className="text-xs text-slate-300 font-mono mt-2 font-bold">Zero Non-ASCII Violations</p>
                  <p className="text-xs text-slate-500 mt-1">This file is ready for trusted push into production branches.</p>
                </div>
              ) : (
                <div className="my-3 space-y-2">
                  <span className="text-xs font-mono text-red-400 font-bold block">
                    {validationResult.violations.length} Non-ASCII Characters Flagged:
                  </span>
                  <div className="max-h-40 overflow-y-auto space-y-1.5 font-mono text-xs">
                    {validationResult.violations.map((v, i) => (
                      <div key={i} className="p-2 rounded bg-red-950/30 border border-red-500/30 text-red-300 flex justify-between">
                        <span>Line {v.line}: char '{v.character}'</span>
                        <span className="text-slate-400">code: 0x{v.charCode.toString(16)} ({v.charCode})</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            <div className="text-xs text-slate-500 font-mono">
              Note: Legion recovery run #42412348112 resolves this exact issue by stripping non-ASCII glyphs before git push.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
