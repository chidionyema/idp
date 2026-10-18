"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { site } from "@/content/site";

export function Nav() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  return (
    <header style={{ position: "sticky", top: 0, zIndex: 50, borderBottom: "1px solid var(--rule)", background: "rgba(250,250,248,0.95)", backdropFilter: "blur(8px)" }}>
      <nav style={{ display: "flex", alignItems: "center", justifyContent: "space-between", maxWidth: "1152px", margin: "0 auto", padding: "16px 24px" }}>
        <Link href="/" style={{ fontFamily: "var(--mono)", fontSize: "14px", fontWeight: 500, letterSpacing: "-0.01em", color: "var(--ink)", textDecoration: "none" }}>
          Meridian<span style={{ color: "var(--accent)" }}>.</span>
        </Link>
        <ul style={{ display: "flex", alignItems: "center", gap: "32px", listStyle: "none" }} className="nav-links">
          {site.nav.map((item) => (
            <li key={item.href}>
              <Link href={item.href} className="nav-link" style={{ fontWeight: pathname === item.href ? 500 : 400, color: pathname === item.href ? "var(--accent)" : "var(--ink-3)" }}>
                {item.label}
              </Link>
            </li>
          ))}
          <li><Link href="/demo" className="nav-link" style={{ color: pathname === "/demo" ? "var(--accent)" : "var(--ink-3)", fontWeight: pathname === "/demo" ? 500 : 400 }}>Live Demo</Link></li>
          <li><Link href="/tools/cost-calculator" className="nav-link" style={{ color: pathname === "/tools/cost-calculator" ? "var(--accent)" : "var(--ink-3)", fontWeight: pathname === "/tools/cost-calculator" ? 500 : 400 }}>Cost Calculator</Link></li>
          <li><Link href="/tools/trace-explorer" className="nav-link" style={{ color: pathname === "/tools/trace-explorer" ? "var(--accent)" : "var(--ink-3)", fontWeight: pathname === "/tools/trace-explorer" ? 500 : 400 }}>Trace Explorer</Link></li>
          <li><Link href="/contact" className="btn-primary" style={{ padding: "8px 16px", fontSize: "12px" }}>Talk to us</Link></li>
        </ul>
        <button onClick={() => setOpen((o) => !o)} className="nav-mobile" style={{ background: "none", border: "none", cursor: "pointer", color: "var(--ink-3)" }} aria-label="Toggle menu">
          {open ? (
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none"><line x1="4" y1="4" x2="16" y2="16" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/><line x1="16" y1="4" x2="4" y2="16" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/></svg>
          ) : (
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none"><line x1="3" y1="6" x2="17" y2="6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/><line x1="3" y1="10" x2="17" y2="10" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/><line x1="3" y1="14" x2="17" y2="14" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/></svg>
          )}
        </button>
      </nav>
      {open && (
        <div style={{ borderTop: "1px solid var(--rule)", padding: "16px 24px" }} className="nav-mobile">
          <ul style={{ display: "flex", flexDirection: "column", gap: "16px", listStyle: "none" }}>
            {site.nav.map((item) => (
              <li key={item.href}><Link href={item.href} onClick={() => setOpen(false)} className="nav-link" style={{ color: pathname === item.href ? "var(--accent)" : "var(--ink-3)" }}>{item.label}</Link></li>
            ))}
            {[{ href: "/demo", label: "Live Demo" }, { href: "/tools/cost-calculator", label: "Cost Calculator" }, { href: "/tools/trace-explorer", label: "Trace Explorer" }].map((t) => (
              <li key={t.href}><Link href={t.href} onClick={() => setOpen(false)} className="nav-link" style={{ color: pathname === t.href ? "var(--accent)" : "var(--ink-3)" }}>{t.label}</Link></li>
            ))}
            <li><Link href="/contact" onClick={() => setOpen(false)} className="btn-primary" style={{ alignSelf: "flex-start", padding: "8px 16px", fontSize: "12px" }}>Talk to us</Link></li>
          </ul>
        </div>
      )}
    </header>
  );
}
