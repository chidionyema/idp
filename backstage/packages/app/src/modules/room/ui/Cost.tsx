// ui/Cost.tsx
// The cost is felt, not read. A warmth in the air. A dimming. A slowing.
// The number is always available, but never in your face.

import React from 'react';
import type { Cost } from '../core/types';

export interface CostGlowProps {
  readonly cost: Cost;
  readonly pressure: number; // 0..1
}

export function CostGlow({ cost, pressure }: CostGlowProps): JSX.Element {
  const warmth = Math.min(0.35, pressure * 0.35);
  return (
    <div
      aria-hidden="true"
      style={{
        position: 'absolute',
        inset: 0,
        pointerEvents: 'none',
        background: `radial-gradient(ellipse at 50% 110%, rgba(255, 140, 60, ${warmth}) 0%, rgba(0,0,0,0) 60%)`,
        transition: 'background 1500ms ease-out',
      }}
    >
      <span
        style={{
          position: 'absolute',
          top: 24,
          right: 24,
          fontSize: 11,
          letterSpacing: 1,
          color: '#a89670',
          opacity: 0.6,
        }}
      >
        ${cost.usd.toFixed(4)} · {cost.carbonGrams.toFixed(1)}g
      </span>
    </div>
  );
}
