import Link from "next/link";
import { Logo } from "@/components/Logo";
export function Footer() {
  return <footer className="mi-footer"><div className="mi-shell">
    <div className="mi-footer-top"><div><Logo tone="light"/><p>Independent AI laboratory, technology consultancy and venture builder.</p></div>
      <div className="mi-footer-links"><div><span>EXPLORE</span><Link href="/consulting">Consultancy</Link><Link href="/research">Laboratory</Link><Link href="/products">Ventures</Link><Link href="/tooling">Tooling</Link></div><div><span>CONNECT</span><Link href="/contact">Start a conversation</Link><Link href="/writing">Insights</Link><Link href="/case-studies">Our approach</Link><Link href="/privacy">Privacy</Link></div></div>
    </div>
    <div className="mi-footer-giant" aria-hidden="true">MERIDIAN<span>⁎</span></div>
    <div className="mi-footer-legal"><span>Meridian Intelligence Limited</span><span>Registered in England and Wales no. 16486712</span><span>4th Floor, 14 Museum Place, Cardiff CF10 3BH</span></div>
    <div className="mi-footer-bottom"><span>© {new Date().getFullYear()} MERIDIAN INTELLIGENCE</span><span>RESEARCH / ENGINEER / BUILD</span><span>UNITED KINGDOM · GLOBAL AMBITION</span></div>
  </div></footer>;
}
