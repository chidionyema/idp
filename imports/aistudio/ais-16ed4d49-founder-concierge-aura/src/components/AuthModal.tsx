import React, { useState } from 'react';
import { Shield, Key, CheckCircle, RefreshCw } from 'lucide-react';

interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSaveCredentials: (creds: { cfAccessJwt: string; ed25519Signature: string }) => void;
  currentJwt: string;
  currentSignature: string;
}

export const AuthModal: React.FC<AuthModalProps> = ({
  isOpen,
  onClose,
  onSaveCredentials,
  currentJwt,
  currentSignature,
}) => {
  const [jwt, setJwt] = useState(currentJwt);
  const [signature, setSignature] = useState(currentSignature);

  if (!isOpen) return null;

  const handleGenerateLocalEd25519 = async () => {
    // Generate a fresh local demo keypair or test signature
    const randomHex = Array.from(crypto.getRandomValues(new Uint8Array(64)))
      .map((b) => b.toString(16).padStart(2, '0'))
      .join('');
    setSignature(randomHex);
  };

  const handleSave = () => {
    onSaveCredentials({
      cfAccessJwt: jwt.trim(),
      ed25519Signature: signature.trim(),
    });
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-md">
      <div className="w-full max-w-lg rounded-2xl bg-[#090D16] border border-white/15 p-6 shadow-2xl space-y-5">
        <div className="flex items-center justify-between border-b border-white/10 pb-4">
          <div className="flex items-center gap-2.5">
            <Shield className="w-5 h-5 text-emerald-400" />
            <h2 className="text-base font-semibold text-white">Founder Security Credentials</h2>
          </div>
          <button
            onClick={onClose}
            className="text-xs font-mono text-slate-400 hover:text-white"
          >
            ESC / Close
          </button>
        </div>

        <p className="text-xs text-slate-300 leading-relaxed">
          In strict compliance with IDP #7664 and Argon #20 security rules, anonymous mutations are strictly rejected. Commands require Cloudflare Access Zero-Trust JWTs or Ed25519 cryptographic signatures.
        </p>

        <div className="space-y-4">
          <div>
            <label className="block text-xs font-mono uppercase tracking-wider text-slate-400 mb-1.5 flex items-center gap-1.5">
              <Key className="w-3.5 h-3.5 text-cyan-400" />
              <span>Cloudflare Access JWT (Cf-Access-Jwt-Assertion)</span>
            </label>
            <textarea
              value={jwt}
              onChange={(e) => setJwt(e.target.value)}
              placeholder="eyJhbGciOiJSUzI1NiIs..."
              rows={3}
              className="w-full bg-black/50 border border-white/10 rounded-xl px-3.5 py-2.5 text-xs font-mono text-slate-200 placeholder-slate-600 focus:outline-none focus:border-cyan-500/50"
            />
            <span className="text-[11px] text-slate-500">
              Header verified against CF_ACCESS_TEAM_DOMAIN and AUD tags.
            </span>
          </div>

          <div>
            <label className="block text-xs font-mono uppercase tracking-wider text-slate-400 mb-1.5 flex items-center justify-between">
              <span className="flex items-center gap-1.5">
                <Shield className="w-3.5 h-3.5 text-emerald-400" />
                <span>Ed25519 Signature (X-Genesis-Signature)</span>
              </span>
              <button
                type="button"
                onClick={handleGenerateLocalEd25519}
                className="text-[11px] text-emerald-400 hover:text-emerald-300 flex items-center gap-1"
              >
                <RefreshCw className="w-3 h-3" />
                <span>Generate Test Key/Sig</span>
              </button>
            </label>
            <input
              type="text"
              value={signature}
              onChange={(e) => setSignature(e.target.value)}
              placeholder="e.g. 7f83b1657ff1fc53b92dc18148a1d65dfc2d4b1fa3d677284addd200126d9069..."
              className="w-full bg-black/50 border border-white/10 rounded-xl px-3.5 py-2 text-xs font-mono text-slate-200 placeholder-slate-600 focus:outline-none focus:border-emerald-500/50"
            />
            <span className="text-[11px] text-slate-500">
              Canonical payload signature verified within a 60-second replay window.
            </span>
          </div>
        </div>

        <div className="flex items-center justify-end gap-3 pt-4 border-t border-white/10">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-xl text-xs font-medium text-slate-400 hover:text-white"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            className="flex items-center gap-2 px-5 py-2 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-semibold text-xs tracking-wider uppercase transition-colors"
          >
            <CheckCircle className="w-4 h-4" />
            <span>Apply Credentials</span>
          </button>
        </div>
      </div>
    </div>
  );
};
