// The Ops dashboard (crew#684): "I need to see everything". CP1 is the cluster tile — nodes
// ready, pods not ready by namespace, Flux rows not ready — read live through the Kubernetes
// plugin. Later checkpoints add the open-reds table, founder tiles and the drills row here.
import { Content, Page } from '@backstage/core-components';
import { Typography, makeStyles } from '@material-ui/core';
import { Pill } from './EstateHome';
import { ClusterHealth, healthSentence } from './clusterHealth';
import { useClusterHealth } from './useClusterHealth';
import { monoFamily } from '../theme/tokens';

const useStyles = makeStyles(theme => ({
  header: { marginBottom: theme.spacing(3) },
  lead: { fontSize: 17, margin: theme.spacing(1, 0, 0) },
  grid: {
    display: 'grid',
    gap: theme.spacing(1.5),
    gridTemplateColumns: 'repeat(auto-fill, minmax(22em, 1fr))',
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
  tileTop: {
    display: 'flex',
    alignItems: 'center',
    gap: theme.spacing(1),
    flexWrap: 'wrap',
  },
  tileTitle: { fontWeight: 600, fontSize: 18, flex: '1 1 10em' },
  row: {
    display: 'flex',
    justifyContent: 'space-between',
    gap: theme.spacing(1),
    fontSize: 14,
  },
  list: {
    margin: 0,
    paddingLeft: theme.spacing(2.5),
    fontSize: 13,
    color: theme.palette.text.secondary,
  },
  mono: { fontFamily: monoFamily, fontSize: 12, overflowWrap: 'anywhere' },
}));

export const TITLE = 'Ops';
/** The sentence only this page says; the login drill grades the page on it. */
export const LEAD = 'The cluster right now, and every red with its owner.';

const ClusterTile = ({ health }: { health: ClusterHealth }) => {
  const classes = useStyles();
  const pods = health.podsNotReady.reduce((n, r) => n + r.count, 0);
  return (
    <div
      className={classes.tile}
      data-testid="ops-cluster"
      data-state={health.state}
    >
      <div className={classes.tileTop}>
        <Pill
          state={health.state}
          why={health.why}
          testId="ops-cluster-health"
        />
        <span className={classes.tileTitle}>Cluster</span>
      </div>
      <div className={classes.row} data-testid="ops-nodes">
        <span>Nodes ready</span>
        <span>
          {health.nodes.ready} of {health.nodes.total}
        </span>
      </div>
      {health.nodes.notReady.length > 0 && (
        <ul className={classes.list}>
          {health.nodes.notReady.map(n => (
            <li key={n} className={classes.mono}>
              {n}
            </li>
          ))}
        </ul>
      )}
      <div className={classes.row} data-testid="ops-pods">
        <span>Pods not ready</span>
        <span>{pods}</span>
      </div>
      {health.podsNotReady.length > 0 && (
        <ul className={classes.list}>
          {health.podsNotReady.map(r => (
            <li key={r.namespace}>
              <span className={classes.mono}>{r.namespace}</span> {r.count}
            </li>
          ))}
        </ul>
      )}
      <div className={classes.row} data-testid="ops-flux">
        <span>Flux rows ready</span>
        <span>
          {health.flux.ready} of {health.flux.total}
        </span>
      </div>
      {health.flux.notReady.length > 0 && (
        <ul className={classes.list}>
          {health.flux.notReady.map(r => (
            <li key={`${r.kind}/${r.namespace}/${r.name}`}>
              <span className={classes.mono}>
                {r.kind} {r.namespace ? `${r.namespace}/` : ''}
                {r.name}
              </span>{' '}
              {r.why}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

export const Ops = () => {
  const classes = useStyles();
  const loaded = useClusterHealth();
  return (
    <Page themeId="home">
      <Content>
        <header className={classes.header}>
          <Typography variant="h1" component="h1">
            {TITLE}
          </Typography>
          <p className={classes.lead} data-testid="ops-lead">
            {LEAD}
          </p>
          {loaded.state === 'loading' && (
            <p className={classes.lead} data-testid="ops-loading">
              Reading the cluster.
            </p>
          )}
          {loaded.state === 'error' && (
            <p className={classes.lead} data-testid="ops-error">
              The cluster could not be read, so nothing below is known.{' '}
              <span className={classes.mono}>{loaded.error}</span>
            </p>
          )}
          {loaded.state === 'ready' && (
            <p className={classes.lead} data-testid="ops-sentence">
              {healthSentence(loaded.health)}
            </p>
          )}
        </header>
        <div className={classes.grid}>
          {loaded.state === 'ready' && <ClusterTile health={loaded.health} />}
        </div>
      </Content>
    </Page>
  );
};
