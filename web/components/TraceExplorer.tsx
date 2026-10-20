"use client";
import { useState } from "react";

interface Span { id: string; name: string; service: string; duration: number; status: "ok" | "error"; attrs: Record<string, string | number>; children?: Span[]; kind: "server" | "client" | "internal"; color: string; }
interface Trace { label: string; trace: Span; totalDuration: number }

const TRACES: Trace[] = [
  {
    label: "Complex multi-step query",
    totalDuration: 3240,
    trace: {
      id: "abc123", name: "agent.pipeline", service: "agentgateway", duration: 3240, status: "ok",
      attrs: { "user.id": "usr_8x92k", "request.total_tokens": 1233, "pipeline.steps": 4 },
      kind: "server", color: "#1A56DB",
      children: [
        { id: "d1", name: "intent.classify", service: "agentgateway", duration: 42, status: "ok", attrs: { "intent.label": "complex_reasoning", "intent.confidence": 0.94 }, kind: "internal", color: "#059669", children: [
          { id: "d1a", name: "llm.classify", service: "litellm-proxy", duration: 31, status: "ok", attrs: { "llm.model": "gpt-4o-mini", "llm.prompt_tokens": 38 }, kind: "client", color: "#7C3AED" }
        ] },
        { id: "d2", name: "model.inference", service: "litellm-proxy", duration: 1842, status: "ok", attrs: { "llm.model": "gpt-4o", "llm.total_tokens": 1233, "llm.cost_usd": 0.00417 }, kind: "client", color: "#7C3AED", children: [
          { id: "d2a", name: "upstream.openai", service: "openai", duration: 1802, status: "ok", attrs: { "http.status_code": 200 }, kind: "client", color: "#D97706" }
        ] },
        { id: "d3", name: "tool.vector_search", service: "agentgateway", duration: 187, status: "ok", attrs: { "tool.hits": 5, "tool.latency_ms": 187 }, kind: "client", color: "#059669", children: [
          { id: "d3a", name: "qdrant.search", service: "qdrant", duration: 142, status: "ok", attrs: { "db.system": "qdrant", "db.hits": 5 }, kind: "client", color: "#059669" }
        ] },
        { id: "d4", name: "tool.web_search", service: "agentgateway", duration: 891, status: "ok", attrs: { "tool.results": 8, "tool.latency_ms": 891 }, kind: "client", color: "#059669" },
        { id: "d5", name: "synthesis", service: "agentgateway", duration: 178, status: "ok", attrs: { "synthesis.sources": 3, "synthesis.latency_ms": 178 }, kind: "internal", color: "#1A56DB" }
      ]
    }
  },
  {
    label: "Simple classification (fast path)",
    totalDuration: 287,
    trace: {
      id: "xyz789", name: "agent.pipeline", service: "agentgateway", duration: 287, status: "ok",
      attrs: { "user.id": "usr_3m44p", "request.total_tokens": 32, "pipeline.steps": 2 },
      kind: "server", color: "#1A56DB",
      children: [
        { id: "z1", name: "intent.classify", service: "agentgateway", duration: 28, status: "ok", attrs: { "intent.label": "classification", "intent.confidence": 0.98 }, kind: "internal", color: "#059669", children: [
          { id: "z1a", name: "llm.classify", service: "litellm-proxy", duration: 19, status: "ok", attrs: { "llm.model": "gpt-4o-mini", "llm.prompt_tokens": 18 }, kind: "client", color: "#7C3AED" }
        ] },
        { id: "z2", name: "model.inference", service: "litellm-proxy", duration: 241, status: "ok", attrs: { "llm.model": "gpt-4o-mini", "llm.total_tokens": 32, "llm.cost_usd": 0.000008 }, kind: "client", color: "#7C3AED" }
      ]
    }
  }
];

function flattenSpans(span: Span, depth = 0): (Span & { depth: number })[] {
  return [{ ...span, depth }, ...(span.children ?? []).flatMap((c) => flattenSpans(c, depth + 1))];
}

