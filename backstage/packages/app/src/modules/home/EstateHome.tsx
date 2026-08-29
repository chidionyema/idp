// The founder god view (crew#401) as the portal's front page (crew#459).
//
// Every card is a `founder-surface` entity read from the catalogue at render
// time. Nothing here names a hostname or a surface: the list is the catalogue,
// so the gate that refuses an unregistered surface (crew#401 CP3) keeps this
// page complete, and the catalogue-drift row (crew#401 CP4) keeps it honest.
import { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Entity } from '@backstage/catalog-model';
import {
  Content,
  ContentHeader,
  Header,
  HeaderLabel,
  InfoCard,
  Link,
  LinkButton,
  Page,
} from '@backstage/core-components';
import { configApiRef, useApi } from '@backstage/frontend-plugin-api';
import { catalogApiRef } from '@backstage/plugin-catalog-react';
import {
  Button,
  Chip,
  Grid,
  TextField,
  Typography,
  makeStyles,
} from '@material-ui/core';

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

const HEALTH_ORDER: Record<Health, number> = {
  down: 0,
  stale: 1,
  unchecked: 2,
  up: 3,
};

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
export const triage = (
  surfaces: Entity[],
  now: number = Date.now(),
): Entity[] =>
  [...surfaces].sort((a, b) => {
    const d = HEALTH_ORDER[healthOf(a, now)] - HEALTH_ORDER[healthOf(b, now)];
    if (d !== 0) return d;
    return (a.metadata.title ?? a.metadata.name).localeCompare(
      b.metadata.title ?? b.metadata.name,
    );
  });

export const needsYou = (h: Health) => h === 'down' || h === 'stale';

// crew#307 (founder, 2026-08-29: "do you really think the founder has time to be scrolling
// down looking for stuff", "group and categorise properly"): every door is one row under its
// group, the whole estate on one phone screen. The group is the `estate/group` annotation in
// backstage/founder/catalog-info.yaml; a door without one lands under "Other" so it is never hidden.
export const GROUP_ORDER = ['Watch', 'Run', 'Build', 'Companies', 'Other'];
export const groupOf = (entity: Entity): string =>
  (entity.metadata.annotations ?? {})['estate/group'] || 'Other';
export const grouped = (surfaces: Entity[]): [string, Entity[]][] => {
  const by = new Map<string, Entity[]>();
  for (const e of surfaces)
    by.set(groupOf(e), [...(by.get(groupOf(e)) ?? []), e]);
  const order = (g: string) =>
    GROUP_ORDER.includes(g) ? GROUP_ORDER.indexOf(g) : GROUP_ORDER.length;
  return [...by.entries()].sort(
    (a, b) => order(a[0]) - order(b[0]) || a[0].localeCompare(b[0]),
  );
};

// Founder, 2026-08-29: "i need to find things super fast not scroll". The first thing on the
// page is a box; typing narrows every door and every action to the ones that match, and Enter
// opens the first match. Actions are the scaffolder templates the catalogue holds (kind
// Template), so "Enable platform feature" is one word away from the front page and nothing here
// names a template by hand.
export const templatePath = (t: Entity): string =>
  `/create/templates/${t.metadata.namespace ?? 'default'}/${t.metadata.name}`;

const text = (e: Entity): string =>
  [
    e.metadata.title,
    e.metadata.name,
    e.metadata.description,
    groupOf(e),
    ...(e.metadata.tags ?? []),
  ]
    .filter(Boolean)
    .join(' ')
    .toLowerCase();

export const findMatches = (
  query: string,
  doors: Entity[],
  templates: Entity[],
): { doors: Entity[]; templates: Entity[] } => {
  const words = query.toLowerCase().split(/\s+/).filter(Boolean);
  if (words.length === 0) return { doors, templates };
  const hit = (e: Entity) => words.every(w => text(e).includes(w));
  return { doors: doors.filter(hit), templates: templates.filter(hit) };
};

