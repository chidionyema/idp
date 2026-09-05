// The Ops dashboard (crew#684): "I need to see everything". CP1 is the cluster tile — nodes
// ready, pods not ready by namespace, Flux rows not ready — read live through the Kubernetes
// plugin. CP2 adds the open-reds table: every firing alert, red drill and door down, with its
// owner, since when, the next action and the board link; a red with no owner is itself a red.
import { Content, Link, Page } from '@backstage/core-components';
import { Typography, makeStyles } from '@material-ui/core';
import { configApiRef, useApi } from '@backstage/frontend-plugin-api';
import { Pill } from './EstateHome';
import { ClusterHealth, healthSentence } from './clusterHealth';
import { useClusterHealth } from './useClusterHealth';
import { DrillSummary, Red, drillsSentence, redsSentence } from './openReds';
import { useOpenReds } from './useOpenReds';
import { FounderData, receiptsSentence, waitingSentence } from './founder';
import { useFounder } from './useFounder';
import { useHealthchecks } from './useHealthchecks';
import { Checks, STATUS_WORD, checksSentence, notUp } from './healthchecks';
import {
  INVENTORY_TABLE,
  InventoryData,
  PLANE_WORD,
  inventorySentence,
  planeOrder,
  planeSentence,
} from './inventory';
import { useInventory } from './useInventory';
import { ago } from './estate';
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
  reds: { marginTop: theme.spacing(3) },
  redsTitle: { fontWeight: 600, fontSize: 18, margin: theme.spacing(0, 0, 1) },
  table: {
    width: '100%',
    borderCollapse: 'collapse',
    fontSize: 14,
    '& th, & td': {
      textAlign: 'left',
      verticalAlign: 'top',
      padding: theme.spacing(1),
      borderBottom: `1px solid ${theme.palette.divider}`,
    },
    '& th': { fontWeight: 600, color: theme.palette.text.secondary },
  },
  unowned: { color: theme.palette.error.main, fontWeight: 600 },
  scroll: { overflowX: 'auto' },
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

const KIND_LABEL: Record<Red['kind'], string> = {
  alert: 'Alert',
  drill: 'Drill',
  door: 'Door',
};

