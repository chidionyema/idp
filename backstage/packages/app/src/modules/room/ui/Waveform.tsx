// ui/Waveform.tsx
// The room shows it is listening. Not a red dot — a breath. When the user
// speaks, the breath quickens. When the room is awake, it glows. When the
// room is dim, it is barely there.

import { useEffect, useRef } from 'react';

export interface WaveformProps {
  readonly active: boolean;
  readonly awake: boolean;
}

export function Waveform({ active, awake }: WaveformProps): JSX.Element {
  const ref = useRef<HTMLCanvasElement | null>(null);
  const raf = useRef(0);
  const t0 = useRef(performance.now());

  useEffect(() => {
    const c = ref.current;
    if (!c) return;
    const ctx = c.getContext('2d');
    if (!ctx) return;

    const draw = () => {
      const w = c.clientWidth;
      const h = c.clientHeight;
      const dpr = window.devicePixelRatio || 1;
      if (c.width !== w * dpr || c.height !== h * dpr) {
        c.width = w * dpr; c.height = h * dpr;
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      }
      ctx.clearRect(0, 0, w, h);

      const t = (performance.now() - t0.current) / 1000;
      const amp = active ? 1 : awake ? 0.35 : 0.08;
      const speed = active ? 3 : awake ? 1.2 : 0.5;

      ctx.strokeStyle = `rgba(255, 196, 120, ${0.5 + amp * 0.5})`;
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      for (let x = 0; x < w; x++) {
        const p = x / w;
        const y = h / 2 +
          Math.sin(p * 12 + t * speed) * h * 0.12 * amp +
          Math.sin(p * 27 + t * speed * 1.7) * h * 0.06 * amp;
        if (x === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
      }
      ctx.stroke();
      raf.current = requestAnimationFrame(draw);
    };
    raf.current = requestAnimationFrame(draw);
    return () => cancelAnimationFrame(raf.current);
  }, [active, awake]);

  return (
    <canvas
      ref={ref}
      aria-hidden="true"
      style={{
        position: 'absolute',
        bottom: 0,
        left: 0,
        width: '100%',
        height: 64,
        pointerEvents: 'none',
      }}
    />
  );
}
