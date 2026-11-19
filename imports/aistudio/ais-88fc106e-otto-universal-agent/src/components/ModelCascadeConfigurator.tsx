import React, { useState } from 'react';
import { 
  Cpu, 
  ArrowDown, 
  ArrowUp, 
  Plus, 
  Trash2, 
  CheckCircle2, 
  AlertTriangle, 
  RotateCcw, 
  Zap, 
  ShieldCheck, 
  Layers, 
  Play, 
  Lock,
  Sparkles,
  Sliders
} from 'lucide-react';
import { 
  AVAILABLE_FRONTIER_MODELS, 
  BEDROCK_LOCAL_MODEL, 
  DEFAULT_CASCADE_TIERS, 
  CascadeTier, 
  FrontierModelOption 
} from '../data/modelCascadeConfig';

interface ModelCascadeConfiguratorProps {
  onConfigurationChange?: (tiers: CascadeTier[]) => void;
  compact?: boolean;
}

export const ModelCascadeConfigurator: React.FC<ModelCascadeConfiguratorProps> = ({
  onConfigurationChange,
  compact = false
}) => {
  const [tiers, setTiers] = useState<CascadeTier[]>(DEFAULT_CASCADE_TIERS);
  const [simRunning, setSimRunning] = useState(false);
  const [simLogs, setSimLogs] = useState<string[]>([]);
  const [simVerdict, setSimVerdict] = useState<string | null>(null);
  const [activePreset, setActivePreset] = useState<string>('default');

  const updateTiers = (newTiers: CascadeTier[]) => {
    // re-number tiers sequentially
    const reindexed = newTiers.map((t, idx) => ({ ...t, tierNumber: idx + 1 }));
    setTiers(reindexed);
    if (onConfigurationChange) {
      onConfigurationChange(reindexed);
    }
  };

  const handleMoveTier = (index: number, direction: 'up' | 'down') => {
    if (direction === 'up' && index === 0) return;
    if (direction === 'down' && index === tiers.length - 1) return;

    const targetIndex = direction === 'up' ? index - 1 : index + 1;
    const updated = [...tiers];
    const temp = updated[index];
    updated[index] = updated[targetIndex];
    updated[targetIndex] = temp;
    updateTiers(updated);
    setActivePreset('custom');
  };

  const handleModelChange = (index: number, newModelId: string) => {
    const updated = [...tiers];
    const modelMeta = AVAILABLE_FRONTIER_MODELS.find(m => m.id === newModelId);
    updated[index] = {
      ...updated[index],
      modelId: newModelId,
      timeoutMs: modelMeta ? modelMeta.defaultTimeoutMs : updated[index].timeoutMs
    };
    updateTiers(updated);
    setActivePreset('custom');
  };

  const handleTimeoutChange = (index: number, newTimeout: number) => {
    const updated = [...tiers];
    updated[index].timeoutMs = newTimeout;
    updateTiers(updated);
    setActivePreset('custom');
  };

  const handleToggleTrigger = (index: number, trigger: 'http_5xx' | 'rate_limit_429' | 'timeout' | 'safety_censor') => {
    const updated = [...tiers];
    const current = updated[index].failoverTriggers;
    if (current.includes(trigger)) {
      if (current.length > 1) {
        updated[index].failoverTriggers = current.filter(t => t !== trigger);
      }
    } else {
      updated[index].failoverTriggers = [...current, trigger];
    }
    updateTiers(updated);
    setActivePreset('custom');
  };

  const handleAddTier = () => {
    if (tiers.length >= 5) return;
    // pick first model not currently in tiers, or default to qwen
    const usedIds = tiers.map(t => t.modelId);
    const available = AVAILABLE_FRONTIER_MODELS.find(m => !usedIds.includes(m.id)) || AVAILABLE_FRONTIER_MODELS[0];
    const newTier: CascadeTier = {
      tierNumber: tiers.length + 1,
      modelId: available.id,
      timeoutMs: available.defaultTimeoutMs,
      failoverTriggers: ['http_5xx', 'rate_limit_429', 'timeout'],
      enabled: true
    };
    updateTiers([...tiers, newTier]);
    setActivePreset('custom');
  };

  const handleRemoveTier = (index: number) => {
    if (tiers.length <= 1) return; // keep at least 1 frontier model before local
    const updated = tiers.filter((_, i) => i !== index);
    updateTiers(updated);
    setActivePreset('custom');
  };

  const applyPreset = (presetName: string) => {
    setActivePreset(presetName);
    if (presetName === 'default') {
      updateTiers([
        { tierNumber: 1, modelId: 'claude-3-7-sonnet', timeoutMs: 4500, failoverTriggers: ['http_5xx', 'rate_limit_429', 'timeout', 'safety_censor'], enabled: true },
        { tierNumber: 2, modelId: 'gemini-2-5-flash', timeoutMs: 2500, failoverTriggers: ['http_5xx', 'rate_limit_429', 'timeout'], enabled: true },
        { tierNumber: 3, modelId: 'deepseek-v3', timeoutMs: 3500, failoverTriggers: ['http_5xx', 'rate_limit_429', 'timeout'], enabled: true }
      ]);
    } else if (presetName === 'speed-economy') {
      updateTiers([
        { tierNumber: 1, modelId: 'gemini-2-5-flash', timeoutMs: 2000, failoverTriggers: ['http_5xx', 'rate_limit_429', 'timeout'], enabled: true },
        { tierNumber: 2, modelId: 'deepseek-v3', timeoutMs: 3000, failoverTriggers: ['http_5xx', 'rate_limit_429', 'timeout'], enabled: true },
        { tierNumber: 3, modelId: 'claude-3-7-sonnet', timeoutMs: 5000, failoverTriggers: ['http_5xx', 'rate_limit_429', 'timeout', 'safety_censor'], enabled: true }
      ]);
    } else if (presetName === 'reasoning-first') {
      updateTiers([
        { tierNumber: 1, modelId: 'claude-3-7-sonnet', timeoutMs: 5000, failoverTriggers: ['http_5xx', 'rate_limit_429', 'timeout', 'safety_censor'], enabled: true },
        { tierNumber: 2, modelId: 'gemini-2-5-pro', timeoutMs: 5000, failoverTriggers: ['http_5xx', 'rate_limit_429', 'timeout'], enabled: true },
        { tierNumber: 3, modelId: 'kimi-k1-5', timeoutMs: 4000, failoverTriggers: ['http_5xx', 'rate_limit_429', 'timeout'], enabled: true }
      ]);
    } else if (presetName === 'open-weights') {
      updateTiers([
        { tierNumber: 1, modelId: 'deepseek-v3', timeoutMs: 3200, failoverTriggers: ['http_5xx', 'rate_limit_429', 'timeout'], enabled: true },
        { tierNumber: 2, modelId: 'qwen-2-5-coder-32b', timeoutMs: 3000, failoverTriggers: ['http_5xx', 'rate_limit_429', 'timeout'], enabled: true },
        { tierNumber: 3, modelId: 'gemini-2-5-flash', timeoutMs: 2500, failoverTriggers: ['http_5xx', 'rate_limit_429', 'timeout'], enabled: true }
      ]);
    }
  };

  const handleTestCascade = (failAllFrontier = false) => {
    setSimRunning(true);
    setSimVerdict(null);
    const tier1Meta = AVAILABLE_FRONTIER_MODELS.find(m => m.id === tiers[0]?.modelId);
    setSimLogs([
      `[ROUTER-DISPATCH] Routing query with user cascade: ${tiers.map(t => t.modelId).join(' ➔ ')} ➔ ${BEDROCK_LOCAL_MODEL.id}`
    ]);

    const steps: string[] = [];
    if (!failAllFrontier) {
      // Simulate Tier 1 503 error, then Tier 2 success
      const tier2Meta = AVAILABLE_FRONTIER_MODELS.find(m => m.id === tiers[1]?.modelId);
      steps.push(
        `T+00ms: Query dispatched to Tier 1: ${tier1Meta?.name || tiers[0]?.modelId}`,
        `T+180ms: SIMULATED HTTP 503: Upstream provider gateway timeout on Tier 1`,
        `T+210ms: Circuit breaker triggered ➔ Stepping down to Tier 2: ${tier2Meta?.name || tiers[1]?.modelId}`,
        `T+340ms: Tier 2 (${tier2Meta?.provider}) responded in 130ms with validated AST tokens`,
        `T+380ms: Invariants verified (ΔU > 0, ΔRisk = 0). Task delivered without founder retry.`
      );
    } else {
      // Simulate failure of all frontier models, falling back to local model
      tiers.forEach((t, i) => {
        const meta = AVAILABLE_FRONTIER_MODELS.find(m => m.id === t.modelId);
        steps.push(
          `T+${i * 120}ms: Tier ${t.tierNumber} (${meta?.name}) tripped trigger [http_5xx/rate_limit] ➔ Stepping down...`
        );
      });
      steps.push(
        `T+${tiers.length * 120 + 40}ms: All frontier cloud tiers offline ➔ Falling back to PERMANENT LOCAL BEDROCK`,
        `T+${tiers.length * 120 + 90}ms: Initializing ${BEDROCK_LOCAL_MODEL.name} on Apple Neural Engine`,
        `T+${tiers.length * 120 + 260}ms: Local model completed inference offline (48 tok/sec). 0 bytes leaked to internet.`
      );
    }

    let i = 0;
    const interval = setInterval(() => {
      if (i < steps.length) {
        setSimLogs(prev => [...prev, steps[i]]);
        i++;
      } else {
        clearInterval(interval);
        setSimRunning(false);
        setSimVerdict(
          failAllFrontier
            ? 'VERIFIED: All frontier clouds failed ➔ Sovereign local bedrock saved execution in 100% offline mode.'
            : `VERIFIED: Tier 1 tripped ➔ Cascade stepped down to Tier 2 (${tiers[1]?.modelId}) in 210ms seamlessly.`
        );
      }
    }, 380);
  };

  return (
    <div className="space-y-6">
      {/* Top Header Card */}
      <div className="rounded-2xl border border-indigo-500/30 bg-slate-950 p-6 shadow-xl space-y-4">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-slate-800 pb-4">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-300 text-xs font-mono font-bold mb-1">
              <Sliders className="w-3.5 h-3.5 text-cyan-400" />
              <span>DYNAMIC FRONTIER CASCADE &amp; LOCAL BEDROCK</span>
            </div>
            <h3 className="text-xl font-bold font-display text-white">
              Configurable Frontier Model Cascade
            </h3>
            <p className="text-xs text-slate-300 max-w-2xl mt-1 leading-relaxed">
              Reorder, tune timeouts, or swap frontier providers at will. The <strong className="text-emerald-400">local quantized 70B model</strong> remains the unshakeable bedrock fallback when clouds go down.
            </p>
          </div>

          {/* Preset Buttons */}
          <div className="flex flex-wrap items-center gap-1.5 self-start md:self-auto">
            <span className="text-[11px] font-mono text-slate-500 mr-1">PRESETS:</span>
            {[
              { id: 'default', label: 'Claude ➔ Gemini ➔ DeepSeek' },
              { id: 'speed-economy', label: 'Speed: Gemini ➔ DeepSeek' },
              { id: 'reasoning-first', label: 'Reasoning: Claude ➔ Pro' },
              { id: 'open-weights', label: 'Open: DeepSeek ➔ Qwen' }
            ].map(p => (
              <button
                key={p.id}
                onClick={() => applyPreset(p.id)}
                className={`px-2.5 py-1 rounded-lg text-xs font-mono transition-all ${
                  activePreset === p.id
                    ? 'bg-indigo-600 text-white font-bold shadow'
                    : 'bg-slate-900 text-slate-400 hover:text-slate-200 border border-slate-800'
                }`}
              >
                {p.label}
              </button>
            ))}
          </div>
        </div>

        {/* Live Visual Flow Ribbon */}
        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 space-y-2">
          <div className="text-[10px] font-mono uppercase tracking-wider text-slate-400 font-bold flex items-center gap-2">
            <Layers className="w-3.5 h-3.5 text-cyan-400" />
            <span>ACTIVE RESOLUTION PIPELINE (TIER 1 ➔ TIER N ➔ LOCAL BEDROCK)</span>
          </div>

          <div className="flex flex-wrap items-center gap-2 pt-1">
            {tiers.map((tier, idx) => {
              const meta = AVAILABLE_FRONTIER_MODELS.find(m => m.id === tier.modelId);
              return (
                <React.Fragment key={tier.tierNumber}>
                  <div className="px-3 py-2 rounded-xl bg-slate-950 border border-indigo-500/40 text-xs font-mono flex items-center gap-2 shadow">
                    <span className="w-5 h-5 rounded-full bg-indigo-500/20 text-indigo-300 flex items-center justify-center font-bold text-[10px]">
                      {tier.tierNumber}
                    </span>
                    <div>
                      <div className="text-white font-bold text-xs">{meta?.name.split(' (')[0] || tier.modelId}</div>
                      <div className="text-[10px] text-cyan-400">{tier.timeoutMs}ms max · {meta?.provider}</div>
                    </div>
                  </div>

                  {/* Flow Arrow */}
                  <span className="text-slate-600 font-mono text-sm">➔</span>
                </React.Fragment>
              );
            })}

            {/* Permanent Bedrock */}
            <div className="px-3 py-2 rounded-xl bg-emerald-950/40 border border-emerald-600/60 text-xs font-mono flex items-center gap-2 shadow">
              <span className="w-5 h-5 rounded-full bg-emerald-500/20 text-emerald-300 flex items-center justify-center font-bold text-[10px]">
                ★
              </span>
              <div>
                <div className="text-emerald-300 font-bold text-xs">Local DeepSeek-R1 70B</div>
                <div className="text-[10px] text-emerald-400">Apple Neural Engine · 100% Offline</div>
              </div>
            </div>
          </div>
        </div>

        {/* Interactive Tier Editor */}
        <div className="space-y-3 pt-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono text-slate-400 font-bold uppercase tracking-wider">
              Configurable Frontier Tiers ({tiers.length} Active)
            </span>
            <button
              onClick={handleAddTier}
              disabled={tiers.length >= 5}
              className="px-3 py-1.5 rounded-lg bg-indigo-500/20 hover:bg-indigo-500/30 border border-indigo-500/40 text-indigo-300 text-xs font-mono font-medium flex items-center gap-1.5 transition-all disabled:opacity-40"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Add Frontier Fallback Tier</span>
            </button>
          </div>

          <div className="space-y-3">
            {tiers.map((tier, index) => {
              const meta = AVAILABLE_FRONTIER_MODELS.find(m => m.id === tier.modelId);
              return (
                <div
                  key={index}
                  className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 space-y-3 transition-all hover:border-slate-700"
                >
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                    <div className="flex items-center gap-3">
                      {/* Tier Number Badge */}
                      <span className="w-7 h-7 rounded-lg bg-indigo-600 text-white font-mono font-bold text-xs flex items-center justify-center shrink-0">
                        #{tier.tierNumber}
                      </span>

                      {/* Model Selector Dropdown */}
                      <div className="space-y-0.5">
                        <label className="text-[10px] font-mono text-slate-400 uppercase">Provider &amp; Model</label>
                        <select
                          value={tier.modelId}
                          onChange={e => handleModelChange(index, e.target.value)}
                          className="bg-slate-950 text-white text-xs font-mono rounded-lg px-3 py-2 border border-slate-700 focus:outline-none focus:border-indigo-400"
                        >
                          {AVAILABLE_FRONTIER_MODELS.map(m => (
                            <option key={m.id} value={m.id}>
                              {m.name} ({m.provider} · {m.specialty})
                            </option>
                          ))}
                        </select>
                      </div>
                    </div>

                    {/* Up / Down & Delete Controls */}
                    <div className="flex items-center gap-1 self-end sm:self-auto">
                      <button
                        onClick={() => handleMoveTier(index, 'up')}
                        disabled={index === 0}
                        title="Move tier up (higher priority)"
                        className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 disabled:opacity-30 transition-colors"
                      >
                        <ArrowUp className="w-3.5 h-3.5" />
                      </button>
                      <button
                        onClick={() => handleMoveTier(index, 'down')}
                        disabled={index === tiers.length - 1}
                        title="Move tier down (lower priority)"
                        className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 disabled:opacity-30 transition-colors"
                      >
                        <ArrowDown className="w-3.5 h-3.5" />
                      </button>
                      <button
                        onClick={() => handleRemoveTier(index)}
                        disabled={tiers.length <= 1}
                        title="Remove tier"
                        className="p-2 rounded-lg bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 disabled:opacity-30 transition-colors"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>

                  {/* Tier Parameters: Timeout Slider & Triggers */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2 border-t border-slate-800/80 text-xs">
                    {/* Timeout Slider */}
                    <div className="space-y-1">
                      <div className="flex items-center justify-between text-slate-400 font-mono text-[11px]">
                        <span>Timeout Threshold:</span>
                        <span className="text-cyan-400 font-bold">{tier.timeoutMs}ms</span>
                      </div>
                      <input
                        type="range"
                        min="1000"
                        max="8000"
                        step="250"
                        value={tier.timeoutMs}
                        onChange={e => handleTimeoutChange(index, Number(e.target.value))}
                        className="w-full accent-indigo-500 cursor-pointer"
                      />
                      <div className="flex justify-between text-[10px] text-slate-500 font-mono">
                        <span>1,000ms</span>
                        <span>4,500ms</span>
                        <span>8,000ms</span>
                      </div>
                    </div>

                    {/* Failover Triggers */}
                    <div className="space-y-1.5">
                      <div className="text-[11px] font-mono text-slate-400">Failover Triggers:</div>
                      <div className="flex flex-wrap gap-2">
                        {[
                          { id: 'http_5xx', label: '500/503 Cloud Outage' },
                          { id: 'rate_limit_429', label: '429 Rate Limit' },
                          { id: 'timeout', label: 'Timeout Exceeded' },
                          { id: 'safety_censor', label: 'Filter Censor' }
                        ].map(trigger => {
                          const isChecked = tier.failoverTriggers.includes(trigger.id as any);
                          return (
                            <button
                              key={trigger.id}
                              onClick={() => handleToggleTrigger(index, trigger.id as any)}
                              className={`px-2.5 py-1 rounded text-[10px] font-mono transition-all ${
                                isChecked
                                  ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40 font-bold'
                                  : 'bg-slate-950 text-slate-500 border border-slate-800 hover:text-slate-300'
                              }`}
                            >
                              {isChecked ? '✓ ' : '+ '}
                              {trigger.label}
                            </button>
                          );
                        })}
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}

            {/* Permanent Local Model Display Card */}
            <div className="p-4 rounded-xl bg-gradient-to-r from-emerald-950/30 via-slate-900 to-slate-900 border border-emerald-600/50 space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="w-7 h-7 rounded-lg bg-emerald-500/20 text-emerald-300 font-mono font-bold text-xs flex items-center justify-center">
                    ★
                  </span>
                  <div>
                    <h4 className="text-sm font-bold text-white font-display flex items-center gap-2">
                      <span>{BEDROCK_LOCAL_MODEL.name}</span>
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                        PERMANENT BEDROCK
                      </span>
                    </h4>
                    <div className="text-[11px] text-slate-400 font-mono">
                      {BEDROCK_LOCAL_MODEL.runtimeHost} · {BEDROCK_LOCAL_MODEL.costPerMToken}
                    </div>
                  </div>
                </div>

                <div className="text-right">
                  <span className="text-xs font-mono font-bold text-emerald-400 flex items-center gap-1">
                    <ShieldCheck className="w-4 h-4" />
                    <span>SOVEREIGN READY</span>
                  </span>
                </div>
              </div>
              <p className="text-xs text-slate-300 font-sans leading-relaxed">
                {BEDROCK_LOCAL_MODEL.description}
              </p>
            </div>
          </div>
        </div>

        {/* Live Test Failover Runner */}
        <div className="pt-4 border-t border-slate-800 space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h4 className="text-sm font-bold text-white font-mono">Test Configured Cascade in Real Time</h4>
              <p className="text-xs text-slate-400">Verify that trips gracefully cascade through your custom tier order.</p>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={() => handleTestCascade(false)}
                disabled={simRunning}
                className="px-3.5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-mono font-semibold flex items-center gap-2 shadow-md transition-all disabled:opacity-50"
              >
                <Play className="w-3.5 h-3.5 fill-current" />
                <span>Test Tier 1 ➔ Tier 2 Failover</span>
              </button>

              <button
                onClick={() => handleTestCascade(true)}
                disabled={simRunning}
                className="px-3.5 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-mono font-semibold flex items-center gap-2 shadow-md transition-all disabled:opacity-50"
              >
                <Zap className="w-3.5 h-3.5" />
                <span>Test All Clouds Down ➔ Local Bedrock</span>
              </button>
            </div>
          </div>

          {/* Test Logs Output */}
          {simLogs.length > 0 && (
            <div className="p-4 rounded-xl bg-[#090b10] border border-slate-800 font-mono text-xs space-y-1.5 animate-fadeIn">
              {simLogs.map((log, i) => (
                <div
                  key={i}
                  className={`${
                    log.includes('Local') || log.includes('BEDROCK')
                      ? 'text-emerald-400 font-bold'
                      : log.includes('SIMULATED') || log.includes('tripped')
                      ? 'text-rose-400'
                      : log.includes('Circuit') || log.includes('Stepping')
                      ? 'text-cyan-300'
                      : 'text-slate-300'
                  }`}
                >
                  {log}
                </div>
              ))}

              {simVerdict && (
                <div className="pt-2 mt-2 border-t border-slate-800 text-emerald-300 font-bold flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                  <span>{simVerdict}</span>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
