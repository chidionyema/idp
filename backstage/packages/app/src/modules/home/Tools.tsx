// The Tools page: every door the founder opens, on one page, grouped (crew#684 CP0).
// Founder, 2026-08-30: "i am founder, i am CEO and i am also engineer ... so i need all the
// tools one place ... another page in backstage just pure tools". Pure links: one tile per
// founder-surface entity, its `links:` as buttons, its probe state as the pill the front page
// uses. Nothing here names a tool; the catalogue is the list (LAW 46).
import { Entity } from '@backstage/catalog-model';
import { Content, Link, LinkButton, Page } from '@backstage/core-components';
import { Typography, makeStyles } from '@material-ui/core';
import { doorState, entityPath } from './estate';
import { useDoors } from './useDoors';
import { ToolGroup, groupTools, toolsSentence } from './toolGroups';
import { Pill } from './EstateHome';
import { monoFamily } from '../theme/tokens';

const useStyles = makeStyles(theme => ({
  header: { marginBottom: theme.spacing(3) },
  lead: { fontSize: 17, margin: theme.spacing(1, 0, 0) },
  group: { marginBottom: theme.spacing(4) },
  groupTitle: { fontSize: 20, fontWeight: 600, margin: theme.spacing(0, 0, 1.5) },
  grid: {
    display: 'grid',
    gap: theme.spacing(1.5),
    gridTemplateColumns: 'repeat(auto-fill, minmax(18em, 1fr))',
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
  },
  tileTop: { display: 'flex', alignItems: 'center', gap: theme.spacing(1), flexWrap: 'wrap' },
  tileTitle: { fontWeight: 500, flex: '1 1 10em', minWidth: 0, overflowWrap: 'anywhere' },
  tileDesc: {
    fontSize: 13,
    color: theme.palette.text.secondary,
    margin: 0,
    display: '-webkit-box',
    WebkitLineClamp: 3,
    WebkitBoxOrient: 'vertical',
    overflow: 'hidden',
  },
  links: { display: 'flex', gap: theme.spacing(0.5), flexWrap: 'wrap' },
  door: {
    maxWidth: '100%',
    '& .MuiButton-label': { whiteSpace: 'normal', overflowWrap: 'anywhere' },
  },
  mono: { fontFamily: monoFamily, fontSize: 12, overflowWrap: 'anywhere' },
}));

export const TITLE = 'Tools';

/** One tile per door: state, name, what it is for, and every link it publishes. */
const Tile = ({ entity }: { entity: Entity }) => {
  const classes = useStyles();
  const s = doorState(entity);
  const links = entity.metadata.links ?? [];
  return (
    <div
      className={classes.tile}
      data-testid={`tool-${entity.metadata.name}`}
      data-state={s.state}
    >
      <div className={classes.tileTop}>
        <Pill state={s.state} why={s.why} testId={`tool-health-${entity.metadata.name}`} />
        <Link to={entityPath(entity)} className={classes.tileTitle}>
          {entity.metadata.title ?? entity.metadata.name}
        </Link>
      </div>
      {entity.metadata.description && (
        <p className={classes.tileDesc} title={entity.metadata.description}>
          {entity.metadata.description}
        </p>
      )}
      <div className={classes.links}>
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

const Group = ({ group }: { group: ToolGroup }) => {
  const classes = useStyles();
  return (
    <section className={classes.group} data-testid={`tools-group-${group.name}`}>
      <h2 className={classes.groupTitle}>
        {group.name}{' '}
        <Typography component="span" color="textSecondary">
          {group.tools.length}
        </Typography>
      </h2>
      <div className={classes.grid}>
        {group.tools.map(e => (
          <Tile key={e.metadata.name} entity={e} />
        ))}
      </div>
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
            {TITLE}
          </Typography>
          {doors.state === 'loading' && (
            <p className={classes.lead} data-testid="tools-loading">
              Reading the catalogue.
            </p>
          )}
          {doors.state === 'error' && (
            <p className={classes.lead} data-testid="tools-error">
              The catalogue did not answer, so nothing can be listed.{' '}
              <span className={classes.mono}>{doors.error.message}</span>
            </p>
          )}
          {doors.state === 'ready' && (
            <p className={classes.lead} data-testid="tools-sentence">
              {toolsSentence(groups)}
            </p>
          )}
        </header>
        {groups.map(g => (
          <Group key={g.name} group={g} />
        ))}
      </Content>
    </Page>
  );
};
