"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { Logo } from "@/components/Logo";
const links = [
  { href: "/consulting", label: "Consultancy" },
  { href: "/research", label: "Laboratory" },
  { href: "/products", label: "Ventures" },
  { href: "/writing", label: "Insights" },
  { href: "/fieldbooks", label: "Fieldbooks" },
];
export function Nav() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  useEffect(() => { setOpen(false); }, [pathname]);
  useEffect(() => {
    if (!open) return;
    const onEscape = (event: KeyboardEvent) => { if (event.key === "Escape") setOpen(false); };
    window.addEventListener("keydown", onEscape);
    return () => window.removeEventListener("keydown", onEscape);
  }, [open]);
  return (
    <header className="mi-header">
      <nav className="mi-nav mi-shell" aria-label="Main navigation">
        <Logo />
        <div className="mi-nav-links">
          {links.map(item => <Link key={item.href} className={pathname === item.href ? "mi-nav-link mi-nav-active" : "mi-nav-link"} href={item.href} aria-current={pathname === item.href ? "page" : undefined}>{item.label}</Link>)}
        </div>
        <div className="mi-nav-actions"><Link href="/contact" className="mi-nav-cta">Start a project <span aria-hidden="true">↗</span></Link>
          <button className="mi-menu-toggle" type="button" aria-label={open ? "Close navigation" : "Open navigation"} aria-expanded={open} aria-controls="mi-mobile-nav" onClick={() => setOpen(s => !s)}>{open ? "CLOSE ×" : "MENU ☰"}</button>
        </div>
      </nav>
      {open && <div id="mi-mobile-nav" className="mi-mobile-panel"><div className="mi-shell">
        {links.map(item => <Link href={item.href} key={item.href} onClick={() => setOpen(false)} aria-current={pathname === item.href ? "page" : undefined}>{item.label}<span aria-hidden="true">↗</span></Link>)}
        <Link href="/contact" onClick={() => setOpen(false)}>Start a project <span aria-hidden="true">↗</span></Link>
      </div></div>}
    </header>
  );
}
