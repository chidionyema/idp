// The front page (crew#459 redesign, 2026-08-29). Founder: "where are all our components,
// tools, services?", "not running live cluster info", "all the tooling we use in our cluster
// is hidden away", "do you understand the concept of IDP and self-service platform".
//
// Reading order on a phone: one sentence (the worst word and its count), six counters that
// are filters, a find box, every layer the cluster runs grouped by system with its live Flux
// state and pods, every door the founder opens, and the actions the scaffolder offers.
// Nothing here names a layer, a door or a host: the catalogue is the list and the cluster is
// the state.
import { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Entity } from '@backstage/catalog-model';
import { Content, Link, LinkButton, Page } from '@backstage/core-components';
import { configApiRef, useApi } from '@backstage/frontend-plugin-api';
import {
  Button,
  TextField,
  Typography,
  makeStyles,
  useTheme,
} from '@material-ui/core';
import {
  STATE_ORDER,
  STATE_WORD,
  State,
  StateTint,
  ease,
  monoFamily,
  phone,
  stateDark,
  stateLight,
} from '../theme/tokens';
import {
  LayerState,
  ago,
  count,
  doorState,
  entityPath,
  layerState,
  matches,
  rank,
  systemOf,
  templatePath,
  verdict,
} from './estate';
import { Estate, useEstate } from './useEstate';

export {
  FOUNDER_SURFACE_TYPE,
  HEALTH_LABEL,
  STALE_AFTER_MS,
  healthOf,
  needsYou,
  templatePath,
} from './estate';
export type { Health } from './estate';

