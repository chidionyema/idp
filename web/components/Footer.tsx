import Link from "next/link";
import { site } from "@/content/site";
import { Logo } from "@/components/Logo";

export function Footer() {
  const year = new Date().getFullYear();
  return (
    <footer style={{ background: "var(--ink)", color: "rgba(255,255,255,0.85)", marginTop: "auto" }}>
      <div style={{ maxWidth: "1152px", margin: "0 auto", padding: "64px 24px 48px" }}>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: "48px" }}>
          <div style={{ gridColumn: "span 2", maxWidth: "280px" }}>
            <Logo tone="light" />
            <p style={{ marginTop: "12px", fontSize: "13px", lineHeight: 1.65, color: "rgba(255,255,255,0.65)", maxWidth: "none" }}>{site.tagline}</p>
            <a href="mailto:hello@meridian.ai" className="footer-link-muted" style={{ display: "inline-block", marginTop: "20px" }}>hello@meridian.ai</a>
          </div>
          <div>
            <p className="footer-heading">Work</p>
            <ul style={{ display: "flex", flexDirection: "column", gap: "10px", marginTop: "16px", listStyle: "none" }}>
              {site.nav.map((item) => <li key={item.href}><Link href={item.href} className="footer-link">{item.label}</Link></li>)}
            </ul>
          </div>
          <div>
            <p className="footer-heading">Tools</p>
            <ul style={{ display: "flex", flexDirection: "column", gap: "10px", marginTop: "16px", listStyle: "none" }}>
              {[{ href: "/demo", label: "LLM Playground" }, { href: "/tools/cost-calculator", label: "Cost Calculator" }, { href: "/tools/trace-explorer", label: "Trace Explorer" }].map((t) => <li key={t.href}><Link href={t.href} className="footer-link">{t.label}</Link></li>)}
            </ul>
          </div>
        </div>
      </div>
      <div style={{ borderTop: "1px solid rgba(255,255,255,0.06)" }}>
        <div style={{ maxWidth: "1152px", margin: "0 auto", padding: "20px 24px", display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "12px" }}>
          <p style={{ fontFamily: "var(--mono)", fontSize: "11px", color: "rgba(255,255,255,0.55)" }}>© {year} {site.name}</p>
          <p style={{ fontFamily: "var(--mono)", fontSize: "11px", color: "rgba(255,255,255,0.55)" }}>AI infrastructure consulting</p>
        </div>
      </div>
    </footer>
  );
}
