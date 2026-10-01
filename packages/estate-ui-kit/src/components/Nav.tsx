import * as React from 'react';
import { cn } from '../lib/cn';

export type NavLink = { label: string; href: string; current?: boolean };

/** Brand, at most four quiet links, one action. Every link is a 44px target. */
export function SiteNav({ brand, links, action, className }: { brand: React.ReactNode; links: NavLink[]; action?: React.ReactNode; className?: string }) {
  return (
    <header className={cn('border-b border-border bg-canvas', className)}>
      <nav aria-label="Primary" className="mx-auto flex max-w-(--size-content) flex-wrap items-center gap-x-6 gap-y-2 px-(--size-gutter) min-h-(--space-16)">
        <a href="/" className="font-display text-lg font-bold text-text min-h-(--size-tap-min) inline-flex items-center mr-auto">{brand}</a>
        <ul className="flex flex-wrap items-center gap-x-2">
          {links.slice(0, 4).map((l) => (
            <li key={l.href}>
              <a
                href={l.href}
                aria-current={l.current ? 'page' : undefined}
                className={cn('inline-flex items-center min-h-(--size-tap-min) px-3 rounded-md text-sm text-text-2 hover:text-text hover:bg-surface-3', l.current && 'text-text font-medium')}
              >
                {l.label}
              </a>
            </li>
          ))}
        </ul>
        {action}
      </nav>
    </header>
  );
}

export function SiteFooter({ children, legal }: { children?: React.ReactNode; legal: React.ReactNode }) {
  return (
    <footer className="border-t border-border mt-16">
      <div className="mx-auto max-w-(--size-content) px-(--size-gutter) py-8 flex flex-col gap-4 text-sm text-text-2">
        {children}
        <p className="font-mono text-xs">{legal}</p>
      </div>
    </footer>
  );
}

/** Skip link + landmarks + single content column. Every template renders inside this. */
export function SiteShell({ nav, footer, children, wide }: { nav: React.ReactNode; footer: React.ReactNode; children: React.ReactNode; wide?: boolean }) {
  return (
    <div className="min-h-dvh flex flex-col bg-canvas text-text">
      <a href="#main" className="sr-only focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-50 focus:bg-surface-2 focus:px-4 focus:py-2 focus:rounded-md focus:outline-2 focus:outline-accent">Skip to content</a>
      {nav}
      <main id="main" className={cn('mx-auto w-full px-(--size-gutter) py-8 flex-1 flex flex-col gap-12', wide ? 'max-w-(--size-content)' : 'max-w-(--size-content)')}>{children}</main>
      {footer}
    </div>
  );
}