const useStyles = makeStyles(theme => ({
  wrap: { display: 'flex', flexDirection: 'column', gap: theme.spacing(3) },
  top: {
    display: 'flex',
    alignItems: 'baseline',
    justifyContent: 'space-between',
    gap: theme.spacing(2),
    flexWrap: 'wrap',
    paddingTop: theme.spacing(1),
  },
  brand: {
    fontSize: 13,
    fontWeight: 600,
    color: theme.palette.text.secondary,
    letterSpacing: '0.02em',
  },
  when: {
    fontSize: 12,
    color: theme.palette.text.disabled,
    fontVariantNumeric: 'tabular-nums',
  },
  verdict: {
    fontSize: 'clamp(26px, 6vw, 40px)',
    fontWeight: 600,
    letterSpacing: '-0.02em',
    lineHeight: 1.1,
    margin: 0,
  },
  counters: {
    display: 'grid',
    gridTemplateColumns: 'repeat(6, minmax(0, 1fr))',
    gap: theme.spacing(1),
    [phone]: { gridTemplateColumns: 'repeat(3, minmax(0, 1fr))' },
  },
  counter: {
    appearance: 'none',
    font: 'inherit',
    textAlign: 'left',
    cursor: 'pointer',
    borderRadius: 10,
    padding: theme.spacing(1.25, 1.5),
    border: `1px solid ${theme.palette.divider}`,
    background: theme.palette.background.paper,
    color: theme.palette.text.primary,
    display: 'flex',
    flexDirection: 'column',
    gap: 2,
    minHeight: 64,
    transition: `border-color 120ms ${ease}, background-color 120ms ${ease}`,
    '&:hover': { borderColor: theme.palette.text.disabled },
  },
  counterOn: {
    borderColor: theme.palette.primary.main,
    boxShadow: `inset 0 0 0 1px ${theme.palette.primary.main}`,
  },
  n: {
    fontSize: 24,
    fontWeight: 600,
    lineHeight: 1,
    fontVariantNumeric: 'tabular-nums',
    letterSpacing: '-0.02em',
  },
  word: {
    fontSize: 12,
    color: theme.palette.text.secondary,
    display: 'flex',
    alignItems: 'center',
    gap: 6,
  },
  find: {
    '& .MuiOutlinedInput-input': { fontSize: 16, padding: '12px 14px' },
  },
  section: {
    display: 'flex',
    flexDirection: 'column',
    gap: theme.spacing(1.5),
  },
  h: {
    display: 'flex',
    alignItems: 'baseline',
    justifyContent: 'space-between',
    gap: theme.spacing(2),
    margin: 0,
    fontSize: 15,
    fontWeight: 600,
  },
  hCount: {
    fontSize: 12,
    fontWeight: 500,
    color: theme.palette.text.secondary,
    fontVariantNumeric: 'tabular-nums',
  },
  hDesc: { fontSize: 13, color: theme.palette.text.secondary, margin: 0 },
  board: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 220px), 1fr))',
    gap: theme.spacing(1),
  },
  list: {
    display: 'grid',
    gridTemplateColumns: '1fr',
    gap: 4,
    '& $tile': {
      minHeight: 0,
      flexDirection: 'row',
      alignItems: 'center',
      flexWrap: 'wrap',
      gap: theme.spacing(1.5),
    },
    '& $tileTitle': { minWidth: 180 },
  },
  toolbar: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: theme.spacing(1),
    flexWrap: 'wrap',
  },
  hint: {
    fontSize: 12,
    color: theme.palette.text.secondary,
    '& kbd': {
      fontFamily: monoFamily,
      fontSize: 11,
      padding: '1px 5px',
      border: `1px solid ${theme.palette.divider}`,
      borderRadius: 4,
    },
  },
  views: { display: 'inline-flex', gap: 4 },
  view: {
    font: 'inherit',
    fontSize: 12,
    fontWeight: 600,
    padding: '4px 10px',
    borderRadius: 999,
    border: `1px solid ${theme.palette.divider}`,
    background: 'transparent',
    color: theme.palette.text.secondary,
    cursor: 'pointer',
    '&[aria-pressed="true"]': {
      color: theme.palette.text.primary,
      borderColor: theme.palette.text.primary,
    },
  },
  tile: {
    display: 'flex',
    flexDirection: 'column',
    gap: 6,
    minHeight: 84,
    padding: theme.spacing(1.25, 1.5),
    borderRadius: 10,
    border: `1px solid ${theme.palette.divider}`,
    background: theme.palette.background.paper,
    color: 'inherit',
    textDecoration: 'none',
    transition: `border-color 120ms ${ease}`,
    '&:hover': {
      borderColor: theme.palette.text.disabled,
      textDecoration: 'none',
    },
    minWidth: 0,
  },
  tileTitle: {
    fontSize: 14,
    fontWeight: 600,
    lineHeight: 1.25,
    overflowWrap: 'anywhere',
  },
  tileMeta: {
    fontSize: 12,
    color: theme.palette.text.secondary,
    display: 'flex',
    justifyContent: 'space-between',
    gap: 8,
    fontVariantNumeric: 'tabular-nums',
    marginTop: 'auto',
  },
  dot: {
    width: 8,
    height: 8,
    borderRadius: 999,
    flex: 'none',
    display: 'inline-block',
  },
  pill: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: 6,
    fontSize: 12,
    fontWeight: 600,
    lineHeight: 1,
    padding: '4px 8px',
    borderRadius: 999,
    border: '1px solid',
    alignSelf: 'flex-start',
    whiteSpace: 'nowrap',
  },
  row: {
    display: 'flex',
    alignItems: 'center',
    gap: theme.spacing(1.5),
    minHeight: 48,
    padding: theme.spacing(0.5, 0),
    borderBottom: `1px solid ${theme.palette.divider}`,
    flexWrap: 'wrap',
  },
  rowTitle: {
    flex: '1 1 12em',
    fontWeight: 500,
    minWidth: 0,
    overflowWrap: 'anywhere',
  },
  rowLinks: { display: 'flex', gap: theme.spacing(0.5), flexWrap: 'wrap' },
  door: {
    maxWidth: '100%',
    '& .MuiButton-label': { whiteSpace: 'normal', overflowWrap: 'anywhere' },
  },
  actions: { display: 'flex', flexWrap: 'wrap', gap: theme.spacing(1) },
  note: { fontSize: 13, color: theme.palette.text.secondary, margin: 0 },
  mono: { fontFamily: monoFamily, fontSize: 12, overflowWrap: 'anywhere' },
  card: {
    padding: theme.spacing(3),
    borderRadius: 12,
    border: `1px solid ${theme.palette.divider}`,
    background: theme.palette.background.paper,
    maxWidth: 560,
  },
  bone: {
    borderRadius: 10,
    background: theme.palette.action.hover,
    animation: '$pulse 1.4s ease-in-out infinite',
  },
  '@keyframes pulse': {
    '0%': { opacity: 1 },
    '50%': { opacity: 0.45 },
    '100%': { opacity: 1 },
  },
}));