export const byTitle = (a: Entity, b: Entity) =>
  (a.metadata.title ?? a.metadata.name).localeCompare(
    b.metadata.title ?? b.metadata.name,
  );

const useStyles = makeStyles(theme => ({
  card: {
    display: 'flex',
    flexDirection: 'column',
    height: '100%',
  },
  // The vendor grid track is 22em (352px): wider than a phone minus padding, so the
  // page scrolled sideways (audit 2026-08-29). min(100%, 22em) never exceeds the column.
  grid: {
    display: 'grid',
    gridGap: theme.spacing(2),
    gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 22em), 1fr))',
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
  // A door whose link has no title shows its URL; a nowrap button then widens the page.
  door: {
    maxWidth: '100%',
    '& .MuiButton-label': { whiteSpace: 'normal', overflowWrap: 'anywhere' },
  },
  count: {
    fontSize: 'clamp(28px, 9vw, 40px)',
    fontWeight: 700,
    lineHeight: 1,
    letterSpacing: '-0.02em',
  },
  countRed: {
    color: theme.palette.status.error,
  },
  totalCard: {
    display: 'block',
    padding: theme.spacing(2),
    minHeight: 96,
    borderRadius: 12,
    background: theme.palette.background.paper,
    boxShadow: theme.shadows[1],
    color: 'inherit',
    '&:hover': { boxShadow: theme.shadows[4] },
  },
  totalLabel: {
    display: 'block',
    marginTop: theme.spacing(0.5),
    lineHeight: 1.3,
    color: theme.palette.text.secondary,
  },
  pill: {
    alignSelf: 'flex-start',
    marginBottom: theme.spacing(1),
    fontWeight: 600,
    color: theme.palette.getContrastText(theme.palette.status.ok),
  },
  pillDown: {
    backgroundColor: theme.palette.status.error,
    color: theme.palette.getContrastText(theme.palette.status.error),
  },
  pillStale: {
    backgroundColor: theme.palette.status.warning,
    color: theme.palette.getContrastText(theme.palette.status.warning),
  },
  pillUnchecked: {
    backgroundColor: theme.palette.status.pending,
    color: theme.palette.getContrastText(theme.palette.status.pending),
  },
  pillUp: {
    backgroundColor: theme.palette.status.ok,
    color: theme.palette.getContrastText(theme.palette.status.ok),
  },
  band: {
    marginBottom: theme.spacing(3),
  },
  row: {
    display: 'flex',
    alignItems: 'center',
    gap: theme.spacing(1),
    padding: theme.spacing(1, 0),
    borderBottom: `1px solid ${theme.palette.divider}`,
    flexWrap: 'wrap',
  },
  rowTitle: {
    flex: '1 1 12em',
    fontWeight: 500,
    minWidth: 0,
    overflowWrap: 'anywhere',
  },
  rowLinks: {
    display: 'flex',
    gap: theme.spacing(0.5),
    flexWrap: 'wrap',
  },
  groupTitle: {
    marginTop: theme.spacing(2),
    marginBottom: theme.spacing(0.5),
    textTransform: 'uppercase',
    letterSpacing: '0.08em',
    fontSize: 12,
    color: theme.palette.text.secondary,
  },
  find: {
    marginBottom: theme.spacing(1),
    '& .MuiOutlinedInput-input': {
      fontSize: 18,
      padding: '14px 16px',
    },
  },
  hint: {
    marginBottom: theme.spacing(3),
    color: theme.palette.text.secondary,
  },
  actions: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: theme.spacing(1),
  },
  errorCard: {
    padding: theme.spacing(3),
    borderRadius: 12,
    background: theme.palette.background.paper,
    boxShadow: theme.shadows[1],
    maxWidth: 560,
  },
  errorDetail: {
    marginTop: theme.spacing(2),
    fontFamily: 'monospace',
    fontSize: 12,
    color: theme.palette.text.secondary,
    overflowWrap: 'anywhere',
  },
  bone: {
    borderRadius: 12,
    background: theme.palette.action.hover,
    animation: '$pulse 1.4s ease-in-out infinite',
  },
  '@keyframes pulse': {
    '0%': { opacity: 1 },
    '50%': { opacity: 0.45 },
    '100%': { opacity: 1 },
  },
  skeletonRow: {
    display: 'grid',
    gridGap: theme.spacing(2),
    gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 22em), 1fr))',
    marginTop: theme.spacing(2),
  },
}));

