// One page shell for every page this estate builds (crew#843).
//
// Before this, each page drew its own header, its own lead line, its own tile and its own
// grid, and each one drew them at slightly different sizes: the front page carried a
// Backstage UI header at a 16px lead, Ops carried the same header outside Content at a 17px
// lead, and Tools and Reports carried no header component at all, only an h1 in the body.
// Four pages, four page tops. That drift is what reads as unfinished, so the shell is the
// fix and every page imports it.
//
// The page top is written here rather than taken from Backstage UI's `Header`. Two reasons,
// both measured. `Header` is documented as a secondary header and renders its title as an
// h2, so a page built on it has no h1 and a screen reader is handed a document with no name.
// And it carries its own container, which is why the front page needed `.estate-today` to
// unpick that container's padding and why the Ops page, which did not have that class, sat
// at a different width to its own body (founder 2026-09-03, and again 2026-09-04). Writing
// the four elements the estate actually uses -- title, lead, actions, rule -- removes both
// problems and the workaround with them.
//
// Colour, radius and font here come from the --bui-* variables, which modules/theme/buiVars.ts
// fills from modules/theme/tokens.ts. No file below this one carries a colour.
import { useId } from 'react';
import type { ReactNode } from 'react';
import { Content, Link, Page } from '@backstage/core-components';
import { Card, CardBody, CardHeader, Flex, Text } from '@backstage/ui';

/** The page top: title, the one sentence that says what the page is for, and its actions. */
export function EstatePage({
  title,
  lead,
  actions,
  children,
}: {
  title: string;
  lead: string;
  actions?: ReactNode;
  children: ReactNode;
}) {
  return (
    <Page themeId="home">
      <Content>
        <div className="estate-page">
          <Flex direction="column" gap="5">
            <header className="estate-page-top">
              <div className="estate-page-titles">
                <Text as="h1" variant="title-large" weight="bold">
                  {title}
                </Text>
                <Text variant="body-large" color="secondary">
                  {lead}
                </Text>
              </div>
              {actions && <div className="estate-page-actions">{actions}</div>}
            </header>
            {children}
          </Flex>
        </div>
      </Content>
    </Page>
  );
}

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

/** A named block of the page. One heading, one optional line saying what it is for. */
export function Section({
  title,
  blurb,
  children,
  testId,
}: {
  title: string;
  blurb?: string;
  children: ReactNode;
  testId?: string;
}) {
  return (
    <section className="estate-section" data-testid={testId}>
      <Flex direction="column" gap="2">
        <Text as="h2" variant="title-medium" weight="bold">
          {title}
        </Text>
        {blurb && (
          <Text variant="body-medium" color="secondary">
            {blurb}
          </Text>
        )}
      </Flex>
      {children}
    </section>
  );
}

/** The tile grid. One column on a phone, as many as fit above it; every page uses this one. */
export function Tiles({
  children,
  testId,
}: {
  children: ReactNode;
  testId?: string;
}) {
  return (
    <div className="estate-tiles" data-testid={testId}>
      {children}
    </div>
  );
}