const useTint = (): Record<State, StateTint> => {
  const theme = useTheme();
  return theme.palette.type === 'dark' ? stateDark : stateLight;
};

const Dot = ({ state }: { state: State }) => {
  const classes = useStyles();
  const tint = useTint()[state];
  return (
    <span
      className={classes.dot}
      aria-hidden="true"
      style={
        state === 'blind'
          ? { border: `2px solid ${tint.ink}`, background: 'transparent' }
          : { background: tint.ink }
      }
    />
  );
};

/** A dot and a word, never a colour alone. `blind` is a hollow ring. */
const Pill = ({
  state,
  why,
  testId,
}: {
  state: State;
  why?: string;
  testId?: string;
}) => {
  const classes = useStyles();
  const tint = useTint()[state];
  return (
    <span
      className={classes.pill}
      style={{ color: tint.ink, background: tint.bg, borderColor: tint.edge }}
      title={why}
      data-testid={testId}
      data-state={state}
    >
      <Dot state={state} />
      {STATE_WORD[state]}
    </span>
  );
};

const Counter = ({
  state,
  n,
  on,
  onClick,
}: {
  state: State;
  n: number;
  on: boolean;
  onClick: () => void;
}) => {
  const classes = useStyles();
  const tint = useTint()[state];
  return (
    <button
      type="button"
      className={`${classes.counter} ${on ? classes.counterOn : ''}`}
      onClick={onClick}
      aria-pressed={on}
      aria-label={`${n} ${STATE_WORD[state]}`}
      data-testid={`count-${state}`}
    >
      <span
        className={classes.n}
        style={{
          color: n > 0 && rank(state) < rank('running') ? tint.ink : undefined,
        }}
      >
        {n}
      </span>
      <span className={classes.word}>
        <Dot state={state} />
        {STATE_WORD[state]}
      </span>
    </button>
  );
};

const LayerTile = ({
  entity,
  s,
  now,
}: {
  entity: Entity;
  s: LayerState;
  now: number;
}) => {
  const age = ago(s.since, now);
  const classes = useStyles();
  return (
    <Link
      to={entityPath(entity)}
      underline="none"
      className={classes.tile}
      data-testid={`layer-${entity.metadata.name}`}
      data-state={s.state}
      title={entity.metadata.description}
    >
      <span className={classes.tileTitle}>
        {entity.metadata.title ?? entity.metadata.name}
      </span>
      <Pill state={s.state} why={s.why} />
      <span className={classes.tileMeta}>
        <span>{s.why}</span>
        {s.pods && (
          <span>
            {s.pods.ready}/{s.pods.wanted} pods
          </span>
        )}
        {age && <span data-testid={`age-${entity.metadata.name}`}>{age}</span>}
      </span>
    </Link>
  );
};

/** One line per door: state, name, and its links. Test ids are the login drill's contract. */
export const DoorRow = ({ entity, now }: { entity: Entity; now?: number }) => {
  const classes = useStyles();
  const s = doorState(entity, now);
  const links = entity.metadata.links ?? [];
  return (
    <div
      className={classes.row}
      data-testid={`surface-${entity.metadata.name}`}
      data-state={s.state}
    >
      <Pill
        state={s.state}
        why={s.why}
        testId={`health-${entity.metadata.name}`}
      />
      <Link
        to={entityPath(entity)}
        className={classes.rowTitle}
        title={entity.metadata.description}
      >
        {entity.metadata.title ?? entity.metadata.name}
      </Link>
      <div className={classes.rowLinks}>
        {links.map((link, i) => (
          <LinkButton
            key={link.url}
            to={link.url}
            color="primary"
            variant={i === 0 ? 'contained' : 'outlined'}
            size="small"
            className={classes.door}
          >
            {link.title ?? link.url}
          </LinkButton>
        ))}
      </div>
    </div>
  );
};

const Loading = () => {
  const classes = useStyles();
  const Bone = ({ height }: { height: number }) => (
    <div className={classes.bone} style={{ height }} aria-hidden="true" />
  );
  return (
    <div data-testid="loading" aria-busy="true" className={classes.wrap}>
      <Bone height={44} />
      <div className={classes.counters}>
        {STATE_ORDER.map(s => (
          <Bone key={s} height={64} />
        ))}
      </div>
      <Bone height={44} />
      <div className={classes.board}>
        {[0, 1, 2, 3].map(i => (
          <Bone key={i} height={84} />
        ))}
      </div>
    </div>
  );
};

