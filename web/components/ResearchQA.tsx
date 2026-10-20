"use client";
import { useState, useRef } from "react";

const SUGGESTIONS = [
  "How does SPIFFE work with ephemeral AI containers?",
  "What is the minimum infrastructure for a production LLM proxy?",
  "How do you measure latency in an agentic pipeline?",
  "What does a circuit breaker pattern look like for LLM routing?",
  "How do you red-team an LLM pipeline?",
];

export function ResearchQA() {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<{ answer: string; sources: { id: string; section: string; relevance: number }[]; mode: string } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [history, setHistory] = useState<{ q: string; a: typeof result }[]>([]);
  const inputRef = useRef<HTMLInputElement>(null);

  async function handleAsk(e: React.FormEvent) {
    e.preventDefault();
    if (!query.trim() || loading) return;
    const q = query.trim();
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await fetch("/api/research/query", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ query: q }) });
      if (!res.ok) { const err = await res.json(); setError(err.error ?? "Failed"); return; }
      const data = await res.json();
      setResult(data);
      setHistory((prev) => [{ q, a: data }, ...prev.slice(0, 4)]);
      setQuery("");
    } catch { setError("Network error"); }
    finally { setLoading(false); }
  }

  return (
    <div style={{ display: "grid", gap: "32px", gridTemplateColumns: "1fr 2fr" }}>
      <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
        <form onSubmit={handleAsk}>
          <p style={{ fontFamily: "var(--mono)", fontSize: "11px", fontWeight: 500, letterSpacing: "0.08em", textTransform: "uppercase", color: "var(--ink-3)", marginBottom: "12px" }}>Ask about our research</p>
          <div style={{ position: "relative" }}>
            <input ref={inputRef} type="text" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="e.g. How does SPIFFE work with AI workloads?"
              style={{ width: "100%", border: "1px solid var(--rule)", background: "var(--white)", padding: "12px 40px 12px 16px", fontSize: "14px", color: "var(--ink)", outline: "none", fontFamily: "inherit" }}
              onFocus={(e) => e.target.style.borderColor = "var(--accent)"}
              onBlur={(e) => e.target.style.borderColor = "var(--rule)"} />
            <button type="submit" disabled={loading || !query.trim()} style={{ position: "absolute", right: "12px", top: "50%", transform: "translateY(-50%)", background: "none", border: "none", cursor: loading ? "default" : "pointer", color: "var(--accent)", opacity: loading || !query.trim() ? 0.3 : 1 }}>
              {loading ? <span className="pulse-dot" /> : <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M2 8L14 8M10 4L14 8L10 12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/></svg>}
            </button>
          </div>
        </form>
        <div>
          <p style={{ fontFamily: "var(--mono)", fontSize: "11px", color: "var(--ink-3)", marginBottom: "12px" }}>Try asking about</p>
          <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
            {SUGGESTIONS.map((s) => (
              <button key={s} onClick={() => { setQuery(s); inputRef.current?.focus(); }}
                style={{ border: "1px solid var(--rule)", background: "var(--white)", padding: "10px 12px", fontFamily: "var(--mono)", fontSize: "11px", color: "var(--ink-2)", cursor: "pointer", textAlign: "left", transition: "all 120ms ease" }}
                onMouseEnter={(e) => { (e.currentTarget as HTMLButtonElement).style.borderColor = "rgba(14,110,98,0.4)"; (e.currentTarget as HTMLButtonElement).style.background = "rgba(14,110,98,0.04)"; (e.currentTarget as HTMLButtonElement).style.color = "var(--accent)"; }}
                onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.borderColor = "var(--rule)"; (e.currentTarget as HTMLButtonElement).style.background = "var(--white)"; (e.currentTarget as HTMLButtonElement).style.color = "var(--ink-2)"; }}>
                {s}
              </button>
            ))}
          </div>
        </div>
        {history.length > 0 && (
          <div>
            <p style={{ fontFamily: "var(--mono)", fontSize: "11px", color: "var(--ink-3)", marginBottom: "12px" }}>Recent</p>
            <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
              {history.map((h, i) => (
                <button key={i} onClick={() => { setQuery(h.q); setResult(h.a); inputRef.current?.focus(); }}
                  style={{ border: "1px solid var(--rule)", background: "var(--panel)", padding: "10px 12px", fontFamily: "var(--mono)", fontSize: "11px", color: "var(--ink-3)", cursor: "pointer", textAlign: "left" }}>
                  {h.q}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
      <div style={{ minHeight: "220px", border: "1px solid var(--rule)", background: "var(--white)", padding: "24px" }}>
        {!result && !loading && !error && (
          <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            <p style={{ fontFamily: "var(--mono)", fontSize: "12px", color: "var(--ink-3)" }}>Ask a question about our research to get a grounded answer with citations.</p>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
              {[{ tag: "Routing", desc: "Fallback chains, model selection, circuit breakers" }, { tag: "SPIFFE", desc: "Workload identity for ephemeral AI containers" }, { tag: "Observability", desc: "Span trees, latency budgets, Langfuse" }, { tag: "Security", desc: "LLM red-teaming, prompt injection, eval harnesses" }].map((t) => (
                <div key={t.tag} style={{ border: "1px solid var(--rule)", background: "var(--panel)", padding: "12px" }}>
                  <p style={{ fontFamily: "var(--mono)", fontSize: "11px", fontWeight: 600, color: "var(--accent)" }}>{t.tag}</p>
                  <p style={{ fontFamily: "var(--mono)", fontSize: "11px", color: "var(--ink-3)", marginTop: "4px" }}>{t.desc}</p>
                </div>
              ))}
            </div>
        </div>
        )}
        {loading && (
          <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <span className="pulse-dot" /><span style={{ fontFamily: "var(--mono)", fontSize: "12px", color: "var(--ink-3)" }}>Searching research corpus…</span>
            </div>
            <div style={{ height: "3px", background: "var(--rule)", borderRadius: "2px", overflow: "hidden" }}><div style={{ height: "100%", width: "60%", background: "var(--accent)", opacity: 0.5 }} /></div>
          </div>
        )}
        {error && <p style={{ fontFamily: "var(--mono)", fontSize: "12px", color: "#DC2626" }}>{error}</p>}
        {result && (
          <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", paddingBottom: "16px", borderBottom: "1px solid var(--rule)" }}>
              <span style={{ fontFamily: "var(--mono)", fontSize: "11px", color: "var(--ink-3)" }}>Answer</span>
              <span style={{ fontFamily: "var(--mono)", fontSize: "11px", color: result.mode === "gpt-enhanced" ? "var(--ok-text)" : "var(--accent)" }}>● {result.mode === "gpt-enhanced" ? "GPT-4o Mini enhanced" : "Research corpus"}</span>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
              {result.answer.split("\n\n").map((para, i) => <p key={i} style={{ fontSize: "14px", lineHeight: 1.75, color: "var(--ink-2)" }}>{para}</p>)}
            </div>
            {result.sources.length > 0 && (
              <div style={{ paddingTop: "16px", borderTop: "1px solid var(--rule)" }}>
                <p style={{ fontFamily: "var(--mono)", fontSize: "11px", color: "var(--ink-3)", marginBottom: "12px" }}>Sources</p>
                <div style={{ display: "flex", flexWrap: "wrap", gap: "8px" }}>
                  {result.sources.map((s) => (
                    <div key={s.id} style={{ border: "1px solid var(--rule)", background: "var(--panel)", padding: "8px 12px" }}>
                      <p style={{ fontFamily: "var(--mono)", fontSize: "11px", fontWeight: 600, color: "var(--ink)" }}>{s.section}</p>
                      <p style={{ fontFamily: "var(--mono)", fontSize: "10px", color: "var(--ink-3)", marginTop: "4px" }}>relevance {s.relevance}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
