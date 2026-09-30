import * as React from 'react';
import * as T from '@radix-ui/react-tabs';
import { cn } from '../lib/cn';

export const Tabs = T.Root;
export const TabsContent = T.Content;
export function TabsList({ className, ...p }: React.ComponentProps<typeof T.List>) {
  return <T.List className={cn('flex gap-1 border-b border-border', className)} {...p} />;
}
export function TabsTrigger({ className, ...p }: React.ComponentProps<typeof T.Trigger>) {
  return (
    <T.Trigger
      className={cn(
        'min-h-(--size-tap-min) px-4 text-sm text-text-2 border-b-2 border-transparent -mb-px',
        'data-[state=active]:text-text data-[state=active]:border-text hover:text-text',
        'focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent',
        className,
      )}
      {...p}
    />
  );
}
