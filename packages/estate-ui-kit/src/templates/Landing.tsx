import * as React from 'react';
import { Button } from '../components/Button';
import { Display, Lede, Eyebrow } from '../components/Text';
import { LedgerFeed, type FeedRow } from '../components/Feed';
import { Card, CardTitle, CardBody, CardMeta } from '../components/Card';
import { VoiceButton } from '../voice/useEstateVoice';

export type LandingProps = {
  eyebrow?: string;
  headline: string;
  lede: string;
  /** Three short checkable facts under the lede (never counts repeated elsewhere on the page). */
  proof?: string[];
  cta: { label: string; href: string };
  secondary?: { label: string; href: string };
  /** The live ledger. Empty rows render "quiet since", never a placeholder. */
  feed?: { rows: FeedRow[]; quietSince?: string; title?: string };
  /** Up to six items on the featured; the catalogue is one route behind it (audit F4). */
  featured?: { title: string; items: { title: string; text: string; meta: string[]; href: string }[] };
  voice?: boolean | { onFinal: (t: string) => void };
};

/** One proposition, one proof line, one featured, one CTA. Everything else lives on its own page. */
export function Landing(p: LandingProps) {
  return (
    <>
      <section className="flex flex-col gap-6 pt-8">
        {p.eyebrow && <Eyebrow>{p.eyebrow}</Eyebrow>}
        <Display className="max-w-[24ch]">{p.headline}</Display>
        <Lede>{p.lede}</Lede>
        {p.proof && (
          <ul className="flex flex-wrap gap-x-6 gap-y-2 font-mono text-sm text-state-good-ink">
            {p.proof.map((x) => <li key={x} className="flex items-center gap-2"><span aria-hidden>✓</span>{x}</li>)}
          </ul>
        )}
        <div className="flex flex-wrap items-center gap-3">
          <Button asChild size="lg"><a href={p.cta.href} className="label-arrow">{p.cta.label} →</a></Button>
          {p.secondary && <Button asChild variant="link"><a href={p.secondary.href}>{p.secondary.label}</a></Button>}
          {p.voice && <VoiceButton onFinal={typeof p.voice === 'object' ? p.voice.onFinal : undefined} />}
        </div>
      </section>
      {p.feed && <LedgerFeed rows={p.feed.rows} quietSince={p.feed.quietSince} title={p.feed.title} />}
      {p.featured && (
        <section className="flex flex-col gap-4">
          <h2 className="font-display text-xl font-bold">{p.featured.title}</h2>
          <ul className="grid gap-4 sm:grid-cols-2 desktop:grid-cols-3">
            {p.featured.items.slice(0, 6).map((it) => (
              <li key={it.href}>
                <Card interactive className="relative h-full">
                  <CardTitle><a href={it.href} className="after:absolute after:inset-0">{it.title}</a></CardTitle>
                  <CardBody>{it.text}</CardBody>
                  <CardMeta>{it.meta.map((m) => <span key={m}>{m}</span>)}</CardMeta>
                </Card>
              </li>
            ))}
          </ul>
        </section>
      )}
    </>
  );
}
