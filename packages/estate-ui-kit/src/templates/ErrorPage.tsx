import * as React from 'react';
import { Button } from '../components/Button';
import { Display, Lede, Eyebrow } from '../components/Text';

export type ErrorPageProps = { code: string; title: string; text: string; home?: { label: string; href: string }; requestId?: string };

/** Says what happened and what to do, in words; the code is mono and small. */
export function ErrorPage(p: ErrorPageProps) {
  return (
    <section className="flex flex-col gap-6 py-16 max-w-(--size-measure)">
      <Eyebrow>{p.code}</Eyebrow>
      <Display>{p.title}</Display>
      <Lede>{p.text}</Lede>
      <div><Button asChild><a href={p.home?.href ?? '/'}>{p.home?.label ?? 'Back to the start'}</a></Button></div>
      {p.requestId && <p className="font-mono text-xs text-text-2">Reference {p.requestId}</p>}
    </section>
  );
}
