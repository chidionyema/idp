// The founder god view (crew#401) as the portal's front page (crew#459).
//
// Every card is a `founder-surface` entity read from the catalogue at render
// time. Nothing here names a hostname or a surface: the list is the catalogue,
// so the gate that refuses an unregistered surface (crew#401 CP3) keeps this
// page complete, and the catalogue-drift row (crew#401 CP4) keeps it honest.
import { useEffect, useState } from 'react';
import { Entity } from '@backstage/catalog-model';
import {
  Content,
  ContentHeader,
  Header,
  HeaderLabel,
  InfoCard,
  ItemCardGrid,
  Link,
  LinkButton,
  Page,
  Progress,
  ResponseErrorPanel,
} from '@backstage/core-components';
import { configApiRef, useApi } from '@backstage/frontend-plugin-api';
import { catalogApiRef } from '@backstage/plugin-catalog-react';
import { Chip, Grid, Typography, makeStyles } from '@material-ui/core';

export const FOUNDER_SURFACE_TYPE = 'founder-surface';

// crew#612 CP3: the page answers "what is down, what needs me" before anything
// else, on a phone. Health comes from the catalogue: bin/catalog-gen probes the
// first door of every founder surface and stamps `estate/health` ("ok 200" or
// "FAIL ...") and `estate/health-checked-at`. A surface nobody has probed, or a
// probe older than STALE_AFTER_MS, is never shown green (silent green is the
// defect class): it says so in plain words.
export const STALE_AFTER_MS = 3 * 60 * 60 * 1000;

export type Health = 'down' | 'stale' | 'unchecked' | 'up';

export const HEALTH_LABEL: Record<Health, string> = {
  down: 'Down',
  stale: 'Not checked lately',
  unchecked: 'Not checked',
  up: 'Up',
};

const HEALTH_ORDER: Record<Health, number> = { down: 0, stale: 1, unchecked: 2, up: 3 };

export const healthOf = (entity: Entity, now: number = Date.now()): Health => {
  const ann = entity.metadata.annotations ?? {};
  const verdict = ann['estate/health'];
  if (!verdict) return 'unchecked';
  if (verdict.startsWith('FAIL')) return 'down';
  const at = Date.parse(ann['estate/health-checked-at'] ?? '');
  if (Number.isNaN(at) || now - at > STALE_AFTER_MS) return 'stale';
  return 'up';
};

/** Down and stale first, then unchecked, then up; ties by title. */
export const triage = (surfaces: Entity[], now: number = Date.now()): Entity[] =>
  [...surfaces].sort((a, b) => {
    const d = HEALTH_ORDER[healthOf(a, now)] - HEALTH_ORDER[healthOf(b, now)];
    if (d !== 0) return d;
    return (a.metadata.title ?? a.metadata.name).localeCompare(b.metadata.title ?? b.metadata.name);
  });

export const needsYou = (h: Health) => h === 'down' || h === 'stale';

const useStyles = makeStyles(theme => ({
  card: {
    display: 'flex',
    flexDirection: 'column',
    height: '100%',
  },
  description: {
    flex: 1,
    marginBottom: theme.spacing(2),
    display: '-webkit-box',
    WebkitLineClamp: 4,
    WebkitBoxOrient: 'vertical',
    overflow: 'hidden',
  },
  links: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: theme.spacing(1),
  },
  count: {
    fontSize: 40,
    fontWeight: 700,
    lineHeight: 1,
  },
  countRed: {
    color: theme.palette.status.error,
  },
  pill: {
    alignSelf: 'flex-start',
    marginBottom: theme.spacing(1),
    fontWeight: 600,
    color: '#ffffff',
  },
  pillDown: { backgroundColor: theme.palette.status.error },
  pillStale: { backgroundColor: theme.palette.status.warning },
  pillUnchecked: { backgroundColor: theme.palette.status.pending },
  pillUp: { backgroundColor: theme.palette.status.ok },
  band: {
    marginBottom: theme.spacing(3),
  },
}));

type Loaded =
  | { state: 'loading' }
  | { state: 'error'; error: Error }
  | { state: 'ready'; surfaces: Entity[]; totals: Record<string, number> };

const pillClass = (classes: ReturnType<typeof useStyles>, h: Health) =>
  ({ down: classes.pillDown, stale: classes.pillStale, unchecked: classes.pillUnchecked, up: classes.pillUp })[h];

