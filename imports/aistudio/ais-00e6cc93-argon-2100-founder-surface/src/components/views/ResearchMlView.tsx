import React, { useState } from 'react';
import { Cpu, TrendingUp, Layers, CheckCircle2, Play, Download, BarChart2 } from 'lucide-react';

export const ResearchMlView: React.FC = () => {
  const [selectedModel, setSelectedModel] = useState('argon-omni-v8.4');
  const [isPromoting, setIsPromoting] = useState(false);
  const [promotedSuccess, setPromotedSuccess] = useState(false);

  const models = [
    {
      id: 'argon-omni-v8.4',
      name: 'Argon-Omni-v8.4 Checkpoint',
      parameters: '70B MoE Active',
      status: 'converged',
      loss: 0.0418,
      yieldMultiplier: '1.84x',
      mmluScore: '89.4%',
      humanEval: '92.6%',
      math500: '88.1%',
      trainingTokens: '4.2T tokens',
    },
    {
      id: 'reasoner-flash-1b',
      name: 'Reasoner-Flash-1b Active',
      parameters: '1.2B Dense Distilled',
      status: 'training',
      loss: 0.0892,
      yieldMultiplier: '2.14x',
      mmluScore: '78.2%',
      humanEval: '84.0%',
      math500: '81.4%',
      trainingTokens: '1.8T tokens',
    },
    {
      id: 'hermes-coder-v3',
      name: 'Hermes-Coder-v3 Fine-Tuned',
      parameters: '14B Specialized',
      status: 'converged',
      loss: 0.0521,
      yieldMultiplier: '1.65x',
      mmluScore: '85.7%',
      humanEval: '95.2%',
      math500: '84.8%',
      trainingTokens: '2.4T tokens',
    },
  ];

  const currentModelData = models.find((m) => m.id === selectedModel) || models[0];

  // SVG Loss Convergence curve coordinates
  const epochs = Array.from({ length: 50 }, (_, i) => i + 1);
  const lossPoints = epochs.map((ep) => {
    const rawLoss = 0.8 / Math.sqrt(ep * 0.8) + (Math.sin(ep * 0.5) * 0.02) / ep;
    return Math.max(0.04, rawLoss);
  });
  const valLossPoints = lossPoints.map((l, i) => l + 0.02 + (i % 3 === 0 ? 0.015 : -0.005));

  // Map to SVG coordinates (width 600, height 200)
  const svgWidth = 600;
  const svgHeight = 200;
  const maxLoss = 1.0;

  const toSvgX = (i: number) => (i / (epochs.length - 1)) * (svgWidth - 60) + 40;
  const toSvgY = (loss: number) => svgHeight - 30 - (loss / maxLoss) * (svgHeight - 50);

  const trainPath = lossPoints
    .map((lp, i) => `${i === 0 ? 'M' : 'L'} ${toSvgX(i).toFixed(1)} ${toSvgY(lp).toFixed(1)}`)
    .join(' ');

  const valPath = valLossPoints
    .map((vlp, i) => `${i === 0 ? 'M' : 'L'} ${toSvgX(i).toFixed(1)} ${toSvgY(vlp).toFixed(1)}`)
    .join(' ');

  const handlePromoteCheckpoint = () => {
    setIsPromoting(true);
    setTimeout(() => {
      setIsPromoting(false);
      setPromotedSuccess(true);
      setTimeout(() => setPromotedSuccess(false), 3000);
    }, 1200);
  };

  return (
    <div className="space-y-6">
      {/* View Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <div className="flex items-center gap-2 text-xs font-mono text-slate-400">
            <span>Estate Intelligence</span>
            <span>/</span>
            <span className="text-sky-400">Research &amp; Active ML</span>
          </div>
          <h2 className="text-xl font-bold text-white tracking-tight mt-1">
            Argon Research &amp; ML Foundation
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Continuous model evaluation, loss curve convergence, checkpoint promotion, and instruction yield multipliers.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handlePromoteCheckpoint}
            disabled={isPromoting}
            className="flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-semibold bg-sky-600 hover:bg-sky-500 text-white transition-colors"
          >
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>{isPromoting ? 'Promoting to Live Cluster...' : 'Promote Checkpoint to Estate'}</span>
          </button>
        </div>
      </div>

      {promotedSuccess && (
        <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4" />
          <span>{currentModelData.name} successfully verified and promoted as live reasoning spine.</span>
        </div>
      )}

      {/* Model Selector Tabs */}
      <div className="flex items-center gap-2 border-b border-slate-800 pb-2 overflow-x-auto">
        {models.map((m) => (
          <button
            key={m.id}
            onClick={() => setSelectedModel(m.id)}
            className={`px-3 py-2 text-xs font-medium rounded-lg whitespace-nowrap transition-colors flex items-center gap-2 ${
              selectedModel === m.id
                ? 'bg-slate-800 text-white border border-slate-700'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Cpu className="w-3.5 h-3.5 text-sky-400" />
            <span>{m.name}</span>
            <span className="text-xs font-mono text-emerald-400 font-bold">{m.yieldMultiplier}</span>
          </button>
        ))}
      </div>

      {/* Main Grid: Loss Curves + Model Benchmark Details */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Loss Convergence Chart */}
        <div className="lg:col-span-8 rounded-2xl border border-slate-800 bg-slate-950/80 p-5 spatial-grid">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800">
            <div>
              <span className="text-xs font-mono text-slate-400 uppercase tracking-wider">Telemetry Curve</span>
              <h3 className="text-sm font-semibold text-white mt-0.5">
                Training vs. Validation Loss Convergence (50 Epochs)
              </h3>
            </div>
            <div className="flex items-center gap-4 text-xs font-mono">
              <span className="flex items-center gap-1.5 text-sky-400">
                <span className="w-2.5 h-0.5 bg-sky-400" /> Training Loss ({currentModelData.loss})
              </span>
              <span className="flex items-center gap-1.5 text-indigo-400">
                <span className="w-2.5 h-0.5 bg-indigo-400" /> Validation Loss
              </span>
            </div>
          </div>

          <div className="w-full overflow-x-auto py-4">
            <svg viewBox={`0 0 ${svgWidth} ${svgHeight}`} className="w-full h-56">
              {/* Grid lines */}
              {[0.2, 0.4, 0.6, 0.8].map((lvl) => (
                <g key={lvl}>
                  <line
                    x1="40"
                    y1={toSvgY(lvl)}
                    x2={svgWidth - 20}
                    y2={toSvgY(lvl)}
                    stroke="rgba(148, 163, 184, 0.1)"
                    strokeDasharray="4 4"
                  />
                  <text
                    x="25"
                    y={toSvgY(lvl) + 4}
                    fill="#64748b"
                    fontSize="10"
                    fontFamily="monospace"
                    textAnchor="end"
                  >
                    {lvl.toFixed(1)}
                  </text>
                </g>
              ))}

              {/* Epoch tick marks */}
              {[10, 20, 30, 40, 50].map((ep) => (
                <text
                  key={ep}
                  x={toSvgX(ep - 1)}
                  y={svgHeight - 10}
                  fill="#64748b"
                  fontSize="10"
                  fontFamily="monospace"
                  textAnchor="middle"
                >
                  ep {ep}
                </text>
              ))}

              {/* Loss Paths */}
              <path d={valPath} fill="none" stroke="#818cf8" strokeWidth="2" strokeDasharray="3 3" />
              <path d={trainPath} fill="none" stroke="#38bdf8" strokeWidth="2.5" />

              {/* Min loss dot */}
              <circle
                cx={toSvgX(epochs.length - 1)}
                cy={toSvgY(lossPoints[lossPoints.length - 1])}
                r="4"
                fill="#38bdf8"
              />
            </svg>
          </div>

          <div className="pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs text-slate-400 font-mono">
            <span>Checkpoint Test Loss: <strong className="text-white">{currentModelData.loss}</strong></span>
            <span>Total Pre-training Tokens: <strong className="text-white">{currentModelData.trainingTokens}</strong></span>
            <span>Reasoning Multiplier: <strong className="text-emerald-400">{currentModelData.yieldMultiplier}</strong></span>
          </div>
        </div>

        {/* Benchmark Evaluation KPI Card */}
        <div className="lg:col-span-4 rounded-2xl border border-slate-800 bg-slate-900/60 p-5 space-y-4">
          <div className="pb-3 border-b border-slate-800">
            <span className="text-xs font-mono uppercase tracking-wider text-slate-400">Evaluation Yields</span>
            <h3 className="text-sm font-bold text-white mt-0.5">{currentModelData.name}</h3>
            <span className="text-xs font-mono text-sky-400">{currentModelData.parameters}</span>
          </div>

          <div className="space-y-3">
            <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800 flex items-center justify-between">
              <div>
                <span className="text-xs text-slate-400">HumanEval (Code)</span>
                <div className="text-sm font-bold font-mono text-white mt-0.5">{currentModelData.humanEval}</div>
              </div>
              <span className="text-xs font-mono text-emerald-400">+4.2% vs baseline</span>
            </div>

            <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800 flex items-center justify-between">
              <div>
                <span className="text-xs text-slate-400">MMLU-Pro (Reasoning)</span>
                <div className="text-sm font-bold font-mono text-white mt-0.5">{currentModelData.mmluScore}</div>
              </div>
              <span className="text-xs font-mono text-emerald-400">+6.1% vs baseline</span>
            </div>

            <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800 flex items-center justify-between">
              <div>
                <span className="text-xs text-slate-400">Math-500 (Proof)</span>
                <div className="text-sm font-bold font-mono text-white mt-0.5">{currentModelData.math500}</div>
              </div>
              <span className="text-xs font-mono text-emerald-400">+3.8% vs baseline</span>
            </div>
          </div>

          <div className="pt-4 border-t border-slate-800">
            <span className="text-xs font-mono text-slate-400 block mb-2">Weight Distribution Checksum</span>
            <div className="p-2.5 rounded bg-slate-950 border border-slate-800 font-mono text-xs text-slate-300 break-all">
              sha256: 9e4f2a7b8810c93a02bb8ef1920ac341772901a
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
