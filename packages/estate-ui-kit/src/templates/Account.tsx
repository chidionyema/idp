import * as React from 'react';
import { Button } from '../components/Button';
import { Heading } from '../components/Text';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '../components/Tabs';
import { Empty } from './Empty';

export type AccountProps = {
  name: string;
  email: string;
  orders: { id: string; title: string; date: string; href: string }[];
  signOut: { label: string; href: string };
};

export function Account(p: AccountProps) {
  return (
    <>
      <header className="flex flex-wrap items-baseline justify-between gap-4">
        <div><Heading>{p.name}</Heading><p className="text-sm text-text-2 font-mono">{p.email}</p></div>
        <Button asChild variant="secondary"><a href={p.signOut.href}>{p.signOut.label}</a></Button>
      </header>
      <Tabs defaultValue="orders">
        <TabsList><TabsTrigger value="orders">Orders</TabsTrigger><TabsTrigger value="details">Details</TabsTrigger></TabsList>
        <TabsContent value="orders" className="pt-6">
          {p.orders.length === 0 ? (
            <Empty title="No orders yet" text="Anything you buy appears here with its download." action={{ label: 'See the catalogue', href: '/catalogue' }} />
          ) : (
            <ul className="divide-y divide-border">
              {p.orders.map((o) => (
                <li key={o.id} className="flex flex-wrap items-center gap-4 py-3">
                  <span className="font-mono text-sm text-text-2">{o.date}</span>
                  <a href={o.href} className="font-medium text-text hover:text-accent min-h-(--size-tap-min) inline-flex items-center">{o.title}</a>
                  <span className="font-mono text-xs text-text-2 ml-auto">{o.id}</span>
                </li>
              ))}
            </ul>
          )}
        </TabsContent>
        <TabsContent value="details" className="pt-6 text-sm text-text-2">Signed in as {p.email}.</TabsContent>
      </Tabs>
    </>
  );
}
