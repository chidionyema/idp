/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React from 'react';
import {
  GitBranch,
  Workflow,
  Cpu,
  Layers,
  Clock,
  Bot,
  Network,
  Terminal,
  ShieldCheck,
  ArrowRight,
} from 'lucide-react';
import { SurfaceDefinition, SurfaceType } from '../types/optimus';

interface SurfaceGridProps {
  surfaces: SurfaceDefinition[];
  selectedSurface: SurfaceType | null;
  onSelectSurface: (surface: SurfaceType) => void;
  onTestGate: (surface: SurfaceType) => void;
}

export const SurfaceGrid: React.FC<SurfaceGridProps> = ({
  surfaces,
  selectedSurface,
  onSelectSurface,
  onTestGate,
}) => {
  const getIcon = (iconName: string) => {
    switch (iconName) {
      case 'GitBranch':
        return <GitBranch className="w-4 h-4 text-emerald-400" />;
      case 'Workflow':
        return <Workflow className="w-4 h-4 text-blue-400" />;
      case 'Cpu':
        return <Cpu className="w-4 h-4 text-indigo-400" />;
      case 'Layers':
        return <Layers className="w-4 h-4 text-amber-400" />;
      case 'Clock':
        return <Clock className="w-4 h-4 text-cyan-400" />;
      case 'Bot':
        return <Bot className="w-4 h-4 text-purple-400" />;
      case 'Network':
        return <Network className="w-4 h-4 text-rose-400" />;
      case 'Terminal':
        return <Terminal className="w-4 h-4 text-slate-300" />;
      default:
        return <ShieldCheck className="w-4 h-4 text-emerald-400" />;
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <div>
          <h2 className="text-base font-bold text-white tracking-tight">
            Estate Surface Topology (8 of 8 Runnable Layers)
          </h2>
          <p className="text-xs text-slate-400">
            Every layer has dedicated pre-execution invariant meters and mathematical anti-circumvention locks.
          </p>
        </div>
        <div className="text-xs font-mono text-slate-400 flex items-center gap-2">
          <span>Total Nodes: <strong className="text-white font-mono">387</strong></span>
          <span aria-hidden="true">·</span>
          <span>Coverage: <strong className="text-emerald-400 font-mono">100.0%</strong></span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {surfaces.map((surface) => {
          const isSelected = selectedSurface === surface.id;
          return (
            <div
              key={surface.id}
              onClick={() => onSelectSurface(surface.id)}
              className={`p-4 rounded-xl border transition-all cursor-pointer bg-slate-900/70 hover:bg-slate-900/90 flex flex-col justify-between ${
                isSelected
                  ? 'border-indigo-500 ring-1 ring-indigo-500 shadow-md shadow-indigo-950/50'
                  : 'border-slate-800 hover:border-slate-700'
              }`}
            >
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2.5">
                    <div className="p-2 rounded-lg bg-slate-800/80 border border-slate-700">
                      {getIcon(surface.iconName)}
                    </div>
                    <div>
                      <h3 className="text-xs font-bold text-white leading-tight">
                        {surface.name}
                      </h3>
                      <div className="text-[11px] text-slate-400">
                        {surface.category}
                      </div>
                    </div>
                  </div>
                </div>

                <div className="space-y-1.5 pt-1">
                  <div className="text-[11px] text-slate-300">
                    <span className="text-slate-500 block text-[10px] uppercase font-mono">Instrumentation</span>
                    {surface.instrumentationTechnique}
                  </div>
                  <div className="text-[11px] text-slate-300">
                    <span className="text-slate-500 block text-[10px] uppercase font-mono">Anti-Circumvention</span>
                    {surface.antiCircumventionMechanism}
                  </div>
                </div>
              </div>

              <div className="pt-3.5 mt-3.5 border-t border-slate-800/80 flex items-center justify-between text-xs">
                <div className="flex items-center gap-2 font-mono text-[11px] text-slate-400">
                  <span>{surface.activeNodes} nodes</span>
                  <span aria-hidden="true">·</span>
                  <span className="text-emerald-400">{surface.hardInvariantsCount} invariants</span>
                </div>
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    onTestGate(surface.id);
                  }}
                  className="text-xs font-semibold text-indigo-400 hover:text-indigo-300 flex items-center gap-1 group whitespace-nowrap"
                >
                  <span>Test Gate</span>
                  <ArrowRight className="w-3 h-3 group-hover:translate-x-0.5 transition-transform" />
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
