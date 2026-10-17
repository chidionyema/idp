import { TraceExplorer } from "@/components/TraceExplorer";
import { Reveal } from "@/components/Reveal";
import type { Metadata } from "next";
export const metadata: Metadata = { title: "Trace Explorer", description: "Interactive trace visualization for agentic AI pipelines. Span trees, duration bars, and attribute inspection." };

export default function TraceExplorerPage() {
  return (
    <div className="container section">
      <Reveal><div style={{ marginBottom: "48px" }}>
        <span className="tag tag-accent" style={{ marginBottom: "16px", display: "inline-flex" }}>Tools</span>
        <h1>Trace Explorer</h1>
        <p style={{ marginTop: "16px", color: "var(--ink-3)", fontSize: "18px", maxWidth: "60ch" }}>Click any span to inspect its attributes. Duration bars show relative time across the pipeline so you can spot where latency is coming from.</p>
      </div></Reveal>
      <Reveal>
        <div style={{ border: "1px solid var(--rule)", background: "var(--white)", padding: "32px", marginBottom: "64px" }}>
          <TraceExplorer />
        </div>
      </Reveal>
      <div style={{ borderTop: "1px solid var(--rule)", paddingTop: "48px" }}>
        <Reveal><h2 style={{ marginBottom: "24px" }}>The observability stack</h2></Reveal>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "16px" }}>
          {[
            { name: "Langfuse", role: "LLM-native traces", desc: "Prompt/response pairs, token counts, cost attribution, evaluation scoring." },
            { name: "OpenTelemetry", role: "Infrastructure spans", desc: "Host, network, and database spans alongside LLM spans in a single trace." },
            { name: "ClickHouse", role: "Trace storage", desc: "Sub-second queries over billions of spans. p95 query latency under 800ms." },
            { name: "Grafana", role: "Dashboards", desc: "Cost per team, per model, per feature. Latency heatmaps and error rate alerts." },
          ].map((s) => (
            <Reveal key={s.name}>
              <div style={{ border: "1px solid var(--rule)", background: "var(--panel)", padding: "20px" }}>
                <p style={{ fontFamily: "var(--mono)", fontSize: "13px", fontWeight: 600, color: "var(--accent)", marginBottom: "4px" }}>{s.name}</p>
                <p style={{ fontFamily: "var(--mono)", fontSize: "10px", color: "var(--ink-3)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "8px" }}>{s.role}</p>
                <p style={{ fontFamily: "var(--mono)", fontSize: "12px", color: "var(--ink-3)", lineHeight: 1.6 }}>{s.desc}</p>
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </div>
  );
}