type Loaded =
  | { state: 'loading' }
  | { state: 'error'; error: Error }
  | { state: 'ready'; surfaces: Entity[]; templates: Entity[] };

const pillClass = (classes: ReturnType<typeof useStyles>, h: Health) =>
  ({
    down: classes.pillDown,
    stale: classes.pillStale,
    unchecked: classes.pillUnchecked,
    up: classes.pillUp,
  }[h]);

const entityPathOf = (entity: Entity) =>
  `/catalog/${
    entity.metadata.namespace ?? 'default'
  }/${entity.kind.toLowerCase()}/${entity.metadata.name}`;

const DoorLinks = ({ entity }: { entity: Entity }) => {
  const classes = useStyles();
  const links = entity.metadata.links ?? [];
  return (
    <div className={classes.links}>
      {links.map(link => (
        <LinkButton
          key={link.url}
          to={link.url}
          color="primary"
          variant={link === links[0] ? 'contained' : 'outlined'}
          size="small"
          className={classes.door}
        >
          {link.title ?? link.url}
        </LinkButton>
      ))}
    </div>
  );
};

/** One card per founder surface: its state in one word, title, what it is, and its doors. */
export const SurfaceCard = ({
  entity,
  now,
}: {
  entity: Entity;
  now?: number;
}) => {
  const classes = useStyles();
  const title = entity.metadata.title ?? entity.metadata.name;
  const health = healthOf(entity, now);
  // InfoCard drops unknown props, so the test id lives on a wrapper (audit 2026-08-29).
  return (
    <div data-testid={`surface-${entity.metadata.name}`}>
      <InfoCard
        title={title}
        variant="gridItem"
        className={classes.card}
        deepLink={{ title: 'Catalogue entry', link: entityPathOf(entity) }}
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
        <DoorLinks entity={entity} />
      </InfoCard>
    </div>
  );
};

/** One line per door: state, name, and its links. No description, nothing to scroll past. */
export const DoorRow = ({ entity, now }: { entity: Entity; now?: number }) => {
  const classes = useStyles();
  const title = entity.metadata.title ?? entity.metadata.name;
  const health = healthOf(entity, now);
  return (
    <div
      className={classes.row}
      data-testid={`surface-${entity.metadata.name}`}
    >
      <Chip
        size="small"
        label={HEALTH_LABEL[health]}
        className={`${classes.pill} ${pillClass(classes, health)}`}
        data-testid={`health-${entity.metadata.name}`}
        data-health={health}
      />
      <Link
        to={entityPathOf(entity)}
        className={classes.rowTitle}
        title={entity.metadata.description}
      >
        {title}
      </Link>
      <div className={classes.rowLinks}>
        <DoorLinks entity={entity} />
      </div>
    </div>
  );
};

/** A headline number. The whole tile is the tap target, not the digits (WCAG 2.5.8). */
const Total = ({
  label,
  value,
  to,
  red,
}: {
  label: string;
  value: number;
  to: string;
  red?: boolean;
}) => {
  const classes = useStyles();
  return (
    <Grid item xs={6} sm={6} md={3}>
      <Link
        to={to}
        underline="none"
        className={classes.totalCard}
        aria-label={`${value} ${label}`}
      >
        <Typography
          className={`${classes.count} ${
            red && value > 0 ? classes.countRed : ''
          }`}
          data-testid={`total-${label}`}
        >
          {value}
        </Typography>
        <Typography variant="body2" className={classes.totalLabel}>
          {label}
        </Typography>
      </Link>
    </Grid>
  );
};

