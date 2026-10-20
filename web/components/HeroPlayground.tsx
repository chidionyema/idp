"use client";
import { useState, useEffect } from "react";

const MODELS = [
  { key: "gpt-4o-mini", label: "GPT-4o Mini", cost: "$0.15" },
  { key: "deepseek-chat", label: "DeepSeek V3", cost: "$0.27" },
  { key: "claude-sonnet-4", label: "Claude Sonnet 4", cost: "$3.00" },
  { key: "gemini-2.0-flash", label: "Gemini 2.0 Flash", cost: "Free" },
];

export function HeroPlayground() {
  const [selected, setSelected] = useState("gpt-4o-mini");
  const [message, setMessage] = useState("How does agentic routing reduce LLM costs at scale?");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<{ response: string; model: string; latency: number; totalTokens: number; costUsd: number; mode: string } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [displayedText, setDisplayedText] = useState("");
  const [streamDone, setStreamDone] = useState(false);

  const response = result?.response;

  useEffect(() => {
    if (!response) return;
    const text = response;
    setDisplayedText("");
    setStreamDone(false);
    let i = 0;
    const interval = setInterval(() => {
      i += 4;
      setDisplayedText(text.slice(0, i));
      if (i >= text.length) { clearInterval(interval); setStreamDone(true); }
    }, 10);
    return () => clearInterval(interval);
  }, [response]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!message.trim() || loading) return;
    setLoading(true);
    setError(null);
    setResult(null);
    setDisplayedText("");
    try {
      const res = await fetch("/api/route", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ message: message.trim(), model: selected }) });
      if (!res.ok) { setError("Request failed"); return; }
      setResult(await res.json());
    } catch { setError("Network error"); }
    finally { setLoading(false); }
  }

  return (
    <form onSubmit={handleSubmit} style={{ display: "grid", gap: "24px", gridTemplateColumns: "1fr" }}>
      <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
        <div>
          <p style={{ fontFamily: "var(--mono)", fontSize: "11px", fontWeight: 500, letterSpacing: "0.08em", textTransform: "uppercase", color: "var(--ink-3)", marginBottom: "8px" }}>Model</p>
          <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
            {MODELS.map((m) => (
              <button key={m.key} type="button" onClick={() => setSelected(m.key)}
                style={{
                  display: "flex", justifyContent: "space-between", alignItems: "center",
                  padding: "10px 12px", border: `1px solid ${selected === m.key ? "var(--accent)" : "var(--rule)"}`,
                  background: selected === m.key ? "rgba(14,110,98,0.06)" : "transparent",
                  color: selected === m.key ? "var(--accent)" : "var(--ink-3)", fontWeight: selected === m.key ? 500 : 400,
                  cursor: "pointer", fontSize: "12px", fontFamily: "var(--mono)", textAlign: "left",
                  transition: "all 120ms ease",
                }}>
                <span>{m.label}</span><span>{m.cost}/1M</span>
              </button>
            ))}
          </div>
        </div>
        <div>
          <p style={{ fontFamily: "var(--mono)", fontSize: "11px", fontWeight: 500, letterSpacing: "0.08em", textTransform: "uppercase", color: "var(--ink-3)", marginBottom: "8px" }}>Prompt</p>
          <textarea value={message} onChange={(e) => setMessage(e.target.value)} rows={3}
            style={{ width: "100%", resize: "none", border: "1px solid var(--rule)", background: "var(--white)", padding: "12px", fontSize: "13px", color: "var(--ink)", fontFamily: "inherit", outline: "none" }}
            onFocus={(e) => e.target.style.borderColor = "var(--accent)"}
            onBlur={(e) => e.target.style.borderColor = "var(--rule)"} />
        </div>
        <button type="submit" disabled={loading || !message.trim()} className="btn-primary" style={{ justifyContent: "center" }}>
          {loading ? <span style={{ display: "flex", alignItems: "center", gap: "8px" }}><span className="pulse-dot" style={{ background: "#fff" }} />Routing…</span> : "Run →"}
        </button>
        {result?.mode === "demo" && <p style={{ fontFamily: "var(--mono)", fontSize: "11px", color: "var(--ink-3)" }}>Demo mode — configure LITELLM_PROXY_URL for live calls</p>}
      </div>
      <div style={{ minHeight: "200px", border: "1px solid var(--rule)", background: "var(--panel)", padding: "20px" }}>
        {!result && !loading && !error && <p style={{ fontFamily: "var(--mono)", fontSize: "12px", color: "var(--ink-3)" }}>Response will appear here…</p>}
        {loading && (
          <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
            <p style={{ fontFamily: "var(--mono)", fontSize: "12px", color: "var(--ink-3)" }}><span className="pulse-dot" style={{ marginRight: "8px" }} />{MODELS.find((m) => m.key === selected)?.label} is thinking…</p>
            <div style={{ height: "3px", background: "var(--rule)", borderRadius: "2px", overflow: "hidden" }}><div style={{ height: "100%", width: "55%", background: "var(--accent)", opacity: 0.6 }} /></div>
          </div>
        )}
        {error && <p style={{ fontFamily: "var(--mono)", fontSize: "12px", color: "#DC2626" }}>{error}</p>}
        {displayedText && (
          <div>
            {result && (
              <div style={{ display: "flex", flexWrap: "wrap", gap: "24px", paddingBottom: "16px", marginBottom: "16px", borderBottom: "1px solid var(--rule)" }}>
                {[{ label: "Model", value: result.model }, { label: "Latency", value: `${result.latency}ms` }, { label: "Tokens", value: result.totalTokens.toLocaleString() }, { label: "Cost", value: `$${result.costUsd.toFixed(5)}` }].map((m) => (
                  <div key={m.label}><span style={{ fontFamily: "var(--mono)", fontSize: "11px", color: "var(--ink-3)" }}>{m.label}</span><span style={{ fontFamily: "var(--mono)", fontSize: "12px", fontWeight: 600, color: "var(--accent)", marginLeft: "8px" }}>{m.value}</span></div>
                ))}
              </div>
            )}
            <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
              {displayedText.split("\n\n").map((para, i) => <p key={i} style={{ fontSize: "14px", lineHeight: 1.75, color: "var(--ink-2)" }}>{para}</p>)}
            </div>
            {!streamDone && <span className="pulse-dot" style={{ marginTop: "12px" }} />}
            {streamDone && <p style={{ fontFamily: "var(--mono)", fontSize: "11px", color: "var(--ink-3)", marginTop: "16px", paddingTop: "16px", borderTop: "1px solid var(--rule)" }}>End of response</p>}
          </div>
        )}
      </div>
    </form>
  );
}
