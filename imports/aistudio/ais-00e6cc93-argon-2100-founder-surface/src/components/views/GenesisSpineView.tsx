import React, { useState, useEffect, useRef } from 'react';
import { Activity, Zap, Server, Shield, RefreshCw, ZoomIn, ZoomOut, CheckCircle2 } from 'lucide-react';
import { SpineNode, INITIAL_SPINE_NODES } from '../../data/estateData';

export const GenesisSpineView: React.FC = () => {
  const [nodes, setNodes] = useState<SpineNode[]>(INITIAL_SPINE_NODES);
  const [selectedNode, setSelectedNode] = useState<SpineNode>(INITIAL_SPINE_NODES[0]);
  const [zoomLevel, setZoomLevel] = useState(1);
  const [isSyncing, setIsSyncing] = useState(false);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  // Animated synaptic pulse canvas
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animId: number;
    let t = 0;

    const render = () => {
      t += 0.02;
      const width = canvas.width;
      const height = canvas.height;

      ctx.clearRect(0, 0, width, height);

      // Draw connections
      nodes.forEach((sourceNode) => {
        sourceNode.connections.forEach((targetId) => {
          const targetNode = nodes.find((n) => n.id === targetId);
          if (!targetNode) return;

          const sx = (sourceNode.x / 100) * width;
          const sy = (sourceNode.y / 100) * height;
          const tx = (targetNode.x / 100) * width;
          const ty = (targetNode.y / 100) * height;

          // Synaptic link line
          ctx.beginPath();
          ctx.moveTo(sx, sy);
          ctx.lineTo(tx, ty);
          ctx.strokeStyle = 'rgba(56, 189, 248, 0.2)';
          ctx.lineWidth = 1.5;
          ctx.stroke();

          // Flowing energy particle along link
          const progress = (t * 0.5 + (sourceNode.id.charCodeAt(5) || 0) * 0.2) % 1;
          const px = sx + (tx - sx) * progress;
          const py = sy + (ty - sy) * progress;

          ctx.beginPath();
          ctx.arc(px, py, 2.5, 0, Math.PI * 2);
          ctx.fillStyle = sourceNode.status === 'syncing' ? '#fbbf24' : '#38bdf8';
          ctx.shadowColor = '#38bdf8';
          ctx.shadowBlur = 6;
          ctx.fill();
          ctx.shadowBlur = 0;
        });
      });

      // Draw nodes
      nodes.forEach((n) => {
        const nx = (n.x / 100) * width;
        const ny = (n.y / 100) * height;
        const isSelected = selectedNode?.id === n.id;

        // Outer glow ring
        ctx.beginPath();
        ctx.arc(nx, ny, isSelected ? 18 : 12, 0, Math.PI * 2);
        ctx.fillStyle = isSelected
          ? 'rgba(56, 189, 248, 0.3)'
          : n.status === 'syncing'
          ? 'rgba(251, 191, 36, 0.2)'
          : 'rgba(56, 189, 248, 0.15)';
        ctx.fill();

        // Node center
        ctx.beginPath();
        ctx.arc(nx, ny, isSelected ? 9 : 7, 0, Math.PI * 2);
        ctx.fillStyle = n.status === 'syncing' ? '#f59e0b' : '#38bdf8';
        ctx.fill();

        // Label
        ctx.font = '11px Plus Jakarta Sans, sans-serif';
        ctx.fillStyle = isSelected ? '#ffffff' : '#94a3b8';
        ctx.textAlign = 'center';
        ctx.fillText(n.name, nx, ny + 24);
      });

      animId = requestAnimationFrame(render);
    };

    render();
    return () => cancelAnimationFrame(animId);
  }, [nodes, selectedNode]);

  const handleSyncSpine = () => {
    setIsSyncing(true);
    setTimeout(() => {
      setNodes((prev) =>
        prev.map((n) => ({
          ...n,
          status: 'nominal',
          latencyMs: Math.max(3, Math.round(n.latencyMs * 0.85)),
        }))
      );
      setIsSyncing(false);
    }, 1000);
  };

  return (
    <div className="space-y-6">
      {/* Top Banner / Breadcrumb */}
      <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <div className="flex items-center gap-2 text-xs font-mono text-slate-400">
            <span>Estate Architecture</span>
            <span>/</span>
            <span className="text-sky-400">Genesis Spine &amp; Neural Topology</span>
          </div>
          <h2 className="text-xl font-bold text-white tracking-tight mt-1">
            Genesis Neural Spine Core
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Dynamic low-latency cognitive backbone routing synchronous founder directives across the estate.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setZoomLevel((z) => Math.max(0.8, z - 0.1))}
            className="p-2 rounded-lg bg-slate-900 border border-slate-800 text-slate-400 hover:text-white"
            title="Zoom Out"
          >
            <ZoomOut className="w-4 h-4" />
          </button>
          <button
            onClick={() => setZoomLevel((z) => Math.min(1.4, z + 0.1))}
            className="p-2 rounded-lg bg-slate-900 border border-slate-800 text-slate-400 hover:text-white"
            title="Zoom In"
          >
            <ZoomIn className="w-4 h-4" />
          </button>
          <button
            onClick={handleSyncSpine}
            disabled={isSyncing}
            className="flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-semibold bg-sky-600 hover:bg-sky-500 text-white disabled:opacity-50 transition-colors"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isSyncing ? 'animate-spin' : ''}`} />
            <span>{isSyncing ? 'Synchronizing Nodes...' : 'Resync Synaptic Mesh'}</span>
          </button>
        </div>
      </div>

      {/* Main Grid: Interactive Topology Graph + Node Details Drawer */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Canvas Visualizer */}
        <div className="lg:col-span-8 rounded-2xl border border-slate-800 bg-slate-950/80 p-4 relative overflow-hidden spatial-grid">
          <div className="absolute top-4 left-4 z-10 flex items-center gap-3 text-xs font-mono">
            <span className="flex items-center gap-1.5 text-emerald-400">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              12 Nodes Active
            </span>
            <span className="text-slate-500">·</span>
            <span className="text-slate-400">Packet Loss: 0.00%</span>
            <span className="text-slate-500">·</span>
            <span className="text-slate-400">Backbone: 400 Gbps Active Synapse</span>
          </div>

          <div
            className="w-full flex items-center justify-center min-h-[460px] transition-transform duration-200"
            style={{ transform: `scale(${zoomLevel})` }}
          >
            <canvas
              ref={canvasRef}
              width={820}
              height={460}
              className="w-full h-auto cursor-crosshair"
              onClick={(e) => {
                const rect = e.currentTarget.getBoundingClientRect();
                const clickX = ((e.clientX - rect.left) / rect.width) * 100;
                const clickY = ((e.clientY - rect.top) / rect.height) * 100;

                // Find closest node
                let closest = nodes[0];
                let minDist = 9999;
                nodes.forEach((n) => {
                  const dist = Math.hypot(n.x - clickX, n.y - clickY);
                  if (dist < minDist) {
                    minDist = dist;
                    closest = n;
                  }
                });

                if (minDist < 12) {
                  setSelectedNode(closest);
                }
              }}
            />
          </div>

          <div className="text-xs text-slate-500 text-center mt-2">
            Click on any topology node to inspect synaptic latency, load pressure, and packet routing.
          </div>
        </div>

        {/* Selected Node Inspector Drawer */}
        <div className="lg:col-span-4 rounded-2xl border border-slate-800 bg-slate-900/60 p-5 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div className="flex items-center gap-2">
                <Server className="w-4 h-4 text-sky-400" />
                <span className="text-xs font-mono uppercase tracking-wider text-slate-400">Node Telemetry</span>
              </div>
              <span className={`text-xs font-mono px-2 py-0.5 rounded border ${
                selectedNode.status === 'nominal'
                  ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
                  : 'bg-amber-500/10 border-amber-500/30 text-amber-400'
              }`}>
                {selectedNode.status.toUpperCase()}
              </span>
            </div>

            <div className="mt-4">
              <h3 className="text-base font-bold text-white">{selectedNode.name}</h3>
              <p className="text-xs text-slate-400 mt-1 font-mono">
                Node Identifier: {selectedNode.id} · Type: {selectedNode.type}
              </p>
            </div>

            <div className="space-y-4 mt-6">
              <div>
                <div className="flex justify-between text-xs font-mono text-slate-400 mb-1">
                  <span>Synaptic Latency</span>
                  <span className="text-white font-bold tabular-nums">{selectedNode.latencyMs} ms</span>
                </div>
                <div className="w-full h-1.5 rounded-full bg-slate-800 overflow-hidden">
                  <div
                    className="h-full bg-sky-400 rounded-full"
                    style={{ width: `${Math.min(100, selectedNode.latencyMs * 3)}%` }}
                  />
                </div>
              </div>

              <div>
                <div className="flex justify-between text-xs font-mono text-slate-400 mb-1">
                  <span>Cognitive Load</span>
                  <span className="text-white font-bold tabular-nums">{selectedNode.loadPct}%</span>
                </div>
                <div className="w-full h-1.5 rounded-full bg-slate-800 overflow-hidden">
                  <div
                    className="h-full bg-indigo-400 rounded-full"
                    style={{ width: `${selectedNode.loadPct}%` }}
                  />
                </div>
              </div>

              <div className="pt-2 border-t border-slate-800">
                <span className="text-xs font-mono text-slate-400">Inter-Node Synapses ({selectedNode.connections.length})</span>
                <div className="flex flex-wrap gap-1.5 mt-2">
                  {selectedNode.connections.map((cId) => {
                    const cNode = nodes.find((n) => n.id === cId);
                    return (
                      <button
                        key={cId}
                        onClick={() => cNode && setSelectedNode(cNode)}
                        className="px-2 py-1 text-xs font-mono bg-slate-800 hover:bg-slate-700 text-slate-300 rounded border border-slate-700 transition-colors"
                      >
                        {cNode?.name || cId}
                      </button>
                    );
                  })}
                </div>
              </div>
            </div>
          </div>

          <div className="pt-6 border-t border-slate-800 mt-6 space-y-2">
            <button
              onClick={() => {
                setNodes((prev) =>
                  prev.map((n) =>
                    n.id === selectedNode.id
                      ? { ...n, latencyMs: Math.max(2, n.latencyMs - 2), status: 'nominal' }
                      : n
                  )
                );
                setSelectedNode((prev) => ({ ...prev, latencyMs: Math.max(2, prev.latencyMs - 2), status: 'nominal' }));
              }}
              className="w-full py-2 px-3 text-xs font-semibold rounded-lg bg-sky-600/20 hover:bg-sky-600/30 text-sky-300 border border-sky-500/30 transition-colors flex items-center justify-center gap-1.5"
            >
              <Zap className="w-3.5 h-3.5" />
              <span>Optimize Node Synapse Path</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
