// ui/Room.tsx
// The full-bleed shell. No panel. No section. The room IS the viewport.
// Everything else floats over it. The cursor is not hidden — it is optional.

import { useEffect, useState } from 'react';
import { SpatialCanvas } from './SpatialCanvas';
import { Spotlight } from './Spotlight';
import { Waveform } from './Waveform';
import { CostGlow } from './Cost';
import type { UserId, AgentId, Provenance, Cost } from '../core/types';
import type { EventBus, RoomEvents } from '../core/events';

export interface RoomProps {
  readonly userId: UserId;
  readonly events: EventBus<RoomEvents>;
  readonly onWakeWord?: (word: string) => void;
  readonly onAddress?: (agentId: AgentId) => void;
  readonly onLeave?: () => void;
}

export function Room(props: RoomProps): JSX.Element {
  const { userId, events } = props;
  const [awake, setAwake] = useState(false);
  const [speaking, setSpeaking] = useState(false);
  const [spotlight, setSpotlight] = useState<AgentId | null>(null);
  const [cost, setCost] = useState<Cost>({
    usd: 0, carbonGrams: 0, latencyMs: 0, trustPenalty: 0,
  });
  const [lastProvenance, setLastProvenance] = useState<Provenance | null>(null);

  useEffect(() => {
    const off1 = events.on('room:wake', () => setAwake(true));
    const off2 = events.on('room:dim', () => setAwake(false));
    const off3 = events.on('voice:partial', () => setSpeaking(true));
    const off4 = events.on('voice:silence', () => setSpeaking(false));
    const off5 = events.on('agent:spotlighted', (e) => setSpotlight(e.agentId));
    const off6 = events.on('agent:released', () => setSpotlight(null));
    const off7 = events.on('cost:incurred', (e) => {
      setCost((c) => ({
        usd: c.usd + e.cost.usd,
        carbonGrams: c.carbonGrams + e.cost.carbonGrams,
        latencyMs: c.latencyMs + e.cost.latencyMs,
        trustPenalty: c.trustPenalty + e.cost.trustPenalty,
      }));
    });
    const off8 = events.on('route:chosen', (e) => setLastProvenance(e.provenance));
    return () => { off1(); off2(); off3(); off4(); off5(); off6(); off7(); off8(); };
  }, [events]);

  // Arrival: the room notices you. No button. No wake word.
  useEffect(() => {
    const at = Date.now();
    events.emit('user:arrived', { userId, at });
    const t = setTimeout(() => {
      // If nothing happens for a while, dim. The room does not demand.
      events.emit('room:dim', { at: Date.now() });
    }, 60_000);
    return () => {
      clearTimeout(t);
      events.emit('user:left', { userId, at: Date.now() });
      props.onLeave?.();
    };
  }, [events, userId, props]);

  return (
    <div
      role="application"
      aria-label="The Room"
      style={{
        position: 'fixed',
        inset: 0,
        background: awake
          ? 'radial-gradient(ellipse at 50% 40%, #1a1206 0%, #050505 75%)'
          : 'radial-gradient(ellipse at 50% 40%, #0a0a14 0%, #000 75%)',
        overflow: 'hidden',
        transition: 'background 1200ms ease-out',
        color: '#e8dcc0',
        fontFamily: 'system-ui, -apple-system, sans-serif',
        // Accessibility: the room is keyboard-navigable even though it is
        // voice-first. Tab order is explicit.
        outline: 'none',
      }}
      tabIndex={-1}
    >
      <SpatialCanvas
        events={events}
        spotlight={spotlight}
        awake={awake}
      />
      {spotlight && lastProvenance && (
        <Spotlight
          agentId={spotlight}
          provenance={lastProvenance}
          onRelease={() => {
            events.emit('agent:released', {
              agentId: spotlight, at: Date.now(),
            });
          }}
        />
      )}
      <Waveform active={speaking} awake={awake} />
      <CostGlow cost={cost} pressure={cost.usd / 5} />
      <ProvenanceLine provenance={lastProvenance} />
    </div>
  );
}

function ProvenanceLine({ provenance }: { provenance: Provenance | null }) {
  if (!provenance) return null;
  return (
    <div
      aria-live="polite"
      style={{
        position: 'absolute',
        bottom: 24,
        left: 24,
        fontSize: 11,
        letterSpacing: 0.5,
        color: '#a89670',
        opacity: 0.7,
        maxWidth: 520,
        pointerEvents: 'none',
      }}
    >
      {provenance.modelId} · {provenance.regionId} · $
      {provenance.cost.usd.toFixed(4)} · {provenance.reason}
    </div>
  );
}
