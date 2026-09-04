// The Health page at /ops (crew#684): "I need to see everything". The cluster, what waits on
// the founder, the drills, the scheduled jobs, the inventory, and every open red with its
// owner -- each read live, each saying plainly when it could not be read.
//
// crew#843: the page was built before the shell existed and drew its own header, tiles, grid
// and table. Its Backstage UI header sat outside Content, so it rendered at a different width
// to everything under it, and the lead sentence printed twice -- once in the header and once
// in the body. Both are gone: the page top, the tiles and the table now come from
// modules/shell, which every estate page shares, and this file carries no styling of its own.
import { Link } from '@backstage/core-components';
import { Text } from '@backstage/ui';
import { configApiRef, useApi } from '@backstage/frontend-plugin-api';
import { Pill } from './EstateHome';
import {
  EstatePage,
  Fact,
  Name,
  Names,
  Section,
  Sheet,
  Summary,
  Tile,
  Tiles,
  Unread,
  UnreadTile,
  Waiting,
} from '../shell';
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

/** The page's name, and the word every door to it already uses (nav, app-config, catalogue). */
export const TITLE = 'Health';
/** The sentence only this page says; the login drill grades the page on it. */
export const LEAD = 'The cluster right now, and every red with its owner.';

const ClusterTile = ({ health }: { health: ClusterHealth }) => {
  const pods = health.podsNotReady.reduce((n, r) => n + r.count, 0);
  return (
    <Tile
      title="Cluster"
      testId="ops-cluster"
      state={health.state}
      badge={
        <Pill state={health.state} why={health.why} testId="ops-cluster-health" />
      }
    >
      <Fact
        label="Nodes ready"
        value={`${health.nodes.ready} of ${health.nodes.total}`}
        testId="ops-nodes"
      />
      {health.nodes.notReady.length > 0 && (
        <Names>
          {health.nodes.notReady.map(n => (
            <li key={n}>
              <Name>{n}</Name>
            </li>
          ))}
        </Names>
      )}
      <Fact label="Pods not ready" value={pods} testId="ops-pods" />
      {health.podsNotReady.length > 0 && (
        <Names>
          {health.podsNotReady.map(r => (
            <li key={r.namespace}>
              <Name>{r.namespace}</Name> {r.count}
            </li>
          ))}
        </Names>
      )}
      <Fact
        label="Flux rows ready"
        value={`${health.flux.ready} of ${health.flux.total}`}
        testId="ops-flux"
      />
      {health.flux.notReady.length > 0 && (
        <Names>
          {health.flux.notReady.map(r => (
            <li key={`${r.kind}/${r.namespace}/${r.name}`}>
              <Name>
                {r.kind} {r.namespace ? `${r.namespace}/` : ''}
                {r.name}
              </Name>{' '}
              {r.why}
            </li>
          ))}
        </Names>
      )}
    </Tile>
  );
};

const KIND_LABEL: Record<Red['kind'], string> = {
  alert: 'Alert',
  drill: 'Drill',
  door: 'Door',
};

const RedsTable = ({ reds, now }: { reds: Red[]; now: number }) => (
  <Sheet testId="ops-reds">
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
            <Name>{KIND_LABEL[r.kind]}</Name>{' '}
            {r.link ? <Link to={r.link}>{r.name}</Link> : r.name}
            <br />
            <Name>{r.why}</Name>
          </td>
          <td>
            {r.owner ?? <span className="estate-missing">No owner</span>}
          </td>
          <td title={r.since}>{ago(r.since, now) ?? 'Unknown'}</td>
          <td>{r.nextAction}</td>
          <td>
            {r.boardUrl ? (
              <Link to={r.boardUrl}>Board</Link>
            ) : (
              <span className="estate-missing">No board link</span>
            )}
          </td>
        </tr>
      ))}
    </tbody>
  </Sheet>
);

const FounderTiles = ({ data, now }: { data: FounderData; now: number }) => (
  <>
    <Tile title="Waiting on you" testId="ops-waiting">
      <Text variant="body-medium" data-testid="ops-waiting-sentence">
        {waitingSentence(data)}
      </Text>
      {data.waiting.length > 0 && (
        <Names>
          {data.waiting.map(w => (
            <li key={`${w.issue}/${w.cp}`} data-testid="ops-waiting-row">
              <Link to={w.url}>
                crew#{w.issue} {w.cp}
              </Link>{' '}
              {w.what}
            </li>
          ))}
        </Names>
      )}
    </Tile>
    <Tile title="Last receipts" testId="ops-receipts">
      <Text variant="body-medium" data-testid="ops-receipts-sentence">
        {receiptsSentence(data)}
      </Text>
      {data.receipts.length > 0 && (
        <Names>
          {data.receipts.map(r => (
            <li key={`${r.repo}#${r.number}`} data-testid="ops-receipt-row">
              <Link to={r.url}>
                {r.repo.split('/')[1]}#{r.number}
              </Link>{' '}
              {r.use} <Name>{ago(r.merged_at, now)}</Name>
            </li>
          ))}
        </Names>
      )}
    </Tile>
  </>
);

