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
import { Link, LinkButton } from '@backstage/core-components';
import { configApiRef, useApi } from '@backstage/frontend-plugin-api';
import { TextField, makeStyles, useTheme } from '@material-ui/core';
import { Button, Text } from '@backstage/ui';
import { EstatePage } from '../shell';
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
  Counts,
  ago,
  count,
  dominantState,
  doorState,  entityPath,
  hasNoAddress,
  isScreen,
  isKubernetes,
  hasNoScreen,
  layerState,
  screenUrl,
  matches,
  rank,
  systemOf,
  templatePath,
  verdict,
} from './estate';
import { Estate, useEstate } from './useEstate';
import {
  NO_ADDRESS_WORDS,
  NO_SCREEN_WORDS,
  OPEN_WORD,
  PAGE,
  SECTIONS,
  STATE_MEANING,
  everythingSentence,
  inventoryWord,
  verdictSentence,
} from './words';
import {
  SectionIcon,
  StateDonut,
  StateIcon,
  SystemBars,
  systemIcon,
} from './visuals';

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
  // The dominant state leader (directive 1): a full-width strip tinted by the worst present
  // state, read from across the room. Background/ink/edge come in as inline style from the
  // state tint; this class only sets the strip's layout and type scale.
  dominant: {
    display: 'flex',
    alignItems: 'center',
    gap: theme.spacing(1.5),
    flexWrap: 'wrap',
    border: `1px solid`,
    borderRadius: 14,
    padding: theme.spacing(2),
  },
  dominantWord: {
    fontSize: 'clamp(28px, 6vw, 44px)',
    fontWeight: 800,
    lineHeight: 1,
    letterSpacing: '-0.02em',
  },
  dominantText: {
    fontSize: 'clamp(15px, 2.4vw, 19px)',
    fontWeight: 500,
    lineHeight: 1.35,
    minWidth: 0,
    flex: '1 1 220px',
  },
  // The one-sentence role a band plays (directive 3): an eyebrow under the heading that says,
  // in the estate's plain voice, what kind of thing its members are. Screens, Kubernetes
  // tooling and the Sign-in pages each carry the same role line, so a reader sees the tag-split
  // as one kind of thing (pages you open) rather than three unrelated bands.
  hRole: {
    display: 'block',
    fontSize: 13,
    fontWeight: 600,
    letterSpacing: '0.02em',
    textTransform: 'uppercase',
    color: theme.palette.text.secondary,
  },
  // Directive 2: the "needs your hand" band, shown only when something is red or needs. A
  // soft warning-tinted callout distinct from a normal section so the actionable set is clearly
  // the page's first duty, not just another band.
  nowBand: {
    '&::before': { content: 'none' },
  },
  nowGrid: {
    display: 'flex',
    flexDirection: 'column',
    gap: theme.spacing(1),
  },
  nowRow: {
    display: 'flex',
    alignItems: 'center',
    gap: theme.spacing(1.5),
    padding: theme.spacing(1.25, 1.5),
    borderRadius: 10,
    border: `1px solid ${theme.palette.divider}`,
    background: theme.palette.background.paper,
    color: theme.palette.text.primary,
    textDecoration: 'none',
    '&:hover': { borderColor: theme.palette.primary.main },
  },
  nowName: { fontWeight: 600 },
  nowWhy: { color: theme.palette.text.secondary },
  // The verdict is a sentence, never a bare number beside a word. The title and the lead
  // above it are the shared page shell's (modules/shell), the same on every page.
  verdict: {
    fontSize: 'clamp(20px, 4vw, 26px)',
    fontWeight: 600,
    lineHeight: 1.25,
    margin: 0,
    display: 'flex',
    alignItems: 'center',
    gap: theme.spacing(1.5),
    flexWrap: 'wrap',
  },
  live: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: 6,
    fontSize: 13,
    fontWeight: 600,
    lineHeight: 1.3,
    padding: '6px 10px',
    borderRadius: 999,
    border: '1px solid',
    maxWidth: '100%',
    [phone]: { borderRadius: 12, alignItems: 'flex-start' },
  },
  picture: {
    display: 'grid',
    gridTemplateColumns: 'minmax(0, 1fr) minmax(0, 1.4fr)',
    gap: theme.spacing(3),
    alignItems: 'start',
    [phone]: { gridTemplateColumns: '1fr' },
  },
  counters: {
    display: 'grid',
    gridTemplateColumns: 'repeat(6, minmax(0, 1fr))',
    gap: theme.spacing(1),
    [phone]: { gridTemplateColumns: 'repeat(3, minmax(0, 1fr))' },
  },
  counter: {
    appearance: 'none',
    position: 'relative',
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
    gap: 4,
    minHeight: 96,
    transition: `border-color 120ms ${ease}, background-color 120ms ${ease}`,
    '&:hover': { borderColor: theme.palette.text.disabled },
  },
  counterOn: {
    borderColor: theme.palette.primary.main,
    boxShadow: `inset 0 0 0 1px ${theme.palette.primary.main}`,
  },
  counterIcon: { position: 'absolute', top: 10, right: 10, display: 'flex' },
  meaning: {
    fontSize: 12,
    lineHeight: 1.35,
    color: theme.palette.text.secondary,
  },
  n: {
    fontSize: 28,
    fontWeight: 700,
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
  // Screens: the six-to-eight things with a screen, in front of the reader, never below the fold.
  screens: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))',
    gap: theme.spacing(1.5),
  },
  screen: {
    display: 'flex',
    flexDirection: 'column',
    gap: theme.spacing(1),
    padding: theme.spacing(2),
    borderRadius: 12,
    border: `1px solid ${theme.palette.divider}`,
    background: theme.palette.background.paper,
    minHeight: 120,
  },
  screenOff: { opacity: 0.6, borderStyle: 'dashed' },
  screenHead: {
    display: 'flex',
    alignItems: 'center',
    gap: theme.spacing(1),
    fontSize: 15,
    fontWeight: 600,
  },
  screenIcon: { color: theme.palette.primary.main, display: 'flex' },
  screenWhy: {
    fontSize: 13,
    color: theme.palette.text.secondary,
    margin: 0,
    display: '-webkit-box',
    WebkitLineClamp: 4,
    WebkitBoxOrient: 'vertical',
    overflow: 'hidden',
    maxHeight: '5.8em',
    flex: 'none',
  },
  screenFoot: {
    display: 'flex',
    alignItems: 'center',
    gap: theme.spacing(1),
    flexWrap: 'wrap',
  },
  // Everything we hold: one chip per kind of thing, count and plain word, each a link to the list.
  inventory: { display: 'flex', flexWrap: 'wrap', gap: theme.spacing(1) },
  chip: {
    display: 'inline-flex',
    alignItems: 'baseline',
    gap: 6,
    padding: '6px 12px',
    borderRadius: 999,
    border: `1px solid ${theme.palette.divider}`,
    background: theme.palette.background.paper,
    fontSize: 14,
    color: theme.palette.text.primary,
    textDecoration: 'none',
    '&:hover': { borderColor: theme.palette.primary.main },
  },
  chipN: { fontWeight: 700, fontVariantNumeric: 'tabular-nums' },
  section: {
    display: 'flex',
    flexDirection: 'column',
    gap: theme.spacing(1.5),
  },
  // Section heading: 24px, 700, primary, with an icon. Group heading: 17px, 600. Their
  // descriptions: 14px, 400, secondary. Two of size, weight and colour always differ.
  h: {
    display: 'flex',
    alignItems: 'center',
    gap: theme.spacing(1),
    margin: 0,
    fontSize: 24,
    fontWeight: 700,
    letterSpacing: '-0.01em',
    lineHeight: 1.2,
    color: theme.palette.text.primary,
    '& svg': { fontSize: 24, color: theme.palette.text.secondary },
  },
  h3: {
    display: 'flex',
    alignItems: 'center',
    gap: theme.spacing(1),
    margin: 0,
    fontSize: 17,
    fontWeight: 600,
    lineHeight: 1.3,
    color: theme.palette.text.primary,
    '& svg': { fontSize: 18, color: theme.palette.text.secondary },
  },
  hCount: {
    fontSize: 13,
    fontWeight: 500,
    color: theme.palette.text.secondary,
    fontVariantNumeric: 'tabular-nums',
    marginLeft: 'auto',
  },
  hDesc: {
    fontSize: 14,
    lineHeight: 1.5,
    color: theme.palette.text.secondary,
    margin: 0,
    maxWidth: 680,
  },
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
export const Pill = ({
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
      aria-label={`${n} ${STATE_WORD[state]}. ${STATE_MEANING[state].long} ${STATE_MEANING[state].action}`}
      title={`${STATE_MEANING[state].long} ${STATE_MEANING[state].action}`}
      data-testid={`count-${state}`}
    >
      <span className={classes.counterIcon}>
        <StateIcon state={state} />
      </span>
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
      <span className={classes.meaning}>{STATE_MEANING[state].short}</span>
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
/** One screen: icon, name, one line, and Open or "No address yet" (crew#612 CP10/CP11). */
export const ScreenCard = ({
  entity,
  now,
}: {
  entity: Entity;
  now?: number;
}) => {
  const classes = useStyles();
  const tint = useTint().blind;
  const s = doorState(entity, now);
  const url = screenUrl(entity);
  const noScreen = hasNoScreen(entity);
  const off = noScreen || hasNoAddress(entity) || !url;
  const title = entity.metadata.title ?? entity.metadata.name;
  const Icon = systemIcon(`${entity.metadata.name} ${title}`);
  // Three different reasons a tile can be dark, and they are not the same thing: the entity
  // names no screen at all, it names one we have no address for, or it has a real state.
  let screenState: string;
  if (noScreen) {
    screenState = 'no-screen';
  } else if (off) {
    screenState = 'no-address';
  } else {
    screenState = s.state;
  }
  return (
    <div
      className={`${classes.screen} ${off ? classes.screenOff : ''}`}
      data-testid={`screen-${entity.metadata.name}`}
      data-state={screenState}
    >
      <div className={classes.screenHead}>
        <span className={classes.screenIcon}>
          <Icon aria-hidden="true" fontSize="small" />
        </span>
        <Link to={entityPath(entity)} title={entity.metadata.description}>
          {title}
        </Link>
      </div>
      <p className={classes.screenWhy} title={entity.metadata.description}>
        {entity.metadata.description}
      </p>
      <div className={classes.screenFoot}>
        {off ? (
          <span
            className={classes.pill}
            style={{
              color: tint.ink,
              background: tint.bg,
              borderColor: tint.edge,
            }}
            title={
              noScreen
                ? 'This tool runs in the background with no screen of its own; its manifest and its alerts are its word.'
                : 'This runs, but nothing on the network has an address for it yet.'
            }
            data-testid={`health-${entity.metadata.name}`}
            data-state="blind"
          >
            <Dot state="blind" />
            {noScreen ? NO_SCREEN_WORDS : NO_ADDRESS_WORDS}
          </span>
        ) : (
          <>
            <Pill
              state={s.state}
              why={s.why}
              testId={`health-${entity.metadata.name}`}
            />
            <LinkButton
              to={url!}
              color="primary"
              variant="contained"
              size="small"
              className={classes.door}
              data-testid={`open-${entity.metadata.name}`}
            >
              {OPEN_WORD}
            </LinkButton>
          </>
        )}
      </div>
    </div>
  );
};

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

const clock = (t: number) =>
  new Date(t).toLocaleTimeString(undefined, {
    hour: '2-digit',
    minute: '2-digit',
  });

/** Live or not, as a chip beside the verdict: a tint, an icon-dot and a sentence. */
const LiveChip = ({ estate }: { estate: Estate }) => {
  const classes = useStyles();
  const tint = useTint()[estate.live ? 'good' : 'red'];
  return (
    <span
      className={classes.live}
      style={{ color: tint.ink, background: tint.bg, borderColor: tint.edge }}
      data-testid="read-at"
      title={
        estate.live
          ? undefined
          : PAGE.notLiveDetail(estate.liveError ?? 'unknown')
      }
    >
      <Dot state={estate.live ? 'good' : 'red'} />
      {estate.live
        ? PAGE.liveLabel(clock(estate.live.readAt))
        : PAGE.notLivePlain}
    </span>
  );
};

/**
 * The dominant state leader (directive 1): the worst present state, said as the one word and
 * the verdict sentence in a full-width strip tinted by that state, above the verdict text. A
 * founder should read the estate's condition from across the room, not from a 17px sentence.
 * The strip is graded by its data-state/word, never colour-only (estate WCAG discipline), and
 * the visible text is the whole verdict sentence, so no bare number-with-word rule is broken.
 */
const DominantMark = ({
  counts,
  total,
}: {
  counts: Counts;
  total: number;
}) => {
  const classes = useStyles();
  const dominant = dominantState(counts);
  const tint = useTint()[dominant];
  return (
    <div
      className={classes.dominant}
      data-testid="dominant"
      data-state={dominant}
      role="status"
      aria-live="polite"
      aria-atomic="true"
      style={{
        color: tint.ink,
        background: tint.bg,
        borderColor: tint.edge,
      }}
    >
      <Dot state={dominant} />
      <span className={classes.dominantWord}>{STATE_WORD[dominant]}</span>
      <span className={classes.dominantText}>
        {total <= 0 ? verdict(counts, total) : verdictSentence(counts, total)}
      </span>
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
      <Text as="h2" variant="title-small" weight="bold">
        The catalogue did not answer
      </Text>
      <Text variant="body-medium">
        The portal is up; the catalogue service behind it did not reply. Nothing
        on this page is proof that anything else is down.
      </Text>
      <Button variant="primary" onPress={retry}>
        Try again
      </Button>
      <details className={classes.mono}>
        <summary>What the service said</summary>
        {String(error?.message ?? error)}
      </details>
    </div>
  );
};

type View = 'board' | 'list';
const VIEW_KEY = 'estate.view';
const readView = (): View => {
  try {
    return window.localStorage.getItem(VIEW_KEY) === 'list' ? 'list' : 'board';
  } catch {
    return 'board';
  }
};

const Ready = ({ estate }: { estate: Estate }) => {
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
  const byOpenable = (a: Entity, b: Entity) =>
    Number(hasNoAddress(a) || hasNoScreen(a)) -
      Number(hasNoAddress(b) || hasNoScreen(b)) ||
    rank(stateOf(a).state) - rank(stateOf(b).state) ||
    (a.metadata.title ?? a.metadata.name).localeCompare(
      b.metadata.title ?? b.metadata.name,
    );
  const allScreens = estate.doors.filter(e => isScreen(e) && !isKubernetes(e));
  const allKube = estate.doors.filter(isKubernetes);
  const kube = matches(query, allKube).filter(keep).sort(byOpenable);
  const screens = matches(query, allScreens)
    .filter(keep)
    .sort(
      (a, b) =>
        Number(hasNoAddress(a)) - Number(hasNoAddress(b)) ||
        rank(stateOf(a).state) - rank(stateOf(b).state) ||
        (a.metadata.title ?? a.metadata.name).localeCompare(
          b.metadata.title ?? b.metadata.name,
        ),
    );
  const doors = matches(
    query,
    estate.doors.filter(e => !isScreen(e) && !isKubernetes(e)),
  )
    .filter(keep)
    .sort((a, b) => rank(stateOf(a).state) - rank(stateOf(b).state));
  const held = estate.inventory.reduce((n, r) => n + r.count, 0);
  // Directive 2: what needs a person's hand, collected from everywhere and shown first, so a
  // red/needs item is never buried by kind in a band further down. Drawn from the same states
  // the page already computes (layers and doors) and mirrors the active find/filter, so typing
  // or picking a state narrows this band exactly as it narrows everywhere else; the rows carry
  // their own now-* test ids, so nothing reuses a tile id (no duplicate-getByTestId collisions).
  const nowList = [...estate.layers, ...estate.doors]
    .filter(e => matches(query, [e]).length > 0 && keep(e))
    .filter(e => {
      const st = stateOf(e).state;
      return st === 'red' || st === 'needs';
    })
    .sort(
      (a, b) =>
        rank(stateOf(a).state) - rank(stateOf(b).state) ||
        (a.metadata.title ?? a.metadata.name).localeCompare(
          b.metadata.title ?? b.metadata.name,
        ),
    );
  const listPath = (kind: string, type?: string) =>
    `/catalog?filters%5Bkind%5D=${encodeURIComponent(kind.toLowerCase())}${
      type ? `&filters%5Btype%5D=${encodeURIComponent(type)}` : ''
    }&filters%5Buser%5D=all`;
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
    const first = [...screens, ...layers, ...kube, ...doors][0];
    if (templates[0] && !first) navigate(templatePath(templates[0]));
    else if (first?.metadata.links?.[0])
      window.location.assign(first.metadata.links[0].url);
    else if (first) navigate(entityPath(first));
  };

  return (
    <div className={classes.wrap}>
      <DominantMark counts={counts} total={all.length} />
      <p
        className={classes.verdict}
        data-testid="verdict"
        title={verdict(counts, all.length)}
      >
        {/* The one sentence that answers the page. It changes when the poll returns and
            nothing announced it: this file had no aria-live region at all. */}
        <span role="status" aria-live="polite" aria-atomic="true">
          {verdictSentence(counts, all.length)}
        </span>
        <LiveChip estate={estate} />
      </p>
      <TextField
        className={classes.find}
        fullWidth
        inputRef={findRef}
        variant="outlined"
        placeholder="Find a service, a door or an action — Enter opens the first"
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

      {nowList.length > 0 && (
        <section
          className={`${classes.section} ${classes.nowBand}`}
          data-testid="band-now"
          aria-label="What needs your hand"
        >
          <h2 className={classes.h}>
            <span role="img" aria-label="hand">
              ✋
            </span>
            <span>What needs your hand</span>
            <span className={classes.hCount}>
              {nowList.length === 1 ? '1 thing' : `${nowList.length} things`}
            </span>
          </h2>
          <p className={classes.hDesc}>
            These are failing or waiting on a person right now, pulled together
            from everywhere so none are buried in a band further down.
          </p>
          <div className={classes.nowGrid}>
            {nowList.map(e => {
              const s = stateOf(e);
              return (
                <Link
                  key={e.metadata.name}
                  to={entityPath(e)}
                  underline="none"
                  className={classes.nowRow}
                  data-testid={`now-${e.metadata.name}`}
                  data-state={s.state}
                  title={e.metadata.description}
                >
                  <Pill state={s.state} why={s.why} />
                  <span className={classes.nowName}>
                    {e.metadata.title ?? e.metadata.name}
                  </span>
                  <span className={classes.nowWhy}>{s.why}</span>
                </Link>
              );
            })}
          </div>
        </section>
      )}

      <section className={classes.section} data-testid="band-everything">
        <h2 className={classes.h}>
          <SectionIcon section="everything" />
          {SECTIONS.everything.title}
          <span className={classes.hCount}>{everythingSentence(held)}</span>
        </h2>
        <p className={classes.hDesc}>{SECTIONS.everything.blurb}</p>
        <div className={classes.inventory} data-testid="inventory">
          {estate.inventory.map(r => (
            <Link
              key={`${r.kind}/${r.type ?? ''}`}
              to={listPath(r.kind, r.type)}
              className={classes.chip}
              data-testid={`held-${r.kind.toLowerCase()}-${r.type ?? 'all'}`}
            >
              <span className={classes.chipN}>{r.count}</span>
              <span>{inventoryWord(r.kind, r.type, r.count)}</span>
            </Link>
          ))}
        </div>
      </section>
      <section
        className={classes.section}
        id="screens"
        data-testid="band-screens"
      >
        <h2 className={classes.h}>
          <SectionIcon section="screens" />
          <span>{SECTIONS.screens.title}</span>
          {SECTIONS.screens.role && (
            <span className={classes.hRole} role="doc-subtitle">
              {SECTIONS.screens.role}
            </span>
          )}
          <span className={classes.hCount}>
            {screens.length === allScreens.length
              ? `${screens.length}`
              : `${screens.length} of ${allScreens.length}`}
          </span>
        </h2>
        <p className={classes.hDesc}>{SECTIONS.screens.blurb}</p>
        {allScreens.length === 0 ? (
          <p className={classes.note} data-testid="no-screens">
            No screens are registered yet.{' '}
            <Link to="/create">Create a component</Link> to add one.
          </p>
        ) : (
          <div className={classes.screens}>
            {screens.map(e => (
              <ScreenCard key={e.metadata.name} entity={e} now={now} />
            ))}
          </div>
        )}
      </section>
      <section
        className={classes.section}
        id="kubernetes"
        data-testid="band-kubernetes"
      >
        <h2 className={classes.h}>
          <SectionIcon section="kubernetes" />
          <span>{SECTIONS.kubernetes.title}</span>
          {SECTIONS.kubernetes.role && (
            <span className={classes.hRole} role="doc-subtitle">
              {SECTIONS.kubernetes.role}
            </span>
          )}
          <span className={classes.hCount}>
            {kube.length === allKube.length
              ? `${kube.length}`
              : `${kube.length} of ${allKube.length}`}
          </span>
        </h2>
        <p className={classes.hDesc}>{SECTIONS.kubernetes.blurb}</p>
        {allKube.length === 0 ? (
          <p className={classes.note} data-testid="no-kubernetes">
            No cluster tools are registered yet.
          </p>
        ) : (
          <div className={classes.screens}>
            {kube.map(e => (
              <ScreenCard key={e.metadata.name} entity={e} now={now} />
            ))}
          </div>
        )}
      </section>
      {all.length > 0 && (
        <div className={classes.picture} data-testid="picture">
          <StateDonut counts={counts} total={all.length} />
          <SystemBars
            rows={systemsShown.map(([id, xs]) => ({
              id,
              title: systemTitle(id).title,
              counts: count(xs.map(e => stateOf(e).state)),
            }))}
          />
        </div>
      )}
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
      <section className={classes.section} data-testid="band-layers">
        <h2 className={classes.h}>
          <SectionIcon section="layers" />
          {SECTIONS.layers.title}
          <span className={classes.hCount}>
            {layers.length === estate.layers.length
              ? `${estate.layers.length} services`
              : `${layers.length} of ${estate.layers.length} services`}
          </span>
        </h2>
        <p className={classes.hDesc}>{SECTIONS.layers.blurb}</p>
        {estate.layers.length === 0 && (
          <p className={classes.note} data-testid="no-layers">
            Nothing has been read from the machines yet, so there is nothing to
            list. The list fills itself the moment a read succeeds.
          </p>
        )}
        {systemsShown.map(([id, xs]) => {
          const s = systemTitle(id);
          const SysIcon = systemIcon(`${id} ${s.title}`);
          return (
            <div
              key={id}
              className={classes.section}
              data-testid={`system-${id}`}
            >
              <h3 className={classes.h3}>
                <SysIcon aria-hidden="true" />
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
          <SectionIcon section="doors" />
          <span>{SECTIONS.doors.title}</span>
          {SECTIONS.doors.role && (
            <span className={classes.hRole} role="doc-subtitle">
              {SECTIONS.doors.role}
            </span>
          )}
          <span className={classes.hCount}>
            {doors.length === estate.doors.length
              ? `${estate.doors.length}`
              : `${doors.length} of ${estate.doors.length}`}
          </span>
        </h2>
        <p className={classes.hDesc}>{SECTIONS.doors.blurb}</p>
        {estate.doors.length === 0 ? (
          <p className={classes.note} data-testid="no-surfaces">
            No sign-in pages yet. They appear here on their own once they are
            registered.
          </p>
        ) : (
          doors.map(e => <DoorRow key={e.metadata.name} entity={e} now={now} />)
        )}
      </section>

      {templates.length > 0 && (
        <section className={classes.section} data-testid="band-actions">
          <h2 className={classes.h}>
            <SectionIcon section="actions" />
            {SECTIONS.actions.title}
            <span className={classes.hCount}>{templates.length}</span>
          </h2>
          <p className={classes.hDesc}>{SECTIONS.actions.blurb}</p>
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
  // The nav links at /#screens and /#kubernetes changed the URL and moved nothing: no
  // scrollIntoView existed anywhere on this page. Focus moves too, so the section is announced
  // and not merely scrolled to.
  useEffect(() => {
    const handler = () => {
      const hash = window.location.hash;
      if (!hash) return;
      const el = document.getElementById(hash.slice(1));
      if (!el) return;
      const reduced =
        typeof window !== 'undefined' && window.matchMedia
          ? window.matchMedia('(prefers-reduced-motion: reduce)').matches
          : false;
      el.scrollIntoView({ block: 'start', behavior: reduced ? 'auto' : 'smooth' });
      el.tabIndex = -1;
      el.focus({ preventScroll: true });
    };
    const raf = requestAnimationFrame(handler);
    window.addEventListener('hashchange', handler);
    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener('hashchange', handler);
    };
  }, []);
  return (
    <EstatePage
      title={brand}
      lead={PAGE.tagline}
      actions={
        <Text variant="body-small" color="secondary">
          {new Date().toLocaleDateString(undefined, {
            weekday: 'long',
            day: 'numeric',
            month: 'long',
          })}
        </Text>
      }
    >
      {loaded.state === 'loading' && <Loading />}
      {loaded.state === 'error' && (
        <CatalogueUnavailable error={loaded.error} retry={retry} />
      )}
      {loaded.state === 'ready' && <Ready estate={loaded} />}
    </EstatePage>
  );
};
