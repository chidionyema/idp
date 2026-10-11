import type { ReactNode } from 'react';
import { Text } from '@backstage/ui';

// Leaf module: the small standing atoms of the estate pages, deliberately free of the
// EstatePage module graph (core-components, the router, analytics). Anything that renders
// a tile on a page that a test also imports -- the home strip, the gates panel -- imports
// from here, so a test never has to load the whole shell to draw one chip.

/** The measured sentence under the header: what is true right now, in one line. */
export function Summary({
  children,
  testId,
}: {
  children: ReactNode;
  testId?: string;
}) {
  return (
    <Text variant="body-large" data-testid={testId}>
      {children}
    </Text>
  );
}

/** A small standing label on a tile -- "Everyday", a date, a count. Never colour alone. */
export function Chip({ children, title }: { children: ReactNode; title?: string }) {
  return (
    <span className="estate-chip" title={title}>
      {children}
    </span>
  );
}
