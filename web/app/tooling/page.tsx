import Link from "next/link";
import { site } from "@/content/site";
import { Reveal } from "@/components/Reveal";
import type { Metadata } from "next";
export const metadata: Metadata = { title: "Tooling", description: "Open-source AI infrastructure tools: routing layer, eval harness, and workload identity integration." };

export default function ToolingPage() {
  return (
    <div className="container section">
      <Reveal><div style={{ marginBottom: "64px" }}>
        <span className="tag tag-accent" style={{ marginBottom: "16px", display: "inline-flex" }}>Open Source</span>
        <h1>Tooling</h1>
        <p style={{ marginTop: "16px", color: "var(--ink-3)", fontSize: "18px", maxWidth: "60ch" }}>The infrastructure we build for clients gets open-sourced. Everything here is production-tested.</p>
      </div></Reveal>
      <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
        {site.tooling.map((t) => (
          <Reveal key={t.name}>
            <div key={t.name} id={t.name} style={{ border: "1px solid var(--rule)", background: "var(--white)", padding: "32px", scrollMarginTop: "96px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "24px", flexWrap: "wrap" }}>
                <div style={{ display: "flex", flexDirection: "column", gap: "16px", flex: 1 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
                    <code style={{ fontFamily: "var(--mono)", fontSize: "18px", fontWeight: 500, color: "var(--accent)" }}>{t.name}</code>
                    <span className={`tag ${t.status === "stable" ? "tag-ok" : t.status === "beta" ? "tag-beta" : ""}`}>{t.status}</span>
                  </div>
                  <p style={{ fontSize: "15px", color: "var(--ink-3)", lineHeight: 1.75, maxWidth: "60ch" }}>{t.desc}</p>
                </div>
                <div style={{ display: "flex", gap: "8px", flexShrink: 0 }}>
                  <Link href="https://github.com/meridian-intelligence" className="btn-secondary" style={{ padding: "8px 16px", fontSize: "11px" }}>GitHub →</Link>
                  <Link href="/demo" className="btn-primary" style={{ padding: "8px 16px", fontSize: "11px" }}>Demo</Link>
                </div>
              </div>
            </div>
          </Reveal>
        ))}
      </div>
      <div style={{ marginTop: "64px", padding: "48px", border: "1px solid var(--rule)", background: "var(--panel)", textAlign: "center" }}>
        <h3 style={{ fontFamily: "var(--serif)", marginBottom: "16px" }}>Want a custom build?</h3>
        <p style={{ color: "var(--ink-3)", maxWidth: "none", margin: "0 auto 32px" }}>We also build proprietary infrastructure for clients who need something specific to their environment.</p>
        <Link href="/contact" className="btn-primary">Talk to us →</Link>
      </div>
    </div>
  );
}
