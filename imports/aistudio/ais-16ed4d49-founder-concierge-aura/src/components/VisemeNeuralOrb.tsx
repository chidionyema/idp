import React, { useEffect, useRef } from 'react';

interface VisemeOrbProps {
  active: boolean;
  energy: number;
  mode: 'listening' | 'speaking' | 'idle' | 'executing';
  onClick: () => void;
  disabled?: boolean;
}

export const VisemeNeuralOrb: React.FC<VisemeOrbProps> = ({
  active,
  energy,
  mode,
  onClick,
  disabled = false,
}) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animationFrameId: number;
    let phase = 0;

    const render = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      const centerX = canvas.width / 2;
      const centerY = canvas.height / 2;
      const baseRadius = 58;

      // Pulse dynamics based on energy and mode
      phase += 0.04 + energy * 0.08;
      const currentRadius = baseRadius + Math.sin(phase) * (active ? 6 + energy * 18 : 2);

      // Outer ethereal glow ring
      const gradient = ctx.createRadialGradient(
        centerX,
        centerY,
        baseRadius * 0.5,
        centerX,
        centerY,
        currentRadius * 1.6
      );

      if (mode === 'speaking') {
        gradient.addColorStop(0, 'rgba(0, 245, 212, 0.6)');
        gradient.addColorStop(0.5, 'rgba(16, 185, 129, 0.25)');
        gradient.addColorStop(1, 'rgba(0, 245, 212, 0)');
      } else if (mode === 'listening') {
        gradient.addColorStop(0, 'rgba(56, 189, 248, 0.6)');
        gradient.addColorStop(0.5, 'rgba(99, 102, 241, 0.25)');
        gradient.addColorStop(1, 'rgba(56, 189, 248, 0)');
      } else if (mode === 'executing') {
        gradient.addColorStop(0, 'rgba(245, 158, 11, 0.6)');
        gradient.addColorStop(0.5, 'rgba(234, 88, 12, 0.25)');
        gradient.addColorStop(1, 'rgba(245, 158, 11, 0)');
      } else {
        gradient.addColorStop(0, 'rgba(100, 116, 139, 0.2)');
        gradient.addColorStop(0.7, 'rgba(71, 85, 105, 0.05)');
        gradient.addColorStop(1, 'rgba(15, 23, 42, 0)');
      }

      ctx.fillStyle = gradient;
      ctx.beginPath();
      ctx.arc(centerX, centerY, currentRadius * 1.6, 0, Math.PI * 2);
      ctx.fill();

      // Reactive waveform viseme rings
      const rings = active ? 3 : 1;
      for (let i = 0; i < rings; i++) {
        ctx.beginPath();
        const ringRadius = currentRadius - i * 8 + (active ? Math.sin(phase + i * 1.2) * 5 * energy : 0);
        ctx.arc(centerX, centerY, Math.max(10, ringRadius), 0, Math.PI * 2);
        ctx.strokeStyle =
          mode === 'speaking'
            ? `rgba(0, 245, 212, ${0.8 - i * 0.25})`
            : mode === 'listening'
            ? `rgba(56, 189, 248, ${0.8 - i * 0.25})`
            : mode === 'executing'
            ? `rgba(245, 158, 11, ${0.8 - i * 0.25})`
            : 'rgba(148, 163, 184, 0.3)';
        ctx.lineWidth = 1.5;
        ctx.stroke();
      }

      // Harmonic frequency spikes when active
      if (active) {
        const spikes = 24;
        ctx.strokeStyle = mode === 'speaking' ? '#00F5D4' : '#38BDF8';
        ctx.lineWidth = 1.2;
        for (let j = 0; j < spikes; j++) {
          const angle = (j / spikes) * Math.PI * 2 + phase * 0.5;
          const spikeLength = 4 + Math.sin(phase * 2 + j * 0.8) * 12 * energy;
          const x1 = centerX + Math.cos(angle) * (currentRadius - 2);
          const y1 = centerY + Math.sin(angle) * (currentRadius - 2);
          const x2 = centerX + Math.cos(angle) * (currentRadius + spikeLength);
          const y2 = centerY + Math.sin(angle) * (currentRadius + spikeLength);

          ctx.beginPath();
          ctx.moveTo(x1, y1);
          ctx.lineTo(x2, y2);
          ctx.stroke();
        }
      }

      // Inner core sphere
      ctx.beginPath();
      ctx.arc(centerX, centerY, 34, 0, Math.PI * 2);
      ctx.fillStyle = '#060B14';
      ctx.fill();
      ctx.strokeStyle = active
        ? (mode === 'speaking' ? '#00F5D4' : mode === 'listening' ? '#38BDF8' : '#F59E0B')
        : '#334155';
      ctx.lineWidth = 1.5;
      ctx.stroke();

      animationFrameId = requestAnimationFrame(render);
    };

    render();

    return () => {
      cancelAnimationFrame(animationFrameId);
    };
  }, [active, energy, mode]);

  return (
    <button
      onClick={onClick}
      disabled={disabled}
      aria-label="Toggle voice concierge"
      className="relative flex items-center justify-center p-0 bg-transparent border-0 rounded-full cursor-pointer focus:outline-none transition-transform hover:scale-105 active:scale-95 disabled:opacity-40 disabled:cursor-not-allowed group"
    >
      <canvas
        ref={canvasRef}
        width={240}
        height={240}
        className="w-56 h-56"
      />
      <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none select-none">
        <span className="text-[10px] tracking-[0.28em] uppercase font-semibold text-slate-400 group-hover:text-white transition-colors">
          {mode === 'listening'
            ? 'LISTENING'
            : mode === 'speaking'
            ? 'SPEAKING'
            : mode === 'executing'
            ? 'EXECUTING'
            : 'CONCIERGE'}
        </span>
        <span className="text-[9px] font-mono text-slate-500 mt-1">
          {disabled
            ? 'OFFLINE'
            : active
            ? 'TAP TO MUTE'
            : 'TAP TO TALK'}
        </span>
      </div>
    </button>
  );
};