/** One card per founder surface: its state in one word, title, what it is, and its doors. */
export const SurfaceCard = ({ entity, now }: { entity: Entity; now?: number }) => {
  const classes = useStyles();
  const title = entity.metadata.title ?? entity.metadata.name;
  const links = entity.metadata.links ?? [];
  const health = healthOf(entity, now);
  const entityPath = `/catalog/${entity.metadata.namespace ?? 'default'}/${entity.kind.toLowerCase()}/${entity.metadata.name}`;
  return (
    <InfoCard
      title={title}
      className={classes.card}
      deepLink={{ title: 'Catalogue entry', link: entityPath }}
      data-testid={`surface-${entity.metadata.name}`}
    >
      <Chip
        size="small"
        label={HEALTH_LABEL[health]}
        className={`${classes.pill} ${pillClass(classes, health)}`}
        data-testid={`health-${entity.metadata.name}`}
        data-health={health}
      />
      <Typography variant="body2" className={classes.description}>
        {entity.metadata.description}
      </Typography>
      <div className={classes.links}>
        {links.map(link => (
          <LinkButton
            key={link.url}
            to={link.url}
            color="primary"
            variant={link === links[0] ? 'contained' : 'outlined'}
            size="small"
          >
            {link.title ?? link.url}
          </LinkButton>
        ))}
      </div>
    </InfoCard>
  );
};

const Total = ({ label, value, to, red }: { label: string; value: number; to: string; red?: boolean }) => {
  const classes = useStyles();
  return (
    <Grid item xs={6} sm={3}>
      <InfoCard>
        <Link to={to} underline="none" color="inherit">
          <Typography className={`${classes.count} ${red && value > 0 ? classes.countRed : ''}`} data-testid={`total-${label}`}>
            {value}
          </Typography>
          <Typography variant="overline">{label}</Typography>
        </Link>
      </InfoCard>
    </Grid>
  );
};

export const EstateHome = () => {
  const classes = useStyles();
  const catalogApi = useApi(catalogApiRef);
  const config = useApi(configApiRef);
  const title = config.getOptionalString('app.title') ?? 'Estate';
  const [loaded, setLoaded] = useState<Loaded>({ state: 'loading' });

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [surfaces, all] = await Promise.all([
          catalogApi.getEntities({
            filter: { 'spec.type': FOUNDER_SURFACE_TYPE },
            fields: ['kind', 'metadata', 'spec.type'],
          }),
          catalogApi.getEntities({ fields: ['kind', 'metadata.name'] }),
        ]);
        const totals: Record<string, number> = {};
        for (const e of all.items) {
          totals[e.kind] = (totals[e.kind] ?? 0) + 1;
        }
        if (!cancelled) {
          setLoaded({
            state: 'ready',
            surfaces: triage(surfaces.items),
            totals,
          });
        }
      } catch (error) {
        if (!cancelled) setLoaded({ state: 'error', error: error as Error });
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [catalogApi]);

  return (
    <Page themeId="home">
      <Header title={title} subtitle="What is up, what is down, and what needs you">
        {loaded.state === 'ready' && (
          <HeaderLabel
            label="Needs you"
            value={String(loaded.surfaces.filter(e => needsYou(healthOf(e))).length)}
          />
        )}
      </Header>
      <Content>
        {loaded.state === 'loading' && <Progress />}
        {loaded.state === 'error' && <ResponseErrorPanel error={loaded.error} />}
        {loaded.state === 'ready' && (
          <>
            <Grid container spacing={2} style={{ marginBottom: 16 }}>
              <Total
                label="Needs you"
                value={loaded.surfaces.filter(e => needsYou(healthOf(e))).length}
                to="/catalog?filters[kind]=component&filters[type]=founder-surface&filters[tags]=unhealthy"
                red
              />
              <Total label="Doors" value={loaded.surfaces.length} to="/catalog?filters[kind]=component&filters[type]=founder-surface" />
              <Total label="Services" value={loaded.totals.Component ?? 0} to="/catalog?filters[kind]=component" />
              <Total label="Things they run on" value={loaded.totals.Resource ?? 0} to="/catalog?filters[kind]=resource" />
            </Grid>
            {loaded.surfaces.length === 0 ? (
              <Typography data-testid="no-surfaces">
                The catalogue holds no {FOUNDER_SURFACE_TYPE} entity yet.
              </Typography>
            ) : (
              <>
                {(() => {
                  const attention = loaded.surfaces.filter(e => needsYou(healthOf(e)));
                  const rest = loaded.surfaces.filter(e => !needsYou(healthOf(e)));
                  return (
                    <>
                      <section className={classes.band} data-testid="band-needs-you">
                        <ContentHeader title={attention.length === 0 ? 'Nothing needs you' : `Needs you (${attention.length})`} />
                        {attention.length > 0 && (
                          <ItemCardGrid>
                            {attention.map(entity => (
                              <SurfaceCard key={entity.metadata.name} entity={entity} />
                            ))}
                          </ItemCardGrid>
                        )}
                      </section>
                      <section className={classes.band} data-testid="band-doors">
                        <ContentHeader title="Every door" />
                        <ItemCardGrid>
                          {rest.map(entity => (
                            <SurfaceCard key={entity.metadata.name} entity={entity} />
                          ))}
                        </ItemCardGrid>
                      </section>
                    </>
                  );
                })()}
              </>
            )}
          </>
        )}
      </Content>
    </Page>
  );
};
