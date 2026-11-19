/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useRef, useEffect } from 'react';
import {
  EstateSubsystemId,
  TOPOLOGICAL_NODES,
} from './AlienTopologicalEstateSurface.tsx';

interface Alien2DTopologicalCanvasProps {
  selectedSubsystem: EstateSubsystemId;
  onSelectSubsystem: (id: EstateSubsystemId) => void;
  hoveredSubsystem: EstateSubsystemId | null;
  setHoveredSubsystem: (id: EstateSubsystemId | null) => void;
  explodedSeparation: number;
  zenDriftEnabled: boolean;
  onPlayChime?: (freq: number) => void;
}

interface StardustPoint {
  x: number;
  y: number;
  vx: number;
  vy: number;
  radius: number;
  alpha: number;
  color: string;
}

interface PhotonPacket {
  targetId: EstateSubsystemId;
  progress: number;
  speed: number;
  color: string;
}

export const Alien2DTopologicalCanvas: React.FC<Alien2DTopologicalCanvasProps> = ({
  selectedSubsystem,
  onSelectSubsystem,
  hoveredSubsystem,
  setHoveredSubsystem,
  explodedSeparation,
  zenDriftEnabled,
  onPlayChime,
}) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);

  // References for render loop
  const stateRef = useRef({
    selectedSubsystem,
    hoveredSubsystem,
    explodedSeparation,
    zenDriftEnabled,
    angleOffset: 0,
    stardust: [] as StardustPoint[],
    photons: [] as PhotonPacket[],
    nodeScreenCoords: new Map<EstateSubsystemId, { x: number; y: number; r: number }>(),
  });

  // Keep refs in sync with props
  useEffect(() => {
    stateRef.current.selectedSubsystem = selectedSubsystem;
    stateRef.current.hoveredSubsystem = hoveredSubsystem;
    stateRef.current.explodedSeparation = explodedSeparation;
    stateRef.current.zenDriftEnabled = zenDriftEnabled;
  }, [selectedSubsystem, hoveredSubsystem, explodedSeparation, zenDriftEnabled]);

  useEffect(() => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container) return;

    const ctx = canvas.getContext('2d', { alpha: false });
    if (!ctx) return;

    // Initialize Stardust (140 celestial points)
    const stardustColors = ['#38bdf8', '#818cf8', '#34d399', '#f59e0b', '#a78bfa'];
    const stardust: StardustPoint[] = [];
    for (let i = 0; i < 140; i++) {
      stardust.push({
        x: Math.random(),
        y: Math.random(),
        vx: (Math.random() - 0.5) * 0.00015,
        vy: (Math.random() - 0.5) * 0.00015,
        radius: 0.8 + Math.random() * 1.6,
        alpha: 0.2 + Math.random() * 0.7,
        color: stardustColors[Math.floor(Math.random() * stardustColors.length)],
      });
    }
    stateRef.current.stardust = stardust;

    // Initialize Photon Packets along branches
    const allNodeIds = Object.keys(TOPOLOGICAL_NODES) as EstateSubsystemId[];
    const targetNodeIds = allNodeIds.filter((id) => id !== 'SOVEREIGN_NUCLEUS');
    const photons: PhotonPacket[] = [];
    for (let i = 0; i < 22; i++) {
      const targetId = targetNodeIds[i % targetNodeIds.length];
      photons.push({
        targetId,
        progress: Math.random(),
        speed: 0.004 + Math.random() * 0.006,
        color: TOPOLOGICAL_NODES[targetId]?.accentColor || '#38bdf8',
      });
    }
    stateRef.current.photons = photons;

    let animFrameId = 0;
    let lastTime = performance.now();

    const resize = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      const width = container.clientWidth || 800;
      const height = container.clientHeight || 600;
      canvas.width = width * dpr;
      canvas.height = height * dpr;
      canvas.style.width = `${width}px`;
      canvas.style.height = `${height}px`;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };

    resize();
    window.addEventListener('resize', resize);

    const render = (now: number) => {
      const dt = (now - lastTime) / 1000;
      lastTime = now;

      const width = container.clientWidth || 800;
      const height = container.clientHeight || 600;
      const cx = width / 2;
      const cy = height / 2;

      // Update cosmic rotation drift
      if (stateRef.current.zenDriftEnabled) {
        stateRef.current.angleOffset += dt * 0.08;
      }

      // Background - Deep Cosmic Gradient
      const bgGrad = ctx.createRadialGradient(cx, cy, 50, cx, cy, Math.max(width, height) * 0.8);
      bgGrad.addColorStop(0, '#040d1a');
      bgGrad.addColorStop(0.4, '#020713');
      bgGrad.addColorStop(1, '#010307');
      ctx.fillStyle = bgGrad;
      ctx.fillRect(0, 0, width, height);

      // Deep galactic nebula clouds
      ctx.save();
      const nebula1 = ctx.createRadialGradient(cx - 140, cy - 80, 20, cx - 140, cy - 80, 320);
      nebula1.addColorStop(0, 'rgba(6, 182, 212, 0.08)');
      nebula1.addColorStop(1, 'rgba(0, 0, 0, 0)');
      ctx.fillStyle = nebula1;
      ctx.fillRect(0, 0, width, height);

      const nebula2 = ctx.createRadialGradient(cx + 180, cy + 120, 20, cx + 180, cy + 120, 340);
      nebula2.addColorStop(0, 'rgba(139, 92, 246, 0.07)');
      nebula2.addColorStop(1, 'rgba(0, 0, 0, 0)');
      ctx.fillStyle = nebula2;
      ctx.fillRect(0, 0, width, height);
      ctx.restore();

      // Render Stardust Points
      ctx.save();
      for (const p of stateRef.current.stardust) {
        p.x = (p.x + p.vx + 1) % 1;
        p.y = (p.y + p.vy + 1) % 1;

        const px = p.x * width;
        const py = p.y * height;

        ctx.fillStyle = p.color;
        ctx.globalAlpha = p.alpha * (0.6 + Math.sin(now * 0.002 + p.x * 20) * 0.3);
        ctx.beginPath();
        ctx.arc(px, py, p.radius, 0, Math.PI * 2);
        ctx.fill();
      }
      ctx.restore();

      // Render Concentric Holographic Runic Rings
      ctx.save();
      const ringRot = stateRef.current.angleOffset;
      const baseScale = Math.min(width, height) / 780;
      const sep = stateRef.current.explodedSeparation;

      const ringRadii = [90 * baseScale * sep, 180 * baseScale * sep, 280 * baseScale * sep];
      ringRadii.forEach((r, idx) => {
        ctx.strokeStyle = idx === 0 ? 'rgba(56, 189, 248, 0.28)' : idx === 1 ? 'rgba(129, 140, 248, 0.18)' : 'rgba(52, 211, 153, 0.14)';
        ctx.lineWidth = 1;
        ctx.setLineDash(idx === 1 ? [6, 8] : idx === 2 ? [3, 9] : []);
        ctx.beginPath();
        ctx.arc(cx, cy, r, 0, Math.PI * 2);
        ctx.stroke();

        // Cardinal tick marks
        ctx.setLineDash([]);
        const tickCount = idx === 0 ? 8 : idx === 1 ? 16 : 24;
        const dir = idx % 2 === 0 ? 1 : -1;
        for (let t = 0; t < tickCount; t++) {
          const theta = (t / tickCount) * Math.PI * 2 + ringRot * dir * (0.4 + idx * 0.2);
          const tx1 = cx + Math.cos(theta) * (r - 4);
          const ty1 = cy + Math.sin(theta) * (r - 4);
          const tx2 = cx + Math.cos(theta) * (r + 4);
          const ty2 = cy + Math.sin(theta) * (r + 4);

          ctx.strokeStyle = idx === 0 ? 'rgba(56, 189, 248, 0.4)' : 'rgba(167, 139, 250, 0.3)';
          ctx.beginPath();
          ctx.moveTo(tx1, ty1);
          ctx.lineTo(tx2, ty2);
          ctx.stroke();
        }
      });
      ctx.restore();

      // Compute 2D Screen Positions for All Topological Nodes
      const coords = new Map<EstateSubsystemId, { x: number; y: number; r: number }>();
      const nodeEntries = Object.entries(TOPOLOGICAL_NODES) as [EstateSubsystemId, (typeof TOPOLOGICAL_NODES)[EstateSubsystemId]][];

      // Sovereign Nucleus at center
      coords.set('SOVEREIGN_NUCLEUS', { x: cx, y: cy, r: 24 * baseScale });

      // Layout surrounding nodes radially based on 3D coordinates projected into 2D plane
      nodeEntries.forEach(([id, meta]) => {
        if (id === 'SOVEREIGN_NUCLEUS') return;

        const [nx, ny, nz] = meta.position;
        // Project 3D vector (x, y, z) into 2D screen coordinates with separation scale
        const angle = Math.atan2(nz, nx) + (stateRef.current.zenDriftEnabled ? stateRef.current.angleOffset * 0.2 : 0);
        const dist3d = Math.sqrt(nx * nx + nz * nz);
        const screenDist = dist3d * 38 * baseScale * sep;

        const yOffset = -ny * 22 * baseScale * sep;
        const sx = cx + Math.cos(angle) * screenDist;
        const sy = cy + Math.sin(angle) * screenDist + yOffset;

        coords.set(id, { x: sx, y: sy, r: 18 * baseScale });
      });

      stateRef.current.nodeScreenCoords = coords;

      // Render Synaptic Splines from Nucleus to all nodes
      const nucleusCoord = coords.get('SOVEREIGN_NUCLEUS')!;
      nodeEntries.forEach(([id, meta]) => {
        if (id === 'SOVEREIGN_NUCLEUS') return;
        const targetCoord = coords.get(id);
        if (!targetCoord) return;

        const isHovered = stateRef.current.hoveredSubsystem === id;
        const isSelected = stateRef.current.selectedSubsystem === id;

        // Draw elegant curved Bézier spline
        const midX = (nucleusCoord.x + targetCoord.x) / 2 + (targetCoord.y - nucleusCoord.y) * 0.12;
        const midY = (nucleusCoord.y + targetCoord.y) / 2 - (targetCoord.x - nucleusCoord.x) * 0.12;

        ctx.save();
        ctx.beginPath();
        ctx.moveTo(nucleusCoord.x, nucleusCoord.y);
        ctx.quadraticCurveTo(midX, midY, targetCoord.x, targetCoord.y);

        if (isSelected) {
          ctx.strokeStyle = meta.accentColor;
          ctx.lineWidth = 2.4;
          ctx.shadowColor = meta.accentColor;
          ctx.shadowBlur = 10;
        } else if (isHovered) {
          ctx.strokeStyle = meta.color;
          ctx.lineWidth = 1.8;
          ctx.shadowColor = meta.color;
          ctx.shadowBlur = 6;
        } else {
          ctx.strokeStyle = 'rgba(56, 189, 248, 0.2)';
          ctx.lineWidth = 1.0;
        }
        ctx.stroke();
        ctx.restore();
      });

      // Render In-Flight Photon Packets along Splines
      ctx.save();
      stateRef.current.photons.forEach((photon) => {
        photon.progress = (photon.progress + photon.speed) % 1.0;
        const targetCoord = coords.get(photon.targetId);
        if (!targetCoord) return;

        const t = photon.progress;
        const midX = (nucleusCoord.x + targetCoord.x) / 2 + (targetCoord.y - nucleusCoord.y) * 0.12;
        const midY = (nucleusCoord.y + targetCoord.y) / 2 - (targetCoord.x - nucleusCoord.x) * 0.12;

        // Quadratic Bézier formula: B(t) = (1-t)^2 P0 + 2(1-t)t P1 + t^2 P2
        const bx = (1 - t) * (1 - t) * nucleusCoord.x + 2 * (1 - t) * t * midX + t * t * targetCoord.x;
        const by = (1 - t) * (1 - t) * nucleusCoord.y + 2 * (1 - t) * t * midY + t * t * targetCoord.y;

        ctx.fillStyle = photon.color;
        ctx.shadowColor = photon.color;
        ctx.shadowBlur = 8;
        ctx.beginPath();
        ctx.arc(bx, by, 2.5 * baseScale, 0, Math.PI * 2);
        ctx.fill();
      });
      ctx.restore();

      // Render Topological Nodes
      nodeEntries.forEach(([id, meta]) => {
        const coord = coords.get(id);
        if (!coord) return;

        const isHovered = stateRef.current.hoveredSubsystem === id;
        const isSelected = stateRef.current.selectedSubsystem === id;
        const isNucleus = id === 'SOVEREIGN_NUCLEUS';

        const nodeRadius = coord.r * (isHovered ? 1.25 : isSelected ? 1.15 : 1.0);

        ctx.save();
        ctx.translate(coord.x, coord.y);

        // Ambient pulsating outer glow ring
        const pulse = 1.0 + Math.sin(now * 0.003 + coord.x) * 0.12;
        ctx.strokeStyle = meta.color;
        ctx.lineWidth = isSelected ? 2 : 1;
        ctx.globalAlpha = isSelected ? 0.8 : isHovered ? 0.7 : 0.35;
        ctx.beginPath();
        ctx.arc(0, 0, nodeRadius * 1.5 * pulse, 0, Math.PI * 2);
        ctx.stroke();

        // Node Geometric Core
        ctx.globalAlpha = 1.0;
        ctx.fillStyle = isSelected ? meta.accentColor : meta.color;
        ctx.shadowColor = meta.accentColor;
        ctx.shadowBlur = isSelected ? 18 : isHovered ? 14 : 8;

        if (isNucleus) {
          // Central Hexagon
          drawHexagon(ctx, 0, 0, nodeRadius);
          ctx.fill();

          // Inner white beacon core
          ctx.fillStyle = '#ffffff';
          ctx.beginPath();
          ctx.arc(0, 0, nodeRadius * 0.45, 0, Math.PI * 2);
          ctx.fill();
        } else if (meta.category === 'QUORUM_NODE') {
          // Octagonal or Diamond Quorum Nodes
          drawOctagon(ctx, 0, 0, nodeRadius);
          ctx.fill();

          ctx.fillStyle = '#0f172a';
          drawOctagon(ctx, 0, 0, nodeRadius * 0.6);
          ctx.fill();
        } else {
          // Subsystem Organ Node (Diamond / Rounded Box)
          drawDiamond(ctx, 0, 0, nodeRadius);
          ctx.fill();

          ctx.fillStyle = '#020617';
          drawDiamond(ctx, 0, 0, nodeRadius * 0.55);
          ctx.fill();
        }

        // Text Label
        ctx.shadowBlur = 0;
        ctx.font = `${Math.max(10, Math.round(11 * baseScale))}px monospace`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'top';

        // Background pill for label
        const labelText = meta.id.replace(/_/g, ' ');
        const labelWidth = ctx.measureText(labelText).width;
        ctx.fillStyle = 'rgba(2, 6, 23, 0.85)';
        ctx.fillRect(-labelWidth / 2 - 4, nodeRadius + 5, labelWidth + 8, 16);

        ctx.strokeStyle = isSelected ? meta.accentColor : 'rgba(56, 189, 248, 0.3)';
        ctx.lineWidth = 0.8;
        ctx.strokeRect(-labelWidth / 2 - 4, nodeRadius + 5, labelWidth + 8, 16);

        ctx.fillStyle = isSelected ? '#ffffff' : isHovered ? meta.accentColor : '#94a3b8';
        ctx.fillText(labelText, 0, nodeRadius + 8);

        // Status badge
        if (meta.category === 'QUORUM_NODE') {
          ctx.font = '8px monospace';
          ctx.fillStyle = '#34d399';
          ctx.fillText('RAFT ACTIVE', 0, nodeRadius + 23);
        }

        ctx.restore();
      });

      animFrameId = requestAnimationFrame(render);
    };

    animFrameId = requestAnimationFrame(render);

    // Pointer Interactivity (Hover & Hit Detection)
    const handleMouseMove = (e: MouseEvent) => {
      const rect = canvas.getBoundingClientRect();
      const mx = e.clientX - rect.left;
      const my = e.clientY - rect.top;

      let found: EstateSubsystemId | null = null;
      stateRef.current.nodeScreenCoords.forEach((coord, id) => {
        const dx = mx - coord.x;
        const dy = my - coord.y;
        const hitRadius = coord.r * 1.8 + 10;
        if (dx * dx + dy * dy <= hitRadius * hitRadius) {
          found = id;
        }
      });

      if (found !== stateRef.current.hoveredSubsystem) {
        setHoveredSubsystem(found);
        canvas.style.cursor = found ? 'pointer' : 'default';
        if (found && onPlayChime) {
          onPlayChime(520);
        }
      }
    };

    const handleClick = (e: MouseEvent) => {
      const rect = canvas.getBoundingClientRect();
      const mx = e.clientX - rect.left;
      const my = e.clientY - rect.top;

      stateRef.current.nodeScreenCoords.forEach((coord, id) => {
        const dx = mx - coord.x;
        const dy = my - coord.y;
        const hitRadius = coord.r * 1.8 + 12;
        if (dx * dx + dy * dy <= hitRadius * hitRadius) {
          onSelectSubsystem(id);
          if (onPlayChime) {
            onPlayChime(640);
          }
        }
      });
    };

    canvas.addEventListener('mousemove', handleMouseMove);
    canvas.addEventListener('click', handleClick);

    return () => {
      cancelAnimationFrame(animFrameId);
      window.removeEventListener('resize', resize);
      canvas.removeEventListener('mousemove', handleMouseMove);
      canvas.removeEventListener('click', handleClick);
    };
  }, [onSelectSubsystem, setHoveredSubsystem, onPlayChime]);

  return (
    <div ref={containerRef} className="absolute inset-0 z-0 w-full h-full overflow-hidden">
      <canvas ref={canvasRef} className="block w-full h-full" />
    </div>
  );
};

