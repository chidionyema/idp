/**
 * <EstateFace/>: the estate's talking head, mounted wherever the estate speaks. While it is on
 * screen it owns the voice's output (setClauseSink), so every clause the estate says comes out of
 * its mouth, lip-synced; unmounted, the voice speaks exactly as it did before.
 */
import { useEffect, useRef, useState } from 'react';
import { mountFace, type EstateFace as Face } from './faceEngine';
import { setClauseSink } from './useEstateVoice';

export default function EstateFace({ height = 360 }: { height?: number | string }) {
  const el = useRef<HTMLDivElement | null>(null);
  const [status, setStatus] = useState<'loading' | 'ready' | 'failed'>('loading');
  const [why, setWhy] = useState('');
  // CONTINUITY: the line this visit earns, from memory the previous visit left behind. Rendered
  // under the face while the visitor has not yet spoken -- "welcome back, visit 3" is the visible
  // proof that the face remembers them, not a fresh mount.
  const [greet, setGreet] = useState('');

  useEffect(() => {
    let face: Face | null = null;
    let gone = false;
    if (!el.current) return undefined;
    mountFace(el.current)
      .then((f) => {
        if (gone) return f.dispose();
        face = f;
        setClauseSink(f);
        setGreet(f.greet());
        setStatus('ready');
        return undefined;
      })
      .catch((e) => {
        setStatus('failed');
        setWhy(String(e?.message || e));
      });
    return () => {
      gone = true;
      setClauseSink(null);
      face?.dispose();
    };
  }, []);

  return (
    <div style={{ position: 'relative', width: '100%', height }} aria-label="Estate face">
      <div ref={el} style={{ position: 'absolute', inset: 0 }} />
      {status === 'ready' && greet && (
        <div
          style={{
            position: 'absolute',
            left: '50%',
            transform: 'translateX(-50%)',
            bottom: 12,
            fontSize: 13,
            letterSpacing: '0.02em',
            color: 'rgba(232,237,245,0.72)',
            textShadow: '0 1px 8px rgba(11,14,20,0.8)',
            pointerEvents: 'none',
          }}
        >
          {greet}
        </div>
      )}
      {status !== 'ready' && (
        <div
          role="status"
          style={{ position: 'absolute', inset: 0, display: 'grid', placeItems: 'center', opacity: 0.7 }}
        >
          {status === 'loading' ? 'Waking the face…' : `The face could not load: ${why}. The voice still works.`}
        </div>
      )}
    </div>
  );
}
