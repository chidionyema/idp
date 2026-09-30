import * as React from 'react';
import { Prose, Display, Eyebrow } from '../components/Text';

export type DocsProps = {
  section?: string;
  title: string;
  nav: { title: string; links: { label: string; href: string; current?: boolean }[] }[];
  toc?: { label: string; href: string }[];
  body: React.ReactNode;
  updated?: string;
};

/** Three columns on desktop, one on a phone; the reading column is 68ch. */
export function Docs(p: DocsProps) {
  return (
    <div className="grid gap-8 desktop:grid-cols-[14rem_minmax(0,1fr)_12rem]">
      <nav aria-label="Docs" className="flex flex-col gap-6 text-sm">
        {p.nav.map((g) => (
          <div key={g.title} className="flex flex-col gap-1">
            <span className="font-mono text-xs uppercase tracking-wider text-text-2">{g.title}</span>
            {g.links.map((l) => <a key={l.href} href={l.href} aria-current={l.current ? 'page' : undefined} className={`inline-flex items-center min-h-(--size-tap-min) ${l.current ? 'text-text font-medium' : 'text-text-2 hover:text-text'}`}>{l.label}</a>)}
          </div>
        ))}
      </nav>
      <article className="flex flex-col gap-6 min-w-0">
        {p.section && <Eyebrow>{p.section}</Eyebrow>}
        <Display className="text-xl">{p.title}</Display>
        <Prose>{p.body}</Prose>
        {p.updated && <p className="font-mono text-xs text-text-2 border-t border-border pt-4">Updated {p.updated}</p>}
      </article>
      {p.toc && (
        <nav aria-label="On this page" className="hidden desktop:flex flex-col gap-1 text-sm sticky top-4 h-fit">
          <span className="font-mono text-xs uppercase tracking-wider text-text-2">On this page</span>
          {p.toc.map((t) => <a key={t.href} href={t.href} className="text-text-2 hover:text-text inline-flex items-center min-h-(--size-tap-min)">{t.label}</a>)}
        </nav>
      )}
    </div>
  );
}
