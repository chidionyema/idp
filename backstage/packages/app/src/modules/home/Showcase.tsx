// /showcase (docs/specs/backstage-as-a-product.md CP1; founder 2026-09-05: "showcase needs to
// wow and impress"). The page a buyer's engineer opens first. Three things, none of them a link:
// the estate bar bin/estate-showcase graded, drawn from the state branch; every system's health
// drawn live from the cluster with the same donut and bars the god view uses; and what Otto does
// on the door today, one tile per LIVE line of the capability inventory, each with its receipt.
// The buyer sandbox button and its countdown are CP2 of the same spec.
import { useMemo } from 'react';
import { Entity } from '@backstage/catalog-model';
import { Text } from '@backstage/ui';
import { makeStyles } from '@material-ui/core';
import {
  Chip,
  EstatePage,
  Fact,
  Name,
  Section,
  Summary,
  Tile,
  Tiles,
  Unread,
  Waiting,
} from '../shell';
import { LayerState, ago, count, layerState, rank, systemOf, verdict } from './estate';
import { Estate, useEstate } from './useEstate';
import { useShowcase } from './useShowcase';
import { abilitiesSentence, barSentence } from './showcaseDocs';
import { StateDonut, SystemBars, donutSentence } from './visuals';

// Rules 8, 9 and 14 of DESIGN-RULES.md: spacing in theme units, related numbers grouped by
// proximity in one container, no border per number.
const useStyles = makeStyles(theme => ({
  picture: {
    display: 'flex',
    flexWrap: 'wrap',
    alignItems: 'center',
    gap: theme.spacing(4),
  },
  facts: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: theme.spacing(4),
  },
}));

export const TITLE = 'Showcase';
export const LEAD =
  'The whole estate on one page, read live: how it is graded, how every system is doing right now, and what Otto can do for you today.';

const Systems = ({ estate }: { estate: Estate }) => {
  const classes = useStyles();
  const states = useMemo(() => {
    const m = new Map<string, LayerState>();
    for (const e of estate.layers)
      m.set(e.metadata.name, layerState(e, estate.live));
    return m;
  }, [estate]);
  const stateOf = (e: Entity): LayerState => states.get(e.metadata.name)!;
  const counts = count(estate.layers.map(e => stateOf(e).state));
  const title = (id: string) =>
    estate.systems.find(x => x.metadata.name === id)?.metadata.title ?? id;
  const bySystem = new Map<string, Entity[]>();
  for (const e of estate.layers)
    bySystem.set(systemOf(e), [...(bySystem.get(systemOf(e)) ?? []), e]);
  const rows = [...bySystem.entries()]
    .sort(
      (a, b) =>
        Math.min(...a[1].map(e => rank(stateOf(e).state))) -
          Math.min(...b[1].map(e => rank(stateOf(e).state))) ||
        title(a[0]).localeCompare(title(b[0])),
    )
    .map(([id, xs]) => ({
      id,
      title: title(id),
      counts: count(xs.map(e => stateOf(e).state)),
    }));
  const readAt = estate.live ? ago(new Date(estate.live.readAt).toISOString(), Date.now()) : undefined;
  return (
    <>
      <Summary testId="showcase-systems-sentence">
        {verdict(counts, estate.layers.length)}{' '}
        {donutSentence(counts, estate.layers.length)}
        {estate.live
          ? `, read from the cluster ${readAt ?? 'just now'}.`
          : `. The cluster could not be read: ${estate.liveError ?? 'unknown'}.`}
      </Summary>
      {estate.layers.length > 0 && (
        <div className={classes.picture} data-testid="showcase-picture">
          <StateDonut counts={counts} total={estate.layers.length} />
          <SystemBars rows={rows} />
        </div>
      )}
    </>
  );
};

export const Showcase = () => {
  const classes = useStyles();
  const docs = useShowcase();
  const { loaded } = useEstate();
  const now = Date.now();
  const abilities = docs.state === 'ready' ? docs.abilities : [];
  return (
    <EstatePage title={TITLE} lead={LEAD}>
      <Section
        title="The estate, graded"
        blurb="Every catalogued thing against the buyer's-engineer bar, red rows first, regraded on the inventory clock."
        testId="showcase-bar"
      >
        {docs.state === 'loading' && (
          <Waiting testId="showcase-bar-loading">Reading the grade.</Waiting>
        )}
        {docs.state === 'ready' && docs.bar && (
          <>
            <Summary testId="showcase-bar-sentence">
              {barSentence(docs.bar)}
              {docs.bar.takenAt
                ? ` Inventory taken ${ago(docs.bar.takenAt, now) ?? docs.bar.takenAt}.`
                : ''}
            </Summary>
            <div className={classes.facts} data-testid="showcase-facts">
              <Fact label="Elite" value={docs.bar.entities.elite} testId="showcase-elite" />
              <Fact label="With a gap" value={docs.bar.entities.gap} testId="showcase-gap" />
              <Fact label="Blind" value={docs.bar.entities.blind} testId="showcase-blind" />
              <Fact
                label="Standards rows live"
                value={`${docs.bar.standards.live} of ${docs.bar.standards.total}`}
                testId="showcase-standards"
              />
            </div>
          </>
        )}
        {docs.state === 'ready' && !docs.bar && (
          <Unread testId="showcase-bar-error" detail={docs.barError}>
            The grade could not be read, so no number is claimed.
          </Unread>
        )}
      </Section>
      <Section
        title="Every system, live"
        blurb="Each platform layer's Flux state and pods, read from the cluster every minute while you watch."
        testId="showcase-systems"
      >
        {loaded.state === 'loading' && (
          <Waiting testId="showcase-systems-loading">Reading the catalogue and the cluster.</Waiting>
        )}
        {loaded.state === 'error' && (
          <Unread testId="showcase-systems-error" detail={loaded.error.message}>
            The catalogue could not be read, so no system is shown.
          </Unread>
        )}
        {loaded.state === 'ready' && <Systems estate={loaded} />}
      </Section>
      <Section
        title="What Otto does today"
        blurb="Each ability is on the door's live path right now, with the file that proves it."
        testId="showcase-otto"
      >
        {docs.state === 'loading' && (
          <Waiting testId="showcase-otto-loading">Reading the inventory.</Waiting>
        )}
        {docs.state === 'ready' && docs.abilitiesError && (
          <Unread testId="showcase-otto-error" detail={docs.abilitiesError}>
            The inventory could not be read, so no ability is claimed.
          </Unread>
        )}
        {docs.state === 'ready' && !docs.abilitiesError && (
          <Summary testId="showcase-otto-sentence">{abilitiesSentence(abilities)}</Summary>
        )}
        <Tiles testId="showcase-abilities">
          {abilities.map((a, i) => (
            <Tile
              key={`${a.sense}-${i}`}
              title={a.text}
              badge={<Chip>{a.sense}</Chip>}
              testId={`ability-${i}`}
              state="good"
            >
              {a.receipts.length > 0 && (
                <Text variant="body-small" color="secondary">
                  Proof:{' '}
                  {a.receipts.map((r, j) => (
                    <span key={r}>
                      {j > 0 ? ', ' : ''}
                      <Name>{r}</Name>
                    </span>
                  ))}
                </Text>
              )}
            </Tile>
          ))}
        </Tiles>
      </Section>
    </EstatePage>
  );
};