/** The page's shape while the catalogue answers: same grid, no jump when it lands. */
const Loading = () => {
  const classes = useStyles();
  const Bone = ({ height }: { height: number }) => (
    <div className={classes.bone} style={{ height }} aria-hidden="true" />
  );
  return (
    <div data-testid="loading" aria-busy="true">
      <Bone height={52} />
      <Typography variant="body2" className={classes.hint}>
        Reading the catalogue…
      </Typography>
      <Grid container spacing={2}>
        {[0, 1].map(i => (
          <Grid item xs={6} key={i}>
            <Bone height={96} />
          </Grid>
        ))}
      </Grid>
      <div className={classes.skeletonRow}>
        {[0, 1, 2].map(i => (
          <Bone key={i} height={132} />
        ))}
      </div>
    </div>
  );
};

/** A human sentence, a way to try again, and the detail folded away for an engineer. */
const CatalogueUnavailable = ({
  error,
  retry,
}: {
  error: Error;
  retry: () => void;
}) => {
  const classes = useStyles();
  return (
    <div
      className={classes.errorCard}
      role="alert"
      data-testid="catalogue-error"
    >
      <Typography variant="h5" gutterBottom>
        The catalogue did not answer
      </Typography>
      <Typography variant="body1" gutterBottom>
        The portal is up; the catalogue service behind it did not reply. Nothing
        on this page is proof that anything else is down.
      </Typography>
      <Button variant="contained" color="primary" onClick={retry}>
        Try again
      </Button>
      <details className={classes.errorDetail}>
        <summary>What the service said</summary>
        {String(error?.message ?? error)}
      </details>
    </div>
  );
};

