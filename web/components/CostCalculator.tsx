"use client";
import { useState } from "react";

interface Model { key: string; label: string; inputPer1M: number; outputPer1M: number; provider: string; color: string; }
const MODELS: Model[] = [
  { key: "gpt-4o-mini", label: "GPT-4o Mini", inputPer1M: 0.15, outputPer1M: 0.60, provider: "OpenAI", color: "#1A56DB" },
  { key: "gpt-4o", label: "GPT-4o", inputPer1M: 2.50, outputPer1M: 10.00, provider: "OpenAI", color: "#1A56DB" },
  { key: "claude-sonnet-4", label: "Claude Sonnet 4", inputPer1M: 3.00, outputPer1M: 15.00, provider: "Anthropic", color: "#059669" },
  { key: "gemini-2.0-flash", label: "Gemini 2.0 Flash", inputPer1M: 0, outputPer1M: 0, provider: "Google", color: "#D97706" },
  { key: "deepseek-v3", label: "DeepSeek V3", inputPer1M: 0.27, outputPer1M: 1.10, provider: "DeepSeek", color: "#7C3AED" },
];

function fmtUsd(n: number): string {
  if (n === 0) return "Free";
  if (n < 0.001) return `$${n.toFixed(6)}`;
  if (n < 1) return `$${n.toFixed(4)}`;
  if (n < 1000) return `$${n.toFixed(2)}`;
  if (n < 1_000_000) return `$${(n / 1000).toFixed(2)}K`;
  return `$${(n / 1_000_000).toFixed(2)}M`;
}
function fmtNum(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1000) return `${(n / 1000).toFixed(0)}K`;
  return n.toLocaleString();
}
function costFor(model: Model, inTok: number, outTok: number): number {
  if (model.inputPer1M === 0) return 0;
  return (inTok / 1_000_000) * model.inputPer1M + (outTok / 1_000_000) * model.outputPer1M;
}