/** One tile. A badge and a title on the top row, then whatever the page puts in it. */
export function Tile({
  title,
  titleHref,
  onChoose,
  chosen,
  badge,
  aside,
  children,
  testId,
  state,
}: {
  title: string;
  titleHref?: string;
  /** Makes the whole tile the control that chooses it, for a page that picks one of many. */
  onChoose?: () => void;
  chosen?: boolean;
  badge?: ReactNode;
  aside?: ReactNode;
  children?: ReactNode;
  testId?: string;
  state?: string;
}) {
  // A tile that is not a control is an article named by its own heading, so a screen reader
  // can list the tiles on a page and say what each one is without reading all of it.
  const headingId = useId();
  const inside = (
    <>
      <CardHeader>
        <Flex align="center" gap="2" className="estate-tile-top">
          {badge}
          <Text as="h3" variant="title-small" weight="bold" id={headingId}>
            {titleHref ? <Link to={titleHref}>{title}</Link> : title}
          </Text>
          {aside}
        </Flex>
      </CardHeader>
      <CardBody>
        <Flex direction="column" gap="2">
          {children}
        </Flex>
      </CardBody>
    </>
  );

  // A tile that picks something is Backstage UI's own pressable card, whose accessible name
  // is the title alone. The page used to make the whole tile one hand-rolled button, so a
  // screen reader read the state, the title, the schedule and the summary as a single
  // control name.
  if (onChoose) {
    return (
      <Card
        className={chosen ? 'estate-tile estate-tile-chosen' : 'estate-tile'}
        onPress={onChoose}
        label={title}
        data-testid={testId}
        data-state={state}
      >
        {inside}
      </Card>
    );
  }

  return (
    <Card
      className="estate-tile"
      role="article"
      aria-labelledby={headingId}
      data-testid={testId}
      data-state={state}
    >
      {inside}
    </Card>
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

/** A group that starts folded. The arrow is drawn as text, so it is not colour alone. */
export function Fold({
  summary,
  children,
  testId,
}: {
  summary: ReactNode;
  children: ReactNode;
  testId?: string;
}) {
  return (
    <details className="estate-fold" data-testid={testId}>
      <summary className="estate-fold-summary">
        <span className="estate-fold-arrow" aria-hidden="true">
          &#9656;
        </span>
        {summary}
      </summary>
      <div className="estate-fold-body">{children}</div>
    </details>
  );
}

/** A label and its number on one line, which is most of what a tile says. */
export function Fact({
  label,
  value,
  testId,
}: {
  label: string;
  value: ReactNode;
  testId?: string;
}) {
  return (
    <div className="estate-fact" data-testid={testId}>
      <Text variant="body-medium" color="secondary">
        {label}
      </Text>
      <Text variant="body-medium" weight="bold">
        {value}
      </Text>
    </div>
  );
}

/** The detail under a fact: the names behind the number, never more than a list. */
export function Names({
  children,
  testId,
}: {
  children: ReactNode;
  testId?: string;
}) {
  return (
    <ul className="estate-names" data-testid={testId}>
      {children}
    </ul>
  );
}

/** A name of a thing in the estate -- a namespace, a pod, a Flux row. Set in the mono face. */
export function Name({ children }: { children: ReactNode }) {
  return <span className="estate-name">{children}</span>;
}

/** Waiting for an answer. Said the same way on every page, and announced to a screen reader. */
export function Waiting({
  children,
  testId,
}: {
  children: ReactNode;
  testId?: string;
}) {
  return (
    <p className="estate-state-line" role="status" data-testid={testId}>
      {children}
    </p>
  );
}

/**
 * A thing that could not be read. Never a zero and never a green: something nobody could check
 * is unknown, and the page says which thing and what the machine said (DESIGN-RULES 21-23).
 */
export function Unread({
  children,
  detail,
  testId,
}: {
  children: ReactNode;
  detail?: string;
  testId?: string;
}) {
  return (
    <p className="estate-state-line estate-unread" role="alert" data-testid={testId}>
      {children}
      {detail ? <> <Name>{detail}</Name></> : null}
    </p>
  );
}

/** A tile-shaped version of Unread, so a grid keeps its shape when one source is down. */
export function UnreadTile({
  children,
  detail,
  testId,
}: {
  children: ReactNode;
  detail?: string;
  testId?: string;
}) {
  return (
    <Card className="estate-tile" data-testid={testId}>
      <CardBody>
        <Unread detail={detail}>{children}</Unread>
      </CardBody>
    </Card>
  );
}

/** A table that scrolls sideways on a phone rather than squeezing its columns to nothing. */
export function Sheet({
  children,
  testId,
}: {
  children: ReactNode;
  testId?: string;
}) {
  return (
    <div className="estate-sheet">
      <table className="estate-table" data-testid={testId}>
        {children}
      </table>
    </div>
  );
}
