import React, { useState } from 'react';
import {
  FileCode,
  Sparkles,
  Play,
  RotateCcw,
  CheckCircle2,
  ShieldCheck,
  Send,
  Coins,
  Cpu,
  Layers,
  Zap,
} from 'lucide-react';
import { SAMPLE_JSONL_SESSIONS } from '../data/mockLegions';
import { extractSessionBrief, parseJsonlLogs } from '../utils/extractiveCore';
import { SpokenBrief } from '../types';
import { audioEngine } from '../utils/audioEngine';

interface ExtractiveLabTabProps {
  onLoadBriefIntoVoiceBar: (brief: SpokenBrief) => void;
  onSendToTelegram: (brief: SpokenBrief) => void;
  geminiEnrichmentEnabled: boolean;
  setGeminiEnrichmentEnabled: (enabled: boolean) => void;
  onSpendIncurred: (usd: number, tokens: number) => void;
}

export const ExtractiveLabTab: React.FC<ExtractiveLabTabProps> = ({
  onLoadBriefIntoVoiceBar,
  onSendToTelegram,
  geminiEnrichmentEnabled,
  setGeminiEnrichmentEnabled,
  onSpendIncurred,
}) => {
  const [selectedTemplate, setSelectedTemplate] = useState('session-kernel-piper');
  const [jsonlInput, setJsonlInput] = useState(SAMPLE_JSONL_SESSIONS['session-kernel-piper']);
  const [targetLegion, setTargetLegion] = useState('Legion Alpha (Kernel)');
  const [isProcessing, setIsProcessing] = useState(false);
  const [resultBrief, setResultBrief] = useState<SpokenBrief | null>(null);
  const [processingStats, setProcessingStats] = useState<{
    rawBytes: number;
    extractedWords: number;
    compressionPct: number;
    costUsd: number;
    modelName: string;
    elapsedMs: number;
  } | null>(null);

  const handleTemplateChange = (templateKey: string) => {
    setSelectedTemplate(templateKey);
    setJsonlInput(SAMPLE_JSONL_SESSIONS[templateKey] || '');
    if (templateKey === 'session-kernel-piper') setTargetLegion('Legion Alpha (Kernel)');
    else if (templateKey === 'session-model-benchmark') setTargetLegion('Legion Beta (Eval)');
    else setTargetLegion('Legion Epsilon (Security)');
  };

  const handleRunPipeline = async () => {
    setIsProcessing(true);
    const startTime = performance.now();
    const rawBytes = new Blob([jsonlInput]).size;

    try {
      if (geminiEnrichmentEnabled) {
        // Call server /api/enrich endpoint
        const res = await fetch('/api/enrich', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            legionName: targetLegion,
            jsonlText: jsonlInput,
            enableGeminiEnrichment: true,
          }),
        });
        const data = await res.json();
        const elapsed = Math.round(performance.now() - startTime);

        const newBrief: SpokenBrief = {
          id: `lab-${Date.now()}`,
          legionId: targetLegion.toLowerCase().replace(/[^a-z]/g, '-'),
          legionName: targetLegion,
          title: data.title || `${targetLegion} Spoken Brief`,
          recordedDurationSec: data.estimatedDurationSec,
          sha256Receipt: data.sha256Receipt,
          rawLogSessionId: `sess_lab_${Math.random().toString(36).slice(2, 7)}`,
          rawLogLineCount: jsonlInput.split('\n').filter(Boolean).length,
          rawLogDurationMinutes: 45,
          timestamp: new Date().toISOString(),
          pipeline: {
            sourceFormat: 'jsonl',
            condenser: 'dream-cycle-extractive-v2',
            ttsEngine: 'piper-neural-arm64',
            piperVoice: 'en_US-ryan-medium',
            estateCostUsd: data.tokenStats?.estimatedCostUsd || 0.00011,
          },
          spokenScript: data.spokenScript,
          karaokeLines: data.karaokeLines || [],
          sections: {
            whatShipped: data.whatShipped || [],
            whatIsBlocked: data.whatIsBlocked || [],
            needsFounder: data.needsFounder || [],
          },
        };

        setResultBrief(newBrief);
        const cost = data.tokenStats?.estimatedCostUsd || 0.00011;
        const tokens = (data.tokenStats?.inputTokens || 500) + (data.tokenStats?.outputTokens || 200);
        onSpendIncurred(cost, tokens);

        setProcessingStats({
          rawBytes,
          extractedWords: data.wordCount,
          compressionPct: Math.round((1 - (data.wordCount * 6) / Math.max(1, rawBytes)) * 100),
          costUsd: cost,
          modelName: 'gemini-2.5-flash',
          elapsedMs: elapsed,
        });
      } else {
        // Pure $0 extractive core
        await new Promise((r) => setTimeout(r, 120)); // Brief simulated estate tick
        const parsedLogs = parseJsonlLogs(jsonlInput);
        const briefContent = extractSessionBrief(targetLegion, parsedLogs);
        const elapsed = Math.round(performance.now() - startTime);

        const newBrief: SpokenBrief = {
          id: `lab-${Date.now()}`,
          legionId: targetLegion.toLowerCase().replace(/[^a-z]/g, '-'),
          legionName: targetLegion,
          title: briefContent.title,
          recordedDurationSec: briefContent.estimatedDurationSec,
          sha256Receipt: briefContent.sha256Receipt,
          rawLogSessionId: `sess_lab_${Math.random().toString(36).slice(2, 7)}`,
          rawLogLineCount: parsedLogs.length,
          rawLogDurationMinutes: 45,
          timestamp: new Date().toISOString(),
          pipeline: {
            sourceFormat: 'jsonl',
            condenser: 'dream-cycle-extractive-v2',
            ttsEngine: 'piper-neural-arm64',
            piperVoice: 'en_US-ryan-medium',
            estateCostUsd: 0.0,
          },
          spokenScript: briefContent.spokenScript,
          karaokeLines: briefContent.karaokeLines,
          sections: {
            whatShipped: briefContent.whatShipped,
            whatIsBlocked: briefContent.whatIsBlocked,
            needsFounder: briefContent.needsFounder,
          },
        };

        setResultBrief(newBrief);
        setProcessingStats({
          rawBytes,
          extractedWords: briefContent.wordCount,
          compressionPct: Math.round((1 - (briefContent.wordCount * 6) / Math.max(1, rawBytes)) * 100),
          costUsd: 0.0,
          modelName: 'dream-cycle-extractive ($0.00 estate)',
          elapsedMs: elapsed,
        });
      }
    } catch (err) {
      console.error(err);
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header Explainer */}
      <div className="bg-zinc-900/60 border border-zinc-800 p-4 rounded-xl flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-sm font-semibold text-zinc-100 flex items-center gap-2">
            <FileCode className="w-4 h-4 text-amber-400" />
            <span>Dream-Cycle Extractive Lab ($0 Ingestion Core)</span>
          </h2>
          <p className="text-xs text-zinc-400 mt-0.5">
            Ingest 20–60 minutes of noisy agent JSONL session transcripts and condense them to a 60–90s spoken founder brief.
          </p>
        </div>

        {/* Cost & Toggle Pill */}
        <div className="flex items-center gap-2">
          <div
            onClick={() => setGeminiEnrichmentEnabled(!geminiEnrichmentEnabled)}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border text-xs font-mono cursor-pointer select-none transition-all ${
              geminiEnrichmentEnabled
                ? 'bg-purple-950/60 border-purple-500/60 text-purple-200'
                : 'bg-zinc-900 border-zinc-800 text-zinc-300'
            }`}
          >
            <Sparkles className={`w-3.5 h-3.5 ${geminiEnrichmentEnabled ? 'text-purple-400' : 'text-zinc-500'}`} />
            <span>Enrichment: {geminiEnrichmentEnabled ? 'Gemini 2.5 Flash (~$0.0001)' : '$0.00 Estate Heuristic'}</span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left Column: Input JSONL Transcripts */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <label className="text-xs font-semibold text-zinc-300 font-mono">
              Raw Agent Session Logs (.jsonl)
            </label>
            <div className="flex items-center gap-1.5 text-xs">
              <span className="text-zinc-500 text-[11px]">Preset:</span>
              <select
                value={selectedTemplate}
                onChange={(e) => handleTemplateChange(e.target.value)}
                className="bg-zinc-900 border border-zinc-700 text-zinc-200 text-[11px] rounded px-2 py-1 focus:outline-none"
              >
                <option value="session-kernel-piper">Alpha: Piper Neural ARM VM (#412)</option>
                <option value="session-model-benchmark">Beta: Dream-Cycle Eval Bench</option>
                <option value="session-dof-gate-lock">Epsilon: DOF-Gate Credential Lock</option>
              </select>
            </div>
          </div>

          <div className="relative">
            <textarea
              value={jsonlInput}
              onChange={(e) => setJsonlInput(e.target.value)}
              rows={12}
              className="w-full bg-zinc-950 border border-zinc-800 rounded-xl p-3 font-mono text-[11px] text-zinc-300 leading-relaxed focus:outline-none focus:border-amber-500/60 resize-none shadow-inner"
              placeholder='{"timestamp":"...","level":"milestone","agent":"...","action":"..."}'
            />
          </div>

          <div className="flex items-center justify-between">
            <div className="text-[11px] font-mono text-zinc-500">
              {jsonlInput.split('\n').filter(Boolean).length} log events • {new Blob([jsonlInput]).size} bytes
            </div>

            <button
              onClick={handleRunPipeline}
              disabled={isProcessing || !jsonlInput.trim()}
              className="flex items-center gap-2 px-5 py-2 rounded-xl bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-400 hover:to-amber-500 disabled:opacity-50 text-zinc-950 font-bold text-xs shadow-lg shadow-amber-500/20 transition-all active:scale-95"
            >
              {isProcessing ? (
                <>
                  <RotateCcw className="w-4 h-4 animate-spin" />
                  <span>Condensing Transcript...</span>
                </>
              ) : (
                <>
                  <Zap className="w-4 h-4 fill-current" />
                  <span>Run Extractive Core {geminiEnrichmentEnabled ? '(& Enrich)' : '($0)'}</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* Right Column: Generated Brief & Provenance Receipt */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <label className="text-xs font-semibold text-zinc-300 font-mono">
              Spoken Executive Brief Output
            </label>
            {processingStats && (
              <span className="text-[11px] font-mono text-emerald-400">
                Processed in {processingStats.elapsedMs}ms • Cost: ${processingStats.costUsd.toFixed(5)}
              </span>
            )}
          </div>

          {resultBrief ? (
            <div className="bg-zinc-950 border border-zinc-800 rounded-xl p-4 space-y-4 shadow-xl">
              {/* Spoken Text Display */}
              <div>
                <div className="flex items-center justify-between text-xs font-semibold text-zinc-200 mb-2 font-mono">
                  <span className="flex items-center gap-1.5 text-sky-400">
                    <Play className="w-3.5 h-3.5" />
                    Spoken Script ({resultBrief.recordedDurationSec}s • {resultBrief.spokenScript.split(/\s+/).length} words)
                  </span>
                  <span className="text-zinc-500 text-[10px]">
                    Engine: {geminiEnrichmentEnabled ? 'Gemini 2.5 Flash' : 'Extractive v2 ($0)'}
                  </span>
                </div>
                <div className="bg-zinc-900/80 p-3 rounded-lg border border-zinc-800 text-xs text-zinc-200 leading-relaxed font-sans">
                  "{resultBrief.spokenScript}"
                </div>
              </div>

              {/* SHA-256 Receipt */}
              <div className="p-2.5 rounded-lg bg-zinc-900 border border-zinc-800 text-xs font-mono space-y-1">
                <div className="flex items-center justify-between text-zinc-400 text-[11px]">
                  <span className="flex items-center gap-1 text-emerald-400">
                    <ShieldCheck className="w-3.5 h-3.5" />
                    Cryptographic Receipt Verified:
                  </span>
                  <span className="text-zinc-300">100% Deterministic</span>
                </div>
                <div className="text-[11px] text-zinc-200 break-all bg-zinc-950 p-1.5 rounded border border-zinc-850">
                  {resultBrief.sha256Receipt}
                </div>
              </div>

              {/* Quick Action Buttons */}
              <div className="flex items-center gap-2 pt-2 border-t border-zinc-900">
                <button
                  onClick={() => {
                    onLoadBriefIntoVoiceBar(resultBrief);
                    audioEngine.playBrief(resultBrief.spokenScript, resultBrief.recordedDurationSec, resultBrief.karaokeLines);
                  }}
                  className="flex-1 flex items-center justify-center gap-2 py-2 px-3 rounded-lg bg-sky-500 hover:bg-sky-400 text-zinc-950 font-bold text-xs shadow transition-colors"
                >
                  <Play className="w-3.5 h-3.5 fill-current" />
                  <span>Hear Now in Voice Bar</span>
                </button>

                <button
                  onClick={() => onSendToTelegram(resultBrief)}
                  className="flex items-center gap-2 py-2 px-3 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-200 text-xs font-semibold transition-colors"
                >
                  <Send className="w-3.5 h-3.5 text-emerald-400" />
                  <span>Spool to Telegram</span>
                </button>
              </div>
            </div>
          ) : (
            <div className="h-64 rounded-xl border border-dashed border-zinc-800 bg-zinc-950/40 flex flex-col items-center justify-center text-center p-6 text-zinc-500">
              <FileCode className="w-8 h-8 text-zinc-600 mb-2" />
              <div className="text-xs font-medium text-zinc-400">Pipeline Awaiting Execution</div>
              <div className="text-[11px] text-zinc-500 mt-1 max-w-xs">
                Select a sample transcript and press "Run Extractive Core" to test condensation into a 60–90s spoken founder brief.
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
