"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { site } from "@/content/site";
import { Logo } from "@/components/Logo";

export function Nav() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const links = site.nav.filter((item) => item.href !== "/contact");
  return (
    <header className="mi-site-header">
      <nav className="mi-site-nav" aria-label="Main navigation">
        <Logo />
        <ul className="mi-site-links">
          {links.map((item) => (
            <li key={item.href}><Link href={item.href} aria-current={pathname === item.href ? "page" : undefined}>{item.label}</Link></li>
          ))}
        </ul>
        <Link href="/contact" className="mi-site-contact">Start a conversation <span aria-hidden="true">↗</span></Link>
        <button type="button" className="mi-site-toggle" aria-label={open ? "Close navigation" : "Open navigation"} aria-expanded={open} aria-controls="mi-site-mobile-nav" onClick={() => setOpen((value) => !value)}>
          {open ? "Close" : "Menu"} <span aria-hidden="true">{open ? "×" : "+"}</span>
        </button>
      </nav>
      {open && (
        <nav id="mi-site-mobile-nav" className="mi-site-mobile" aria-label="Mobile navigation">
          {[...links, { href: "/contact", label: "Contact" }].map((item) => <Link key={item.href} href={item.href} onClick={() => setOpen(false)}>{item.label} <span aria-hidden="true">↗</span></Link>)}
        </nav>
      )}
    </header>
  );
}
