import * as React from 'react';
import { Button } from '../components/Button';
import { Heading, Price } from '../components/Text';
import { Field, Input, Checkbox } from '../components/Field';

export type CheckoutProps = {
  item: { title: string; price: string };
  /** The payment element (Stripe Elements, etc.) is passed in; the template owns the form around it. */
  payment: React.ReactNode;
  facts: string[];
  consent?: { id: string; label: React.ReactNode };
  submit: { label: string; onSubmit?: (e: React.FormEvent<HTMLFormElement>) => void; pending?: boolean };
  error?: string;
};

/** Guest checkout, one column on a phone, one action. Nothing sells a second thing here. */
export function Checkout(p: CheckoutProps) {
  return (
    <form onSubmit={p.submit.onSubmit} className="grid gap-8 desktop:grid-cols-[1fr_minmax(0,20rem)] max-w-(--size-content)">
      <div className="flex flex-col gap-6 min-w-0">
        <Heading>Checkout</Heading>
        <Field id="email" label="Email" hint="Your receipt and download link go here. No account needed.">
          <Input type="email" name="email" autoComplete="email" required inputMode="email" />
        </Field>
        <section className="flex flex-col gap-2" aria-label="Payment">
          <span className="text-sm font-medium">Payment</span>
          <div className="rounded-md border border-border-strong bg-surface-2 p-4">{p.payment}</div>
        </section>
        {p.consent && <Checkbox id={p.consent.id} name={p.consent.id} label={p.consent.label} />}
        {p.error && <p role="alert" className="text-sm text-state-red-ink">{p.error}</p>}
        <Button type="submit" size="lg" disabled={p.submit.pending} aria-busy={p.submit.pending}>{p.submit.label}</Button>
      </div>
      <aside className="rounded-md border border-border bg-surface-1 p-6 flex flex-col gap-3 h-fit">
        <span className="font-mono text-xs uppercase tracking-wider text-text-2">Order</span>
        <p className="font-display font-bold text-lg">{p.item.title}</p>
        <Price amount={p.item.price} note="one-time" />
        <ul className="flex flex-col gap-1 text-sm text-text-2 border-t border-border pt-3">{p.facts.slice(0, 3).map((f) => <li key={f}>{f}</li>)}</ul>
      </aside>
    </form>
  );
}
