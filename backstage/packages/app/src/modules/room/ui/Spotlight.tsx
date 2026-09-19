// ui/Spotlight.tsx
// The named agent detaches from the swarm, glides to the center, grows, and
// speaks. You do not find it on a grid. It comes to you.

import React, { useEffect, useState } from 'react';
import type { AgentId, Provenance } from '../core/types';

export interface SpotlightProps {
  readonly agentId: AgentId;
  readonly provenance: Provenance;
  readonly onRelease: () => void;
}

export function Spotlight(props: SpotlightProps): JSX.Element {
  const { agentId, provenance, onRelease } = props;
  const [phase, setPhase] = useState<'arriving' | 'present' | 'leaving'>('arriving');

  useEffect(() => {
    const t1 = setTimeout(() => setPhase('present'), 800);
    return () => clearTimeout(t1);
  }, []);

  // Escape releases. Accessibility: any modality can dismiss.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') { setPhase('leaving'); setTimeout(onRelease, 400); }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onRelease]);

  const transform =
    phase === 'arriving' ? 'scale(0.3)' :
    phase === 'leaving'  ? 'scale(0.3)' :
    'scale(1)';

  return (
    <div
      role="dialog"
      aria-label={`Agent ${agentId}`}
      style={{
        position: 'absolute',
        inset: 0,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        pointerEvents: 'none',
        transition: 'opacity 400ms ease-out',
        opacity: phase === 'present' ? 1 : 0,
      }}
    >
      <div
        style={{
          width: '33vw',
          maxWidth: 520,
          minWidth: 280,
          padding: 32,
          borderRadius: 24,
          background: 'rgba(20, 14, 6, 0.85)',
          border: '1px solid rgba(255, 196, 120, 0.25)',
          boxShadow: '0 24px 80px rgba(255, 180, 80, 0.15)',
          transform,
          transition: 'transform 800ms cubic-bezier(0.16, 1, 0.3, 1)',
          color: '#f0e4c8',
          backdropFilter: 'blur(12px)',
          pointerEvents: 'auto',
        }}
      >
        <div style={{ fontSize: 12, letterSpacing: 2, opacity: 0.6 }}>
          {provenance.regionId} · {provenance.modelId}
        </div>
        <div style={{ fontSize: 28, marginTop: 8, marginBottom: 16 }}>
          {agentId}
        </div>
        <div style={{ fontSize: 14, lineHeight: 1.6, opacity: 0.85 }}>
          {provenance.reason}
        </div>
        <div style={{ marginTop: 20, fontSize: 12, opacity: 0.5 }}>
          ${provenance.cost.usd.toFixed(4)} · {provenance.cost.latencyMs}ms
        </div>
      </div>
    </div>
  );
}