export const EstateHome = () => {
  const classes = useStyles();
  const catalogApi = useApi(catalogApiRef);
  const config = useApi(configApiRef);
  const title = config.getOptionalString('app.title') ?? 'Estate';
  const [loaded, setLoaded] = useState<Loaded>({ state: 'loading' });
  const [attempt, setAttempt] = useState(0);
  const [query, setQuery] = useState('');
  const navigate = useNavigate();
  // The box takes the keyboard as soon as the page has something to find; the founder
  // lands and types (2026-08-29: "i need to find things super fast not scroll").
  const findRef = useRef<HTMLInputElement>(null);
  useEffect(() => {
    if (loaded.state === 'ready') findRef.current?.focus();
  }, [loaded.state]);
  const retry = useCallback(() => {
    setLoaded({ state: 'loading' });
    setAttempt(a => a + 1);
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [surfaces, templates] = await Promise.all([
          catalogApi.getEntities({
            filter: { 'spec.type': FOUNDER_SURFACE_TYPE },
            fields: ['kind', 'metadata', 'spec.type'],
          }),
          catalogApi.getEntities({
            filter: { kind: 'Template' },
            fields: ['kind', 'metadata'],
          }),
        ]);
        if (!cancelled) {
          setLoaded({
            state: 'ready',
            surfaces: triage(surfaces.items),
            templates: [...templates.items].sort(byTitle),
          });
        }
      } catch (error) {
        if (!cancelled) setLoaded({ state: 'error', error: error as Error });
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [catalogApi, attempt]);

  const needsYouCount =
    loaded.state === 'ready'
      ? loaded.surfaces.filter(e => needsYou(healthOf(e))).length
      : undefined;

  return (
    <Page themeId="home">
      <Header
        title={title}
        subtitle="Every service, every door, and what needs you, on one screen"
      >
        <HeaderLabel
          label="Needs you"
          value={needsYouCount === undefined ? '—' : String(needsYouCount)}
        />
      </Header>
      <Content>
        {loaded.state === 'loading' && <Loading />}
        {loaded.state === 'error' && (
          <CatalogueUnavailable error={loaded.error} retry={retry} />
        )}
        {loaded.state === 'ready' && (
          <>
            <TextField
              className={classes.find}
              fullWidth
              inputRef={findRef}
              variant="outlined"
              placeholder="Find a door or an action"
              value={query}
              onChange={e => setQuery(e.target.value)}
              onKeyDown={e => {
                if (e.key !== 'Enter') return;
                const m = findMatches(query, loaded.surfaces, loaded.templates);
                if (m.templates[0]) navigate(templatePath(m.templates[0]));
                else if (m.doors[0]?.metadata.links?.[0])
                  window.location.assign(m.doors[0].metadata.links[0].url);
              }}
              inputProps={{ 'data-testid': 'quick-find', 'aria-label': 'Find' }}
            />
            <Typography variant="body2" className={classes.hint}>
              Type a word; Enter opens the first match.
            </Typography>
            {(() => {
              const m = findMatches(query, loaded.surfaces, loaded.templates);
              return m.templates.length > 0 ? (
                <section className={classes.band} data-testid="band-actions">
                  <ContentHeader title="Do" />
                  <div className={classes.actions}>
                    {m.templates.map((t, i) => (
                      <LinkButton
                        key={t.metadata.name}
                        to={templatePath(t)}
                        color="primary"
                        variant={i === 0 ? 'contained' : 'outlined'}
                        size="small"
                        title={t.metadata.description}
                        data-testid={`action-${t.metadata.name}`}
                      >
                        {t.metadata.title ?? t.metadata.name}
                      </LinkButton>
                    ))}
                  </div>
                </section>
              ) : null;
            })()}
            <Grid container spacing={2} className={classes.band}>
              <Total
                label="Needs you"
                value={needsYouCount ?? 0}
                to="/catalog?filters[kind]=component&filters[type]=founder-surface"
                red
              />
              <Total
                label="Doors"
                value={loaded.surfaces.length}
                to="/catalog?filters[kind]=component&filters[type]=founder-surface"
              />
            </Grid>
            {loaded.surfaces.length === 0 ? (
              <Typography data-testid="no-surfaces">
                No doors are registered yet. A door is added to the catalogue,
                never typed here.
              </Typography>
            ) : (
              <>
                {(() => {
                  const shown = findMatches(query, loaded.surfaces, []).doors;
                  const attention = query
                    ? []
                    : shown.filter(e => needsYou(healthOf(e)));
                  const rest = query
                    ? shown
                    : shown.filter(e => !needsYou(healthOf(e)));
                  return (
                    <>
                      {!query && (
                        <section
                          className={classes.band}
                          data-testid="band-needs-you"
                        >
                          <ContentHeader
                            title={
                              attention.length === 0
                                ? 'Nothing needs you'
                                : `Needs you (${attention.length})`
                            }
                          />
                          {attention.length > 0 && (
                            <div className={classes.grid}>
                              {attention.map(entity => (
                                <SurfaceCard
                                  key={entity.metadata.name}
                                  entity={entity}
                                />
                              ))}
                            </div>
                          )}
                        </section>
                      )}
                      <section
                        className={classes.band}
                        data-testid="band-doors"
                      >
                        <ContentHeader
                          title={
                            query
                              ? `Doors matching "${query}" (${rest.length})`
                              : `Every door (${loaded.surfaces.length})`
                          }
                        />
                        {grouped(rest).map(([group, doors]) => (
                          <div key={group} data-testid={`group-${group}`}>
                            <Typography
                              variant="h6"
                              className={classes.groupTitle}
                            >
                              {group}
                            </Typography>
                            {doors.map(entity => (
                              <DoorRow
                                key={entity.metadata.name}
                                entity={entity}
                              />
                            ))}
                          </div>
                        ))}
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
