// The Tools page: every door the founder opens, on one page, grouped (crew#684 CP0).
// Founder, 2026-08-30: "i am founder, i am CEO and i am also engineer ... so i need all the
// tools one place ... another page in backstage just pure tools". Founder, 2026-09-02, on the
// 49-tile page: "that page is not intuitive at all, I don't know what I'm looking at ... this is
// supposed to be used by a human admin ... it needs to be clear what's going on, it's not a maze".
//
// So the page reads in five seconds: one headline, one lead line, one sentence of counts; then
// each group as a heading with one line saying what it is for; then one tile per tool with its
// state, its name, one plain sentence and one Open button. Everyday tools sit first in their
// group; plumbing is folded closed at the bottom. Nothing here names a tool; the catalogue is
// the list (LAW 46) and toolGroups.ts owns every word of copy.
import { Entity } from '@backstage/catalog-model';
import { Content, Link, LinkButton, Page } from '@backstage/core-components';
import { Typography, makeStyles } from '@material-ui/core';
import { doorState, entityPath } from './estate';
import { useDoors } from './useDoors';
import {
  GROUP_BLURB,
  HEADLINE,
  LEAD,
  ToolGroup,
  groupTools,
  isDaily,
  moreLinks,
  openLink,
  toolsSentence,
} from './toolGroups';
import { Pill } from './EstateHome';
import { monoFamily, phone } from '../theme/tokens';

/** The page's short name for menus and tabs; the h1 on the page itself is HEADLINE. */
export const TITLE = 'Tools';

export const EVERYDAY_WORD = 'Everyday';
export const OPEN_WORD = 'Open';
export const ALSO_WORD = 'Also:';
export const NO_LINK_SENTENCE = 'No link is published for this tool yet.';
export const LOADING_SENTENCE = 'Reading the catalogue.';
export const ERROR_SENTENCE =
  'The catalogue did not answer, so nothing can be listed.';

const useStyles = makeStyles(theme => ({
  // Scale per DESIGN-RULES.md: h1 40/700, lead 16/400 secondary, h2 24/700, blurb 14/400
  // secondary, tile title 15/600, sentence 14/400 secondary, small print 12/500 secondary.
  header: { marginBottom: theme.spacing(4), maxWidth: 720 },
  lead: {
    fontSize: 16,
    lineHeight: 1.5,
    color: theme.palette.text.secondary,
    margin: theme.spacing(1, 0, 0),
  },
  sentence: { fontSize: 16, lineHeight: 1.5, margin: theme.spacing(1, 0, 0) },
  group: { marginBottom: theme.spacing(5) },
  groupHead: { marginBottom: theme.spacing(2), maxWidth: 720 },
  groupTitle: {
    fontSize: 24,
    fontWeight: 700,
    lineHeight: 1.2,
    margin: 0,
    [phone]: { fontSize: 20 },
  },
  groupCount: {
    fontSize: 16,
    fontWeight: 400,
    color: theme.palette.text.secondary,
    marginLeft: theme.spacing(1),
    whiteSpace: 'nowrap',
  },
  blurb: {
    fontSize: 14,
    lineHeight: 1.5,
    color: theme.palette.text.secondary,
    margin: theme.spacing(0.5, 0, 0),
  },
  summary: {
    cursor: 'pointer',
    listStyle: 'none',
    padding: theme.spacing(1, 0),
    '&::-webkit-details-marker': { display: 'none' },
    '&:focus-visible': {
      outline: `2px solid ${theme.palette.primary.main}`,
      outlineOffset: 2,
    },
  },
  // The fold's own arrow, drawn as text so it is not colour alone and turns when open.
  chevron: {
    display: 'inline-block',
    width: '1em',
    marginRight: theme.spacing(0.5),
    color: theme.palette.text.secondary,
    transition: 'transform 120ms',
    'details[open] > summary &': { transform: 'rotate(90deg)' },
  },
  grid: {
    display: 'grid',
    gap: theme.spacing(2),
    // min(18em, 100%) so a tile never asks for more than a 375px phone can give.
    gridTemplateColumns: 'repeat(auto-fill, minmax(min(18em, 100%), 1fr))',
    [phone]: { gap: theme.spacing(1.5) },
  },
  tile: {
    display: 'flex',
    flexDirection: 'column',
    gap: theme.spacing(1),
    padding: theme.spacing(2),
    borderRadius: 12,
    border: `1px solid ${theme.palette.divider}`,
    background: theme.palette.background.paper,
    minWidth: 0,
    overflow: 'hidden',
  },
  tileTop: {
    display: 'flex',
    alignItems: 'center',
    gap: theme.spacing(1),
    flexWrap: 'wrap',
    minWidth: 0,
  },
  tileTitle: {
    fontSize: 15,
    fontWeight: 600,
    lineHeight: 1.3,
    minWidth: 0,
    overflowWrap: 'anywhere',
  },
  everyday: {
    fontSize: 12,
    fontWeight: 600,
    lineHeight: 1,
    letterSpacing: '0.01em',
    color: theme.palette.text.secondary,
    border: `1px solid ${theme.palette.divider}`,
    borderRadius: 999,
    padding: '4px 8px',
    whiteSpace: 'nowrap',
  },
  tileDesc: {
    fontSize: 14,
    lineHeight: 1.5,
    color: theme.palette.text.secondary,
    margin: 0,
    display: '-webkit-box',
    WebkitLineClamp: 2,
    WebkitBoxOrient: 'vertical',
    overflow: 'hidden',
    overflowWrap: 'anywhere',
  },
  actions: { marginTop: 'auto', paddingTop: theme.spacing(0.5) },
  open: { alignSelf: 'flex-start', maxWidth: '100%' },
  also: {
    fontSize: 12,
    fontWeight: 500,
    lineHeight: 1.5,
    color: theme.palette.text.secondary,
    margin: theme.spacing(1, 0, 0),
    overflowWrap: 'anywhere',
  },
  noLink: {
    fontSize: 14,
    lineHeight: 1.5,
    color: theme.palette.text.secondary,
    margin: 0,
  },
  mono: { fontFamily: monoFamily, fontSize: 12, overflowWrap: 'anywhere' },
}));

