import Link from "next/link";
import { site } from "@/content/site";
import { Logo } from "@/components/Logo";

export function Footer() {
  return (
    <footer style={{ background: "var(--ink)", color: "#fff", marginTop: "auto" }}>
      <div className="container" style={{ maxWidth: 1248, paddingBlock: "65px 47px" }}>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(220px,1fr))", gap: 46 }}>
          <div style={{ maxWidth: 340 }}>
            <Logo tone="light" />
            <p style={{ color: "var(--on-ink)", marginTop: 18, fontSize: 14, lineHeight: 1.8 }}>{site.tagline}</p>
            <Link href="/contact" className="footer-link" style={{ display: "inline-flex", marginTop: 20 }}>Start a conversation →</Link>
          </div>
          <div>
            <p className="footer-heading">Company</p>
            <ul style={{ listStyle: "none", display: "grid", gap: 11, marginTop: 18 }}>
              {site.nav.map((item) => <li key={item.href}><Link href={item.href} className="footer-link">{item.label}</Link></li>)}
            </ul>
          </div>
          <div>
            <p className="footer-heading">Engineering references</p>
            <ul style={{ listStyle: "none", display: "grid", gap: 11, marginTop: 18 }}>
              <li><Link href="/demo" className="footer-link">Routing simulation</Link></li>
              <li><Link href="/tools/trace-explorer" className="footer-link">Trace explorer</Link></li>
              <li><Link href="/tooling" className="footer-link">Reference tooling</Link></li>
            </ul>
          </div>
        </div>
      </div>
      <div style={{ borderTop: "1px solid rgba(255,255,255,.1)" }}>
        <div className="container" style={{ maxWidth: 1248, paddingBlock: 22, display: "flex", flexWrap: "wrap", justifyContent: "space-between", gap: 12 }}>
          <span style={{ font: "400 11px/1.5 var(--mono)", color: "var(--on-ink-muted)" }}>© {new Date().getFullYear()} Meridian Intelligence</span>
          <span style={{ font: "400 11px/1.5 var(--mono)", color: "var(--on-ink-muted)" }}>AI systems engineering · Delivery with evidence</span>
        </div>
      </div>
    </footer>
  );
}
