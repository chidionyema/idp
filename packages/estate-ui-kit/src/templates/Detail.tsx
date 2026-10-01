import * as React from 'react';
import { Button } from '../components/Button';
import { Display, Eyebrow, Lede, Prose, Price } from '../components/Text';
import { StatePill, type State } from '../components/StatePill';

export type DetailProps = {
  eyebrow?: string;
  title: string;
  lede?: string;
  price: { amount: string; note?: string };
  /** Per-check verdicts, when the product has them. The strip and the panel count agree by construction (audit F7). */
  checks?: { label: string; state: State }[];
  /** When only a count is known ("7/8 checks cleared"), say that and show no per-check pill: an unverifiable pill is a claim. */
  checksSummary?: { cleared: number; total: number };
  /** Three short facts beside the price, at body size (audit F12, F15): guarantee, payment, operator. */
  facts: string[];
  /** A link, or the product's own buy control (a button wired to its checkout). */
  cta: { label: string; href: string } | React.ReactNode;
  sample?: { label: string; href: string };
  /** Rendered under the price inside the panel: a currency note, an error, a cart link. */
  panelExtra?: React.ReactNode;
  body: React.ReactNode;
  sources?: { label: string; href: string }[];
};

const isLink = (c: DetailProps['cta']): c is { label: string; href: string } => !!c && typeof c === 'object' && 'href' in (c as object);

/** The money page: one purchase action, the checks that passed, the sources you can open. */
export function Detail(p: DetailProps) {
  const checks = p.checks ?? [];
  const passed = p.checksSummary?.cleared ?? checks.filter((c) => c.state === 'good').length;
  const total = p.checksSummary?.total ?? checks.length;
  return (
    <div className="grid gap-8 desktop:grid-cols-[1fr_minmax(0,20rem)] desktop:items-start">
      <article className="flex flex-col gap-6 min-w-0">
        {p.eyebrow && <Eyebrow>{p.eyebrow}</Eyebrow>}
        <Display>{p.title}</Display>
        {p.lede && <Lede>{p.lede}</Lede>}
        {checks.length > 0 && (
          <ul className="flex flex-wrap gap-2" aria-label={`${passed} of ${total} checks passed`}>
            {checks.map((c) => <li key={c.label}><StatePill state={c.state} word={c.label} /></li>)}
          </ul>
        )}
        <Prose>{p.body}</Prose>
        {p.sources && (
          <section className="flex flex-col gap-2">
            <h2 className="font-display text-lg font-bold">Sources ({p.sources.length})</h2>
            <ol className="flex flex-col gap-1 font-mono text-sm">
              {p.sources.map((s) => <li key={s.href}><a href={s.href} className="inline-flex items-center min-h-(--size-tap-min) text-accent underline underline-offset-4 break-all">{s.label}</a></li>)}
            </ol>
          </section>
        )}
      </article>
      <aside className="rounded-md border border-border bg-surface-1 p-6 flex flex-col gap-4 desktop:sticky desktop:top-4">
        <Price amount={p.price.amount} note={p.price.note} className="text-xl" />
        {total > 0 && <p className="text-sm text-text-2">{passed} of {total} checks cleared</p>}
        {isLink(p.cta) ? <Button asChild size="lg" className="w-full"><a href={p.cta.href}>{p.cta.label}</a></Button> : p.cta}
        {p.panelExtra}
        {p.sample && <Button asChild variant="link"><a href={p.sample.href}>{p.sample.label}</a></Button>}
        <ul className="flex flex-col gap-2 text-sm text-text-2 border-t border-border pt-4">
          {p.facts.slice(0, 3).map((f) => <li key={f}>{f}</li>)}
        </ul>
      </aside>
    </div>
  );
}
