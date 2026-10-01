import * as React from 'react';
import { Card, CardTitle, CardBody, CardMeta } from '../components/Card';
import { Heading, Price } from '../components/Text';
import { Button } from '../components/Button';

export type CatalogueItem = { title: string; text: string; price?: string; meta: string[]; href: string };
export type CatalogueProps = {
  title: string;
  count: number;
  facets?: { name: string; options: { label: string; href: string; active?: boolean; count?: number }[] }[];
  sort?: { label: string; href: string; active?: boolean }[];
  items: CatalogueItem[];
  /** Pagination or "load more"; a catalogue page never exceeds the 6,000px height guard. */
  more?: { label: string; href: string };
};

/** The one catalogue route: facets, sort, the whole card is the link (audit F4, F16). */
export function Catalogue(p: CatalogueProps) {
  return (
    <>
      <header className="flex flex-wrap items-baseline justify-between gap-4">
        <h1 className="font-display text-xl font-bold text-text text-balance">{p.title}</h1>
        <span className="font-mono text-sm text-text-2">{p.count} total</span>
      </header>
      {(p.facets || p.sort) && (
        <div className="flex flex-col gap-3 border-y border-border py-4">
          {p.facets?.map((f) => (
            <div key={f.name} className="flex flex-wrap items-center gap-2">
              <span className="font-mono text-xs uppercase tracking-wider text-text-2 min-w-(--space-16)">{f.name}</span>
              {f.options.map((o) => (
                <a key={o.href} href={o.href} aria-current={o.active ? 'true' : undefined}
                  className={`inline-flex items-center min-h-(--size-tap-min) px-3 rounded-pill text-sm border ${o.active ? 'bg-text text-canvas border-text' : 'border-border-strong text-text-2 hover:text-text'}`}>
                  {o.label}{o.count != null && <span className="ml-2 font-mono text-xs opacity-80">{o.count}</span>}
                </a>
              ))}
            </div>
          ))}
          {p.sort && (
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-mono text-xs uppercase tracking-wider text-text-2 min-w-(--space-16)">Sort</span>
              {p.sort.map((s) => <a key={s.href} href={s.href} className={`inline-flex items-center min-h-(--size-tap-min) px-3 text-sm ${s.active ? 'text-text font-medium underline underline-offset-4' : 'text-text-2 hover:text-text'}`}>{s.label}</a>)}
            </div>
          )}
        </div>
      )}
      <ul className="grid gap-4 sm:grid-cols-2 desktop:grid-cols-3">
        {p.items.map((it) => (
          <li key={it.href}>
            <Card interactive className="h-full relative">
              <CardTitle><a href={it.href} className="after:absolute after:inset-0">{it.title}</a></CardTitle>
              <CardBody className="line-clamp-3">{it.text}</CardBody>
              <div className="mt-auto flex flex-wrap items-center justify-between gap-2">
                {it.price && <Price amount={it.price} />}
                <CardMeta>{it.meta.slice(0, 2).map((m) => <span key={m}>{m}</span>)}</CardMeta>
              </div>
            </Card>
          </li>
        ))}
      </ul>
      {p.more && <div className="flex justify-center"><Button asChild variant="secondary"><a href={p.more.href}>{p.more.label}</a></Button></div>}
    </>
  );
}