export function CostCalculator() {
  const [inputTokens, setInputTokens] = useState(500);
  const [outputTokens, setOutputTokens] = useState(800);
  const [dailyRequests, setDailyRequests] = useState(1000);
  const [selectedModel, setSelectedModel] = useState("gpt-4o-mini");
  const model = MODELS.find((m) => m.key === selectedModel)!;
  const costPerReq = costFor(model, inputTokens, outputTokens);
  const costPerDay = costPerReq * dailyRequests;
  const costPerMonth = costPerDay * 30;
  const costPerYear = costPerDay * 365;
  const sorted = MODELS.filter((m) => m.inputPer1M > 0).sort((a, b) => costFor(a, inputTokens, outputTokens) - costFor(b, inputTokens, outputTokens));
  const cheapest = sorted[0];
  const cheapestCost = cheapest ? costFor(cheapest, inputTokens, outputTokens) : 0;
  const vsCheapest = cheapest && costPerReq > 0 && cheapestCost > 0 ? (costPerReq / cheapestCost) - 1 : 0;

  return (
    <div style={{ display: "grid", gap: "48px", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))" }}>
      <div style={{ display: "flex", flexDirection: "column", gap: "32px" }}>
        {[{ label: "Input tokens / request", value: inputTokens, setValue: setInputTokens, max: 128000, step: 50 }, { label: "Output tokens / request", value: outputTokens, setValue: setOutputTokens, max: 64000, step: 50 }, { label: "Daily requests", value: dailyRequests, setValue: setDailyRequests, max: 1_000_000, step: 10 }].map((slider) => (
          <div key={slider.label}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "12px" }}>
              <label style={{ fontFamily: "var(--mono)", fontSize: "11px", fontWeight: 500, letterSpacing: "0.08em", textTransform: "uppercase", color: "var(--ink-3)" }}>{slider.label}</label>
              <span style={{ fontFamily: "var(--mono)", fontSize: "13px", fontWeight: 600, color: "var(--accent)" }}>{fmtNum(slider.value)}</span>
            </div>
            <input type="range" min={slider.step} max={slider.max} step={slider.step} value={slider.value} onChange={(e) => slider.setValue(Number(e.target.value))} className="cost-range" />
          </div>
        ))}
        <div>
          <p style={{ fontFamily: "var(--mono)", fontSize: "11px", fontWeight: 500, letterSpacing: "0.08em", textTransform: "uppercase", color: "var(--ink-3)", marginBottom: "12px" }}>Model</p>
          <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
            {MODELS.map((m) => {
              const c = costFor(m, inputTokens, outputTokens);
              const sel = selectedModel === m.key;
              return (
                <button key={m.key} onClick={() => setSelectedModel(m.key)} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "12px", border: `1px solid ${sel ? "var(--accent)" : "var(--rule)"}`, background: sel ? "rgba(14,110,98,0.06)" : "transparent", cursor: "pointer", textAlign: "left", fontFamily: "inherit", fontSize: "13px", color: sel ? "var(--ink)" : "var(--ink-2)", fontWeight: sel ? 500 : 400, transition: "all 120ms ease" }}>
                  <span style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                    <span style={{ width: "8px", height: "8px", borderRadius: "50%", background: m.color, flexShrink: 0 }} />
                    <span style={{ fontFamily: "var(--mono)", fontSize: "11px", color: "var(--ink-3)" }}>{m.provider}</span>
                    <span>{m.label}</span>
                  </span>
                  <span style={{ fontFamily: "var(--mono)", fontSize: "11px", color: "var(--ink-3)" }}>{m.inputPer1M === 0 ? "Free" : `${fmtUsd(c)}/req`}</span>
                </button>
              );
            })}
          </div>
        </div>
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "12px" }}>
          {[{ label: "Per request", value: costPerReq, hint: `${fmtNum(inputTokens + outputTokens)} tokens` }, { label: "Per day", value: costPerDay, hint: `${fmtNum(dailyRequests)} reqs` }, { label: "Per month", value: costPerMonth, hint: `${fmtNum(dailyRequests * 30)} reqs` }].map((t) => (
            <div key={t.label} style={{ border: "1px solid var(--rule)", background: "var(--white)", padding: "16px", textAlign: "center" }}>
              <p style={{ fontFamily: "var(--mono)", fontSize: "11px", color: "var(--ink-3)" }}>{t.label}</p>
              <p style={{ fontFamily: "var(--mono)", fontSize: "18px", fontWeight: 600, color: model.inputPer1M === 0 ? "var(--ok)" : "var(--accent)", marginTop: "8px" }}>{model.inputPer1M === 0 ? "Free" : fmtUsd(t.value)}</p>
              <p style={{ fontFamily: "var(--mono)", fontSize: "10px", color: "var(--ink-3)", marginTop: "4px" }}>{t.hint}</p>
            </div>
          ))}
        </div>
        {model.inputPer1M > 0 && (
          <div style={{ border: "1px solid rgba(26,86,219,0.2)", background: "rgba(26,86,219,0.03)", padding: "16px" }}>
            <p style={{ fontFamily: "var(--mono)", fontSize: "11px", color: "var(--ink-3)" }}>Annual projection</p>
            <p style={{ fontFamily: "var(--mono)", fontSize: "24px", fontWeight: 600, color: "var(--accent)", marginTop: "4px" }}>{fmtUsd(costPerYear)}</p>
            <p style={{ fontFamily: "var(--mono)", fontSize: "11px", color: "var(--ink-3)", marginTop: "4px" }}>{fmtNum(dailyRequests * 365)} requests / year</p>
          </div>
        )}
        {vsCheapest > 0 && (
          <div style={{ border: "1px solid var(--rule)", padding: "16px" }}>
            <p style={{ fontFamily: "var(--mono)", fontSize: "11px", color: "var(--ink-3)" }}>vs cheapest model ({cheapest.label})</p>
            <p style={{ fontFamily: "var(--mono)", fontSize: "24px", fontWeight: 600, color: "var(--signal)", marginTop: "4px" }}>+{(vsCheapest * 100).toFixed(0)}%</p>
          </div>
        )}
        <div style={{ border: "1px solid var(--rule)", padding: "16px" }}>
          <p style={{ fontFamily: "var(--mono)", fontSize: "11px", color: "var(--ink-3)", marginBottom: "16px" }}>All models — monthly cost</p>
          <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
            {MODELS.map((m) => {
              const c = costFor(m, inputTokens, outputTokens);
              const monthly = c * dailyRequests * 30;
              const pct = model.inputPer1M > 0 && c > 0 && costPerReq > 0 ? (c / costPerReq) * 100 : c === 0 ? 0 : 100;
              return (
                <div key={m.key} style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                  <span style={{ width: "8px", height: "8px", borderRadius: "50%", background: m.color, flexShrink: 0 }} />
                  <span style={{ width: "140px", fontFamily: "var(--mono)", fontSize: "11px", color: "var(--ink-2)", flexShrink: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{m.label}</span>
                  <div style={{ flex: 1, height: "6px", background: "var(--rule)", borderRadius: "3px", overflow: "hidden" }}>
                    <div style={{ height: "100%", width: `${Math.max(pct, 1)}%`, background: m.color, borderRadius: "3px", transition: "width 300ms ease", minWidth: c === 0 ? "100%" : undefined }} />
                  </div>
                  <span style={{ width: "80px", fontFamily: "var(--mono)", fontSize: "11px", color: "var(--ink-3)", textAlign: "right", flexShrink: 0 }}>{m.inputPer1M === 0 ? "Free" : fmtUsd(monthly)}</span>
                </div>
              );
            })}
          </div>
        </div>
        <div style={{ border: "1px solid var(--rule)", padding: "16px" }}>
          <p style={{ fontFamily: "var(--mono)", fontSize: "11px", color: "var(--ink-3)", marginBottom: "12px" }}>Per-token pricing</p>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
            {[{ label: "Input", value: model.inputPer1M }, { label: "Output", value: model.outputPer1M }].map((r) => (
              <div key={r.label} style={{ textAlign: "center" }}>
                <p style={{ fontFamily: "var(--mono)", fontSize: "11px", color: "var(--ink-3)" }}>{r.label}</p>
                <p style={{ fontFamily: "var(--mono)", fontSize: "14px", fontWeight: 600, color: "var(--ink)", marginTop: "4px" }}>{r.value === 0 ? "Free" : `$${r.value.toFixed(2)}`}</p>
                <p style={{ fontFamily: "var(--mono)", fontSize: "10px", color: "var(--ink-3)", marginTop: "2px" }}>/ 1M tokens</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