const RedsTable = ({ reds, now }: { reds: Red[]; now: number }) => {
  const classes = useStyles();
  return (
    <div className={classes.scroll}>
      <table className={classes.table} data-testid="ops-reds">
        <thead>
          <tr>
            <th>Red</th>
            <th>Owner</th>
            <th>Since</th>
            <th>Next action</th>
            <th>Board</th>
          </tr>
        </thead>
        <tbody>
          {reds.map(r => (
            <tr
              key={r.key}
              data-testid="ops-red"
              data-kind={r.kind}
              data-owned={r.owner ? 'yes' : 'no'}
            >
              <td>
                <span className={classes.mono}>{KIND_LABEL[r.kind]}</span>{' '}
                {r.link ? <Link to={r.link}>{r.name}</Link> : r.name}
                <br />
                <span className={classes.mono}>{r.why}</span>
              </td>
              <td>
                {r.owner ?? <span className={classes.unowned}>No owner</span>}
              </td>
              <td title={r.since}>{ago(r.since, now) ?? 'Unknown'}</td>
              <td>{r.nextAction}</td>
              <td>
                {r.boardUrl ? (
                  <Link to={r.boardUrl}>Board</Link>
                ) : (
                  <span className={classes.unowned}>No board link</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

const FounderTiles = ({ data, now }: { data: FounderData; now: number }) => {
  const classes = useStyles();
  return (
    <>
      <div className={classes.tile} data-testid="ops-waiting">
        <div className={classes.tileTop}>
          <span className={classes.tileTitle}>Waiting on you</span>
        </div>
        <p data-testid="ops-waiting-sentence">{waitingSentence(data)}</p>
        {data.waiting.length > 0 && (
          <ul className={classes.list}>
            {data.waiting.map(w => (
              <li key={`${w.issue}/${w.cp}`} data-testid="ops-waiting-row">
                <Link to={w.url}>
                  crew#{w.issue} {w.cp}
                </Link>{' '}
                {w.what}
              </li>
            ))}
          </ul>
        )}
      </div>
      <div className={classes.tile} data-testid="ops-receipts">
        <div className={classes.tileTop}>
          <span className={classes.tileTitle}>Last receipts</span>
        </div>
        <p data-testid="ops-receipts-sentence">{receiptsSentence(data)}</p>
        {data.receipts.length > 0 && (
          <ul className={classes.list}>
            {data.receipts.map(r => (
              <li key={`${r.repo}#${r.number}`} data-testid="ops-receipt-row">
                <Link to={r.url}>
                  {r.repo.split('/')[1]}#{r.number}
                </Link>{' '}
                {r.use}{' '}
                <span className={classes.mono}>{ago(r.merged_at, now)}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </>
  );
};

const DrillsTile = ({ drills }: { drills: DrillSummary }) => {
  const classes = useStyles();
  return (
    <div className={classes.tile} data-testid="ops-drills">
      <div className={classes.tileTop}>
        <span className={classes.tileTitle}>Drills</span>
      </div>
      <p data-testid="ops-drills-sentence">{drillsSentence(drills)}</p>
    </div>
  );
};

const HealthchecksTile = ({ data }: { data: Checks }) => {
  const classes = useStyles();
  const rows = notUp(data);
  return (
    <div className={classes.tile} data-testid="ops-healthchecks">
      <div className={classes.tileTop}>
        <span className={classes.tileTitle}>Scheduled jobs</span>
      </div>
      <p data-testid="ops-healthchecks-sentence">{checksSentence(data)}</p>
      {rows.length > 0 && (
        <ul className={classes.list}>
          {rows.map(c => (
            <li key={c.name} data-testid="ops-healthcheck-row">
              <span className={classes.mono}>{c.name}</span>{' '}
              {STATUS_WORD[c.status]}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

// crew#740: what every plane actually holds, graded against git, from the table the inventory
// workflow publishes on the state branch. An unread plane is said so, never a green zero.
const InventoryTile = ({ data, now }: { data: InventoryData; now: number }) => {
  const classes = useStyles();
  const config = useApi(configApiRef);
  const base = config.getOptionalString('backend.baseUrl') ?? '';
  return (
    <div className={classes.tile} data-testid="ops-inventory">
      <div className={classes.tileTop}>
        <span className={classes.tileTitle}>Estate inventory</span>
        <span className={classes.mono} title={data.generated_at}>
          {ago(data.generated_at, now) ?? 'Unknown'}
        </span>
      </div>
      <p data-testid="ops-inventory-sentence">{inventorySentence(data)}</p>
      <ul className={classes.list}>
        {planeOrder(data).map(plane => (
          <li
            key={plane}
            data-testid="ops-inventory-row"
            data-read={data.counts[plane].read}
          >
            {PLANE_WORD[plane] ?? plane}: {planeSentence(data.counts[plane])}
          </li>
        ))}
      </ul>
      {data.blind.length > 0 && (
        <ul className={classes.list}>
          {data.blind.map(b => (
            <li
              key={b}
              className={classes.mono}
              data-testid="ops-inventory-blind"
            >
              {b}
            </li>
          ))}
        </ul>
      )}
      <Link to={`${base}/api/proxy${INVENTORY_TABLE}`}>The full table</Link>
    </div>
  );
};

export const Ops = () => {
  const classes = useStyles();
  const loaded = useClusterHealth();
  const reds = useOpenReds();
  const founder = useFounder();
  const checks = useHealthchecks();
  const inventory = useInventory();
  const now = Date.now();
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
          {founder.state === 'ready' && (
            <FounderTiles data={founder.data} now={now} />
          )}
          {reds.state === 'ready' && reds.drills && (
            <DrillsTile drills={reds.drills} />
          )}
          {checks.state === 'ready' && <HealthchecksTile data={checks.data} />}
          {checks.state === 'error' && (
            <div className={classes.tile} data-testid="ops-healthchecks-error">
              Scheduled jobs could not be read, so their state is unknown.{' '}
              <span className={classes.mono}>{checks.error}</span>
            </div>
          )}
          {inventory.state === 'ready' && (
            <InventoryTile data={inventory.data} now={now} />
          )}
          {inventory.state === 'error' && (
            <div className={classes.tile} data-testid="ops-inventory-error">
              The estate inventory could not be read, so it is unknown.{' '}
              <span className={classes.mono}>{inventory.error}</span>
            </div>
          )}
          {founder.state === 'error' && (
            <div className={classes.tile} data-testid="ops-founder-error">
              What waits on you could not be read, so it is unknown.{' '}
              <span className={classes.mono}>{founder.error}</span>
            </div>
          )}
        </div>
        <section className={classes.reds} data-testid="ops-reds-section">
          <h2 className={classes.redsTitle}>Open reds</h2>
          {reds.state === 'loading' && (
            <p data-testid="ops-reds-loading">
              Reading the alerts and the catalogue.
            </p>
          )}
          {reds.state === 'ready' && (
            <>
              <p data-testid="ops-reds-sentence">{redsSentence(reds.reds)}</p>
              {reds.unread.map(u => (
                <p
                  key={u}
                  data-testid="ops-reds-unread"
                  className={classes.unowned}
                >
                  Could not be read, so its reds are unknown: {u}
                </p>
              ))}
              {reds.reds.length > 0 && <RedsTable reds={reds.reds} now={now} />}
            </>
          )}
        </section>
      </Content>
    </Page>
  );
};