const DrillsTile = ({ drills }: { drills: DrillSummary }) => (
  <Tile title="Drills" testId="ops-drills">
    <Text variant="body-medium" data-testid="ops-drills-sentence">
      {drillsSentence(drills)}
    </Text>
  </Tile>
);

const HealthchecksTile = ({ data }: { data: Checks }) => {
  const rows = notUp(data);
  return (
    <Tile title="Scheduled jobs" testId="ops-healthchecks">
      <Text variant="body-medium" data-testid="ops-healthchecks-sentence">
        {checksSentence(data)}
      </Text>
      {rows.length > 0 && (
        <Names>
          {rows.map(c => (
            <li key={c.name} data-testid="ops-healthcheck-row">
              <Name>{c.name}</Name> {STATUS_WORD[c.status]}
            </li>
          ))}
        </Names>
      )}
    </Tile>
  );
};

// crew#740: what every plane actually holds, graded against git, from the table the inventory
// workflow publishes on the state branch. An unread plane is said so, never a green zero.
const InventoryTile = ({ data, now }: { data: InventoryData; now: number }) => {
  const config = useApi(configApiRef);
  const base = config.getOptionalString('backend.baseUrl') ?? '';
  return (
    <Tile
      title="Estate inventory"
      testId="ops-inventory"
      aside={<Name>{ago(data.generated_at, now) ?? 'Unknown'}</Name>}
    >
      <Text variant="body-medium" data-testid="ops-inventory-sentence">
        {inventorySentence(data)}
      </Text>
      <Names>
        {planeOrder(data).map(plane => (
          <li
            key={plane}
            data-testid="ops-inventory-row"
            data-read={data.counts[plane].read}
          >
            {PLANE_WORD[plane] ?? plane}: {planeSentence(data.counts[plane])}
          </li>
        ))}
      </Names>
      {data.blind.length > 0 && (
        <Names>
          {data.blind.map(b => (
            <li key={b} data-testid="ops-inventory-blind">
              <Name>{b}</Name>
            </li>
          ))}
        </Names>
      )}
      <Link to={`${base}/api/proxy${INVENTORY_TABLE}`}>The full table</Link>
    </Tile>
  );
};

export const Ops = () => {
  const loaded = useClusterHealth();
  const reds = useOpenReds();
  const founder = useFounder();
  const checks = useHealthchecks();
  const inventory = useInventory();
  const now = Date.now();
  return (
    <EstatePage title={TITLE} lead={LEAD}>
      {loaded.state === 'loading' && (
        <Waiting testId="ops-loading">Reading the cluster.</Waiting>
      )}
      {loaded.state === 'error' && (
        <Unread testId="ops-error" detail={loaded.error}>
          The cluster could not be read, so nothing below is known.
        </Unread>
      )}
      {loaded.state === 'ready' && (
        <Summary testId="ops-sentence">{healthSentence(loaded.health)}</Summary>
      )}
      <Tiles>
        {loaded.state === 'ready' && <ClusterTile health={loaded.health} />}
        {founder.state === 'ready' && (
          <FounderTiles data={founder.data} now={now} />
        )}
        {reds.state === 'ready' && reds.drills && (
          <DrillsTile drills={reds.drills} />
        )}
        {checks.state === 'ready' && <HealthchecksTile data={checks.data} />}
        {checks.state === 'error' && (
          <UnreadTile testId="ops-healthchecks-error" detail={checks.error}>
            Scheduled jobs could not be read, so their state is unknown.
          </UnreadTile>
        )}
        {inventory.state === 'ready' && (
          <InventoryTile data={inventory.data} now={now} />
        )}
        {inventory.state === 'error' && (
          <UnreadTile testId="ops-inventory-error" detail={inventory.error}>
            The estate inventory could not be read, so it is unknown.
          </UnreadTile>
        )}
        {founder.state === 'error' && (
          <UnreadTile testId="ops-founder-error" detail={founder.error}>
            What waits on you could not be read, so it is unknown.
          </UnreadTile>
        )}
      </Tiles>
      <Section
        title="Open reds"
        blurb="Every firing alert, red drill and door that is down, with its owner and what happens next. A red with no owner is itself a red."
        testId="ops-reds-section"
      >
        {reds.state === 'loading' && (
          <Waiting testId="ops-reds-loading">
            Reading the alerts and the catalogue.
          </Waiting>
        )}
        {reds.state === 'ready' && (
          <>
            <Text variant="body-medium" data-testid="ops-reds-sentence">
              {redsSentence(reds.reds)}
            </Text>
            {reds.unread.map(u => (
              <Unread key={u} testId="ops-reds-unread">
                Could not be read, so its reds are unknown: {u}
              </Unread>
            ))}
            {reds.reds.length > 0 && <RedsTable reds={reds.reds} now={now} />}
          </>
        )}
      </Section>
    </EstatePage>
  );
};