const CatalogueUnavailable = ({
  error,
  retry,
}: {
  error: Error;
  retry: () => void;
}) => {
  const classes = useStyles();
  return (
    <div className={classes.card} role="alert" data-testid="catalogue-error">
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
      <details className={classes.mono}>
        <summary>What the service said</summary>
        {String(error?.message ?? error)}
      </details>
    </div>
  );
};

const clock = (t: number) =>
  new Date(t).toLocaleTimeString(undefined, {
    hour: '2-digit',
    minute: '2-digit',
  });

type View = 'board' | 'list';
const VIEW_KEY = 'estate.view';
const readView = (): View => {
  try {
    return window.localStorage.getItem(VIEW_KEY) === 'list' ? 'list' : 'board';
  } catch {
    return 'board';
  }
};

const Ready = ({ estate, brand }: { estate: Estate; brand: string }) => {
  const classes = useStyles();
  const navigate = useNavigate();
  const [query, setQuery] = useState('');
  const [only, setOnly] = useState<State | undefined>(undefined);
  const [view, setView] = useState<View>(readView);
  const findRef = useRef<HTMLInputElement>(null);
  useEffect(() => {
    findRef.current?.focus();
  }, []);
  // `/` or Cmd/Ctrl+K from anywhere on the page lands in the find box.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const typing = (e.target as HTMLElement | null)?.tagName;
      const inField = typing === 'INPUT' || typing === 'TEXTAREA';
      const cmdK = (e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k';
      if (cmdK || (e.key === '/' && !inField)) {
        e.preventDefault();
        findRef.current?.focus();
        findRef.current?.select();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);
  const pickView = (v: View) => {
    setView(v);
    try {
      window.localStorage.setItem(VIEW_KEY, v);
    } catch {
      /* a private window forgets; the page still works */
    }
  };

  const now = Date.now();
  const states = useMemo(() => {
    const m = new Map<string, LayerState>();
    for (const e of estate.layers)
      m.set(e.metadata.name, layerState(e, estate.live));
    for (const e of estate.doors) m.set(e.metadata.name, doorState(e, now));
    return m;
  }, [estate, now]);
  const stateOf = (e: Entity): LayerState => states.get(e.metadata.name)!;
  const all = [...estate.layers, ...estate.doors];
  const counts = count(all.map(e => stateOf(e).state));

  const keep = (e: Entity) => !only || stateOf(e).state === only;
  const layers = matches(query, estate.layers).filter(keep);
  const doors = matches(query, estate.doors)
    .filter(keep)
    .sort((a, b) => rank(stateOf(a).state) - rank(stateOf(b).state));
  const templates = matches(query, estate.templates);
  const systemTitle = (id: string) => {
    const s = estate.systems.find(x => x.metadata.name === id);
    return {
      title: s?.metadata.title ?? id,
      description: s?.metadata.description,
    };
  };
  const bySystem = new Map<string, Entity[]>();
  for (const e of layers)
    bySystem.set(systemOf(e), [...(bySystem.get(systemOf(e)) ?? []), e]);
  const systemsShown = [...bySystem.entries()].sort((a, b) => {
    const worst = (xs: Entity[]) =>
      Math.min(...xs.map(e => rank(stateOf(e).state)));
    return (
      worst(a[1]) - worst(b[1]) ||
      systemTitle(a[0]).title.localeCompare(systemTitle(b[0]).title)
    );
  });

  const open = () => {
    const first = [...layers, ...doors][0];
    if (templates[0] && !first) navigate(templatePath(templates[0]));
    else if (first?.metadata.links?.[0])
      window.location.assign(first.metadata.links[0].url);
    else if (first) navigate(entityPath(first));
  };

  return (
    <div className={classes.wrap}>
      <div className={classes.top}>
        <span className={classes.brand}>{brand}</span>
        <span className={classes.when} data-testid="read-at">
          {estate.live
            ? `Cluster read at ${clock(estate.live.readAt)}`
            : `Cluster not read: ${estate.liveError ?? 'unknown'}`}
        </span>
      </div>
      <h1 className={classes.verdict} data-testid="verdict">
        {verdict(counts, all.length)}
      </h1>
      <div
        className={classes.counters}
        role="group"
        aria-label="Filter by state"
      >
        {STATE_ORDER.map(s => (
          <Counter
            key={s}
            state={s}
            n={counts[s]}
            on={only === s}
            onClick={() => setOnly(only === s ? undefined : s)}
          />
        ))}
      </div>
      <TextField
        className={classes.find}
        fullWidth
        inputRef={findRef}
        variant="outlined"
        placeholder="Find a layer, a door or an action — Enter opens the first"
        value={query}
        onChange={e => setQuery(e.target.value)}
        onKeyDown={e => e.key === 'Enter' && open()}
        inputProps={{ 'data-testid': 'quick-find', 'aria-label': 'Find' }}
      />
      <div className={classes.toolbar}>
        <span className={classes.hint}>
          <kbd>/</kbd> or <kbd>⌘K</kbd> to find · Enter opens the first
        </span>
        <span className={classes.views} role="group" aria-label="Layout">
          {(['board', 'list'] as View[]).map(v => (
            <button
              key={v}
              type="button"
              className={classes.view}
              data-testid={`view-${v}`}
              aria-pressed={view === v}
              onClick={() => pickView(v)}
            >
              {v === 'board' ? 'Board' : 'List'}
            </button>
          ))}
        </span>
      </div>

      <section className={classes.section} data-testid="band-layers">
        <h2 className={classes.h}>
          What we run
          <span className={classes.hCount}>
            {layers.length === estate.layers.length
              ? `${estate.layers.length} layers`
              : `${layers.length} of ${estate.layers.length} layers`}
          </span>
        </h2>
        {estate.layers.length === 0 && (
          <p className={classes.note} data-testid="no-layers">
            No platform layers are registered. bin/catalog-platform writes them
            from the cluster's Flux list; nothing is typed here.
          </p>
        )}
        {systemsShown.map(([id, xs]) => {
          const s = systemTitle(id);
          return (
            <div
              key={id}
              className={classes.section}
              data-testid={`system-${id}`}
            >
              <h3 className={classes.h} style={{ fontSize: 13 }}>
                {s.title}
                <span className={classes.hCount}>{xs.length}</span>
              </h3>
              {s.description && (
                <p className={classes.hDesc}>{s.description}</p>
              )}
              <div
                className={view === 'list' ? classes.list : classes.board}
                data-view={view}
              >
                {[...xs]
                  .sort(
                    (a, b) =>
                      rank(stateOf(a).state) - rank(stateOf(b).state) ||
                      (a.metadata.title ?? a.metadata.name).localeCompare(
                        b.metadata.title ?? b.metadata.name,
                      ),
                  )
                  .map(e => (
                    <LayerTile
                      key={e.metadata.name}
                      entity={e}
                      s={stateOf(e)}
                      now={now}
                    />
                  ))}
              </div>
            </div>
          );
        })}
      </section>

      <section className={classes.section} data-testid="band-doors">
        <h2 className={classes.h}>
          Doors
          <span className={classes.hCount}>
            {doors.length === estate.doors.length
              ? `${estate.doors.length}`
              : `${doors.length} of ${estate.doors.length}`}
          </span>
        </h2>
        {estate.doors.length === 0 ? (
          <p className={classes.note} data-testid="no-surfaces">
            No doors are registered yet. A door is added to the catalogue, never
            typed here.
          </p>
        ) : (
          doors.map(e => <DoorRow key={e.metadata.name} entity={e} now={now} />)
        )}
      </section>

      {templates.length > 0 && (
        <section className={classes.section} data-testid="band-actions">
          <h2 className={classes.h}>
            Do
            <span className={classes.hCount}>{templates.length}</span>
          </h2>
          <div className={classes.actions}>
            {templates.map((t, i) => (
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
      )}
    </div>
  );
};

export const EstateHome = () => {
  const config = useApi(configApiRef);
  const brand = config.getOptionalString('app.title') ?? 'Estate';
  const { loaded, retry } = useEstate();
  return (
    <Page themeId="home">
      <Content>
        {loaded.state === 'loading' && <Loading />}
        {loaded.state === 'error' && (
          <CatalogueUnavailable error={loaded.error} retry={retry} />
        )}
        {loaded.state === 'ready' && <Ready estate={loaded} brand={brand} />}
      </Content>
    </Page>
  );
};