const titleOf = (e: Entity) => e.metadata.title ?? e.metadata.name;
const tools = (n: number) => `${n} ${n === 1 ? 'tool' : 'tools'}`;

/** One tile per door: state, name, one sentence, one Open button, and the rest as small print. */
const Tile = ({ entity }: { entity: Entity }) => {
  const classes = useStyles();
  const s = doorState(entity);
  const title = titleOf(entity);
  const open = openLink(entity);
  const more = moreLinks(entity);
  const headingId = `tool-${entity.metadata.namespace ?? 'default'}-${
    entity.metadata.name
  }`;
  return (
    <article className={classes.tile} aria-labelledby={headingId}>
      <div className={classes.tileTop}>
        <Pill state={s.state} why={s.why} />
        <Link
          to={entityPath(entity)}
          className={classes.tileTitle}
          id={headingId}
        >
          {title}
        </Link>
        {isDaily(entity) && (
          <span className={classes.everyday} title="You open this most days">
            {EVERYDAY_WORD}
          </span>
        )}
      </div>
      {entity.metadata.description && (
        <p className={classes.tileDesc} title={entity.metadata.description}>
          {entity.metadata.description}
        </p>
      )}
      <div className={classes.actions}>
        {open ? (
          <>
            <LinkButton
              to={open.url}
              color="primary"
              variant="contained"
              size="small"
              className={classes.open}
              aria-label={`${OPEN_WORD} ${title}`}
            >
              {OPEN_WORD}
            </LinkButton>
            {more.length > 0 && (
              <p className={classes.also}>
                {ALSO_WORD}{' '}
                {more.map((l, i) => (
                  <span key={l.url}>
                    {i > 0 && ' · '}
                    <Link to={l.url}>{l.title}</Link>
                  </span>
                ))}
              </p>
            )}
          </>
        ) : (
          <p className={classes.noLink}>{NO_LINK_SENTENCE}</p>
        )}
      </div>
    </article>
  );
};

const Grid = ({ group }: { group: ToolGroup }) => {
  const classes = useStyles();
  return (
    <div className={classes.grid}>
      {group.tools.map(e => (
        <Tile
          key={`${e.metadata.namespace ?? 'default'}/${e.metadata.name}`}
          entity={e}
        />
      ))}
    </div>
  );
};

/** A group: heading with its count, one line saying what it is for, then its tiles. */
const Group = ({ group }: { group: ToolGroup }) => {
  const classes = useStyles();
  const blurb = GROUP_BLURB[group.name];
  if (group.folded) {
    return (
      <details className={classes.group}>
        <summary className={classes.summary}>
          <span className={classes.groupTitle}>
            <span className={classes.chevron} aria-hidden="true">
              ▸
            </span>
            {group.name}, {tools(group.tools.length)}.
          </span>
          {blurb && <span className={classes.blurb}> {blurb}</span>}
        </summary>
        <Grid group={group} />
      </details>
    );
  }
  return (
    <section className={classes.group}>
      <div className={classes.groupHead}>
        <h2 className={classes.groupTitle}>
          {group.name}
          <span className={classes.groupCount}>
            {tools(group.tools.length)}
          </span>
        </h2>
        {blurb && <p className={classes.blurb}>{blurb}</p>}
      </div>
      <Grid group={group} />
    </section>
  );
};

export const Tools = () => {
  const classes = useStyles();
  const doors = useDoors();
  const groups = doors.state === 'ready' ? groupTools(doors.doors) : [];
  return (
    <Page themeId="home">
      <Content>
        <header className={classes.header}>
          <Typography variant="h1" component="h1">
            {HEADLINE}
          </Typography>
          <p className={classes.lead}>{LEAD}</p>
          {doors.state === 'loading' && (
            <p className={classes.sentence} role="status">
              {LOADING_SENTENCE}
            </p>
          )}
          {doors.state === 'error' && (
            <p className={classes.sentence} role="alert">
              {ERROR_SENTENCE}{' '}
              <span className={classes.mono}>{doors.error.message}</span>
            </p>
          )}
          {doors.state === 'ready' && (
            <p className={classes.sentence}>{toolsSentence(groups)}</p>
          )}
        </header>
        {groups.map(g => (
          <Group key={g.name} group={g} />
        ))}
      </Content>
    </Page>
  );
};