// ==============================================================================
// 2D Shape Helper Functions
// ==============================================================================

function drawHexagon(ctx: CanvasRenderingContext2D, x: number, y: number, radius: number) {
  ctx.beginPath();
  for (let i = 0; i < 6; i++) {
    const angle = (i * Math.PI) / 3;
    const hx = x + Math.cos(angle) * radius;
    const hy = y + Math.sin(angle) * radius;
    if (i === 0) ctx.moveTo(hx, hy);
    else ctx.lineTo(hx, hy);
  }
  ctx.closePath();
}

function drawOctagon(ctx: CanvasRenderingContext2D, x: number, y: number, radius: number) {
  ctx.beginPath();
  for (let i = 0; i < 8; i++) {
    const angle = (i * Math.PI) / 4 + Math.PI / 8;
    const ox = x + Math.cos(angle) * radius;
    const oy = y + Math.sin(angle) * radius;
    if (i === 0) ctx.moveTo(ox, oy);
    else ctx.lineTo(ox, oy);
  }
  ctx.closePath();
}

function drawDiamond(ctx: CanvasRenderingContext2D, x: number, y: number, radius: number) {
  ctx.beginPath();
  ctx.moveTo(x, y - radius * 1.15);
  ctx.lineTo(x + radius, y);
  ctx.lineTo(x, y + radius * 1.15);
  ctx.lineTo(x - radius, y);
  ctx.closePath();
}