function SpanRow({ span, maxDuration, depth, selected, onClick, onToggle }: { span: Span; maxDuration: number; depth: number; selected: boolean; onClick: () => void; onToggle: () => void }) {
  const hasChildren = (span.children?.length ?? 0) > 0;
  const widthPct = (span.duration / maxDuration) * 100;
  const kindBg: Record<string, string> = { server: "rgba(26,86,219,0.1)", client: "rgba(217,119,6,0.1)", internal: "rgba(138,138,131,0.1)" };
  return (
    <>
      <div onClick={onClick} style={{ display: "flex", alignItems: "center", gap: "8px", borderBottom: "1px solid rgba(226,226,220,0.5)", paddingTop: "8px", paddingBottom: "8px", paddingRight: "16px", cursor: "pointer", background: selected ? "rgba(26,86,219,0.03)" : "transparent", paddingLeft: `${depth * 24 + 16}px` }}>
        <button onClick={(e) => { e.stopPropagation(); onToggle(); }} style={{ width: "16px", fontSize: "10px", background: "none", border: "none", cursor: hasChildren ? "pointer" : "default", color: "var(--ink-3)", flexShrink: 0, padding: 0 }}>
          {hasChildren ? "▸" : ""}
        </button>
        <span style={{ width: "8px", height: "8px", borderRadius: "50%", background: span.color, flexShrink: 0 }} />
        <span style={{ width: "208px", fontFamily: "var(--mono)", fontSize: "11px", fontWeight: 500, color: span.status === "error" ? "#DC2626" : "var(--ink)", flexShrink: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{span.name}</span>
        <span style={{ width: "64px", fontFamily: "var(--mono)", fontSize: "10px", color: "var(--ink-3)", background: kindBg[span.kind] ?? "", padding: "2px 6px", borderRadius: "2px", flexShrink: 0, textAlign: "center" }}>{span.kind}</span>
        <div style={{ flex: 1, height: "12px", background: "var(--rule)", borderRadius: "2px", overflow: "hidden", position: "relative" }}>
          <div style={{ position: "absolute", left: 0, top: 0, height: "100%", width: `${Math.max(widthPct, 1)}%`, background: span.color + "25" }} />
          <div style={{ position: "absolute", left: 0, top: 0, height: "100%", width: `${Math.max(widthPct * 0.75, 1)}%`, background: span.color }} />
        </div>
        <span style={{ width: "64px", fontFamily: "var(--mono)", fontSize: "11px", fontWeight: 600, color: span.color, textAlign: "right", flexShrink: 0 }}>{span.duration}ms</span>
        <span style={{ width: "32px", fontFamily: "var(--mono)", fontSize: "11px", color: span.status === "ok" ? "var(--ok)" : "#DC2626", textAlign: "center", flexShrink: 0 }}>{span.status === "ok" ? "✓" : "✗"}</span>
      </div>
    </>
  );
}

export function TraceExplorer() {
  const [selectedTrace, setSelectedTrace] = useState(0);
  const [selectedSpanId, setSelectedSpanId] = useState<string | null>(null);
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set(["abc123", "xyz789", "d1", "d2", "d3", "d4", "z1"]));

  const { trace, totalDuration } = TRACES[selectedTrace];
  const flat = flattenSpans(trace);
  const selectedSpan = flat.find((s) => s.id === selectedSpanId) ?? null;

  function toggleExpand(id: string) {
    setExpandedIds((prev) => { const next = new Set(prev); if (next.has(id)) next.delete(id); else next.add(id); return next; });
  }

  function renderSpans(span: Span, depth: number): React.ReactNode {
    const visible = flat.filter((s) => s.id === span.id || (s.depth > depth && expandedIds.has(span.id)));
    return visible.map((s) => {
      const isRoot = s.id === span.id;
      if (!isRoot) return null;
      return (
        <div key={s.id}>
          <SpanRow span={s} maxDuration={totalDuration} depth={s.depth} selected={selectedSpanId === s.id}
            onClick={() => setSelectedSpanId(selectedSpanId === s.id ? null : s.id)}
            onToggle={() => toggleExpand(s.id)} />
          {(s.children ?? []).filter((c) => expandedIds.has(s.id)).map((child) => renderSpans(child, s.depth + 1))}
        </div>
      );
    });
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
      <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
        {TRACES.map((t, i) => (
          <button key={t.label} onClick={() => { setSelectedTrace(i); setSelectedSpanId(null); setExpandedIds(new Set(["abc123", "xyz789", "d1", "d2", "d3", "d4", "z1"])); }}
            style={{ padding: "8px 16px", border: `1px solid ${selectedTrace === i ? "var(--accent)" : "var(--rule)"}`, background: selectedTrace === i ? "rgba(14,110,98,0.06)" : "transparent", color: selectedTrace === i ? "var(--accent)" : "var(--ink-3)", fontFamily: "var(--mono)", fontSize: "11px", cursor: "pointer", fontWeight: selectedTrace === i ? 500 : 400 }}>
            {t.label}
          </button>
        ))}
      </div>
      <div style={{ display: "grid", gap: "24px", gridTemplateColumns: "2fr 1fr" }}>
        <div>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "8px" }}>
            <span style={{ fontFamily: "var(--mono)", fontSize: "11px", color: "var(--ink-3)" }}>Trace {trace.id} — {totalDuration}ms total</span>
            <span style={{ fontFamily: "var(--mono)", fontSize: "11px", color: "var(--ok)" }}>● ok</span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "8px", borderBottom: "1px solid rgba(226,226,220,0.5)", paddingBottom: "8px", marginBottom: "4px" }}>
            <span style={{ width: "16px" }} /><span style={{ width: "8px" }} /><span style={{ width: "208px", fontFamily: "var(--mono)", fontSize: "10px", color: "var(--ink-3)" }}>Span</span>
            <span style={{ width: "64px", fontFamily: "var(--mono)", fontSize: "10px", color: "var(--ink-3)" }}>Kind</span>
            <span style={{ flex: 1, fontFamily: "var(--mono)", fontSize: "10px", color: "var(--ink-3)" }}>Duration</span>
            <span style={{ width: "64px", fontFamily: "var(--mono)", fontSize: "10px", color: "var(--ink-3)", textAlign: "right" }}>ms</span>
            <span style={{ width: "32px", fontFamily: "var(--mono)", fontSize: "10px", color: "var(--ink-3)", textAlign: "center" }}>Status</span>
          </div>
          <div style={{ maxHeight: "420px", overflowY: "auto" }}>
            {renderSpans(trace, 0)}
          </div>
        </div>
        <div>
          {selectedSpan ? (
            <div style={{ border: "1px solid var(--rule)", background: "var(--white)", padding: "20px" }}>
              <p style={{ fontFamily: "var(--mono)", fontSize: "11px", color: "var(--ink-3)", textTransform: "uppercase", letterSpacing: "0.08em" }}>Selected span</p>
              <p style={{ fontFamily: "var(--mono)", fontSize: "13px", fontWeight: 600, color: selectedSpan.color, marginTop: "8px" }}>{selectedSpan.name}</p>
              <p style={{ fontFamily: "var(--mono)", fontSize: "11px", color: "var(--ink-3)", marginTop: "4px" }}>{selectedSpan.service}</p>
              <div style={{ display: "flex", flexDirection: "column", gap: "8px", marginTop: "24px" }}>
                {[{ label: "Duration", value: `${selectedSpan.duration}ms` }, { label: "Kind", value: selectedSpan.kind }, { label: "Status", value: selectedSpan.status, color: selectedSpan.status === "ok" ? "var(--ok)" : "#DC2626" }].map((r) => (
                  <div key={r.label} style={{ display: "flex", justifyContent: "space-between", fontFamily: "var(--mono)", fontSize: "11px" }}>
                    <span style={{ color: "var(--ink-3)" }}>{r.label}</span><span style={{ color: r.color ?? "var(--ink)", fontWeight: 500 }}>{r.value}</span>
                  </div>
                ))}
              </div>
              <div style={{ marginTop: "24px", paddingTop: "16px", borderTop: "1px solid var(--rule)" }}>
                <p style={{ fontFamily: "var(--mono)", fontSize: "11px", color: "var(--ink-3)", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "12px" }}>Attributes</p>
                <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                  {Object.entries(selectedSpan.attrs).map(([k, v]) => (
                    <div key={k} style={{ fontFamily: "var(--mono)", fontSize: "11px", paddingBottom: "8px", borderBottom: "1px solid rgba(226,226,220,0.5)" }}>
                      <span style={{ color: "var(--ink-3)" }}>{k}</span><br />
                      <span style={{ color: "var(--ink)" }}>{typeof v === "number" && k.includes("usd") ? `$${(v as number).toFixed(5)}` : String(v)}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div style={{ border: "1px solid var(--rule)", background: "var(--white)", padding: "20px" }}>
              <p style={{ fontFamily: "var(--mono)", fontSize: "11px", color: "var(--ink-3)", textTransform: "uppercase", letterSpacing: "0.08em" }}>Trace overview</p>
              <div style={{ display: "flex", flexDirection: "column", gap: "8px", marginTop: "16px" }}>
                {[{ label: "Trace ID", value: trace.id }, { label: "Total duration", value: `${totalDuration}ms`, color: "var(--accent)" }, { label: "Spans", value: String(flat.length) }, { label: "Status", value: "✓ ok", color: "var(--ok)" }].map((r) => (
                  <div key={r.label} style={{ display: "flex", justifyContent: "space-between", fontFamily: "var(--mono)", fontSize: "11px", paddingBottom: "8px", borderBottom: "1px solid rgba(226,226,220,0.5)" }}>
                    <span style={{ color: "var(--ink-3)" }}>{r.label}</span><span style={{ color: r.color ?? "var(--ink)", fontWeight: 500 }}>{r.value}</span>
                  </div>
                ))}
              </div>
              <div style={{ marginTop: "24px", paddingTop: "16px", borderTop: "1px solid var(--rule)" }}>
                <p style={{ fontFamily: "var(--mono)", fontSize: "11px", color: "var(--ink-3)", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "12px" }}>Click a span to inspect attributes</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
