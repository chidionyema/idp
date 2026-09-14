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
import { usePlacement } from './usePlacement';
import { useCompiled } from './useCompiled';
import { cpuLabel, guaranteed } from './compiled';
import { headroomLabel, placementState, requestLabel } from './placement';
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
import { useEstateGraph } from './useEstateGraph';
import { domainRows, graphSentence, worst } from './estateGraph';
import { useGuards } from './useGuards';
import { guardRows, guardsSentence, guardsUnreadable } from './guards';
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

// crew#716 + crew#684 CP-pending: the estate's one scheduler (Dagster) lives in-cluster; the
// tile is the link from /ops to the webserver. The backend proxy plugin (/dagster -> the
// in-cluster Service) is the door, so the browser never reaches the cluster address directly.
// Once the platform/edge HTTPRoute for dagster-webserver lands (W4 glass-break), the target
// moves to the gateway hostname and the loop is closed end to end.
const SchedulerTile = () => (
  <Tile title="Scheduler (Dagster)" testId="ops-scheduler">
    <Text variant="body-medium" data-testid="ops-scheduler-sentence">
      The one scheduler for every recurring job. Open it for runs, sensors and schedules.
    </Text>
    <Names>
      <li data-testid="ops-scheduler-link">
        <Link to="/dagster" data-testid="ops-scheduler-open">Open the scheduler</Link>
      </li>
    </Names>
  </Tile>
);

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
  const placement = usePlacement();
  const compiled = useCompiled();
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
        <SchedulerTile />
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
      {/* Placement: whether the workloads that run could be placed again.
          This is the question that had no page. A pod the scheduler refused is NOT RUNNING and
          comes first; a pinned pod is running but would not come back after one drain, which is
          the state SigNoz's ClickHouse sat in for eleven days. And when the receipt carries both,
          the sentence says how much CPU is reserved but idle -- the fact that explains a cluster
          reading 96% full while using 39%. */}
      <Section
        title="Placement"
        blurb="Whether the workloads that run could be placed on the nodes that exist, and how much of the CPU we reserve is actually used."
        testId="ops-placement-section"
      >
        {placement.state === 'loading' && (
          <Waiting testId="ops-placement-loading">Reading placement.</Waiting>
        )}
        {placement.state === 'error' && (
          <Unread testId="ops-placement-error" detail={placement.error}>
            Placement could not be measured, so whether anything could be placed again is
            unknown.
          </Unread>
        )}
        {placement.state === 'ready' && (
          <>
            <Text variant="body-medium" data-testid="ops-placement-sentence">
              {placement.summary.summary}
            </Text>
            {placement.at && (
              <Text variant="body-small" color="secondary">
                Measured {ago(placement.at, now) ?? placement.at}
              </Text>
            )}
            {placement.summary.refused.length + placement.summary.pinned.length > 0 && (
              <Sheet testId="ops-placement">
                <thead>
                  <tr>
                    <th>Workload</th>
                    <th>Problem</th>
                    <th>Asks</th>
                    <th>Best other node</th>
                  </tr>
                </thead>
                <tbody>
                  {[
                    ...placement.summary.refused,
                    ...placement.summary.pinned,
                  ].map(p => (
                    <tr key={`${p.namespace}/${p.name}`}>
                      <td>
                        {p.namespace}/{p.kind ? `${p.kind}/` : ''}
                        {p.name}
                      </td>
                      <td title={p.reason ?? undefined}>
                        {placementState(p) === 'refused'
                          ? 'The scheduler refused it'
                          : 'No other node would take it'}
                      </td>
                      <td>{requestLabel(p)}</td>
                      <td>{headroomLabel(p)}</td>
                      <td>{requestLabel(p)}</td>
                      <td>{headroomLabel(p)}</td>
                    </tr>
                  ))}
                </tbody>
              </Sheet>
            )}
          </>
        )}
      </Section>
      <GraphSection />
      <GuardsSection now={now} />
      {/* The compiled estate: what every Helm chart RENDERS, straight from git.
          This is the instrument that closes the five-day gap. A values file, a comment and a
          postRenderer patch are all CLAIMS; the number below is the one the chart decides, which
          is the one the cluster runs. On 2026-09-12 langfuse-web rendered 1000m while the comment
          beside that value said 500m, and nothing in the estate could see the difference. */}
      <Section
        title="What the charts actually render"
        blurb="Every Helm release compiled from git. The value shown is the one the chart produces, never the one a comment claims."
        testId="ops-compiled-section"
      >
        {compiled.state === 'loading' && (
          <Waiting testId="ops-compiled-loading">Compiling the estate.</Waiting>
        )}
        {compiled.state === 'error' && (
          <Unread testId="ops-compiled-error" detail={compiled.error}>
            The compiled estate could not be read, so what the charts will run is unknown.
          </Unread>
        )}
        {compiled.state === 'ready' && (
          <>
            <Text variant="body-medium" data-testid="ops-compiled-sentence">
              {compiled.summary.summary}
            </Text>
            {compiled.summary.unrendered.length > 0 && (
              <Sheet testId="ops-compiled-blind">
                <thead>
                  <tr>
                    <th>Release</th>
                    <th>Why it did not render</th>
                  </tr>
                </thead>
                <tbody>
                  {compiled.summary.unrendered.map(r => (
                    <tr key={`${r.namespace}/${r.name}`}>
                      <td>
                        {r.namespace}/{r.name}
                      </td>
                      <td>{r.error}</td>
                    </tr>
                  ))}
                </tbody>
              </Sheet>
            )}
            <Sheet testId="ops-compiled">
              <thead>
                <tr>
                  <th>Workload</th>
                  <th>Container</th>
                  <th>Rendered cpu</th>
                  <th>Guaranteed</th>
                </tr>
              </thead>
              <tbody>
                {compiled.summary.workloads.flatMap(w =>
                  w.containers.map(c => (
                    <tr key={`${w.namespace}/${w.name}/${c.name}`}>
                      <td>
                        {w.namespace}/{w.kind}/{w.name}
                      </td>
                      <td>{c.name}</td>
                      <td>{cpuLabel(c)}</td>
                      <td>{guaranteed(c) ? 'yes' : 'no'}</td>
                    </tr>
                  )),
                )}
              </tbody>
            </Sheet>
          </>
        )}
      </Section>
    </EstatePage>
  );
};

/**
 * The estate's own memory, beside the live probe above.
 *
 * The distinction this section exists to hold: everything else on this page asks the cluster
 * what it is doing now. This asks the estate what it has recorded about itself -- including
 * the half no probe can reach. 648 branches carrying 94,093 files that exist on no commit of
 * main are not cluster objects; they are in the graph and nowhere else.
 *
 * The three-state rule is rendered, not summarised away. A domain outside its freshness
 * window leads the sentence, because a graph that has not been read is a memory, and a page
 * that showed it as healthy would be the exact failure this exists to prevent.
 */
const GraphSection = () => {
  const loaded = useEstateGraph();
  return (
    <Section
      title="What the estate has recorded about itself"
      blurb="The estate's own graph: what is built, what is running and what is not. Unlike the readings above, this is not a probe of the cluster -- it is what the estate already knows, including work that exists on a branch and on no commit of main."
      testId="ops-graph-section"
    >
      {loaded.state === 'loading' && (
        <Waiting testId="ops-graph-loading">Reading the estate graph.</Waiting>
      )}
      {loaded.state === 'error' && (
        <Unread testId="ops-graph-error" detail={loaded.error}>
          The estate graph could not be read, so what the estate has recorded is unknown.
        </Unread>
      )}
      {loaded.state === 'ready' && (
        <>
          <Text variant="body-medium" data-testid="ops-graph-sentence">
            {graphSentence(loaded.graph)}
          </Text>
          <Sheet testId="ops-graph-domains">
            {domainRows(loaded.graph).map(d => (
              <Fact
                key={d.domain}
                label={`${d.domain} — ${d.state.toLowerCase().replace(/_/g, ' ')}`}
                value={`${d.detail} (${d.age})`}
              />
            ))}
          </Sheet>
          {loaded.graph.not_serving.length > 0 && (
            <Sheet testId="ops-graph-worst">
              <Fact label="Not serving" value={String(loaded.graph.not_serving_total)} />
              {worst(loaded.graph).map(n => (
                <Fact key={n.id} label={n.status} value={n.id} />
              ))}
            </Sheet>
          )}
          {loaded.graph.truncated && loaded.graph.note && (
            <Text variant="body-small" data-testid="ops-graph-truncated">
              {loaded.graph.note}
            </Text>
          )}
          {loaded.graph.evidence.length > 0 && (
            <Text variant="body-small" data-testid="ops-graph-evidence">
              Also recorded, as evidence rather than failure:{' '}
              {loaded.graph.evidence.map(e => `${e.n} ${e.type}`).join(', ')}.
            </Text>
          )}
        </>
      )}
    </Section>
  );
};

/**
 * The guards, drawn from what they have actually done. A guard that exists and has been asked
 * nothing is not proof of anything, which is why the sentence carries the total beside the rows:
 * two rows under a heading that says "guards" would otherwise read as the whole fifty-six.
 */
export const GuardsSection = ({ now }: { now: number }) => {
  const loaded = useGuards();

  return (
    <Section
      title="The guards, and what they have refused"
      blurb="Every guard in the estate, with how many times it was consulted and how many commands it refused. A guard that has never refused anything has not yet been tested by a real mistake, so this page separates guards that fired from guards that merely exist."
      testId="ops-guards-section"
    >
      {loaded.state === 'loading' && (
        <Waiting testId="ops-guards-loading">Reading the guard inventory.</Waiting>
      )}
      {loaded.state === 'error' && (
        <Unread testId="ops-guards-error" detail={loaded.error}>
          The guard inventory could not be read, so how many guards are in use is unknown.
        </Unread>
      )}
      {loaded.state === 'ready' && (
        <>
          <Text variant="body-medium" data-testid="ops-guards-sentence">
            {guardsSentence(loaded.guards)}
          </Text>
          {(guardsUnreadable(loaded.guards) ||
            guardRows(loaded.guards).length > 0) && (
            <Sheet testId="ops-guards-table">
              {guardRows(loaded.guards).map(g => (
                <Fact
                  key={g.id}
                  label={g.title}
                  value={
                    <>
                      <span data-testid={`ops-guard-id-${g.id}`}>{g.id}</span> — fired{' '}
                      <b>{g.fired}</b>, refused <b>{g.blocked}</b>
                      {g.last_command ? ` — ${g.last_command}` : ''}
                      {g.last_at ? ` (${ago(g.last_at, now)})` : ''}
                    </>
                  }
                  testId={`ops-guard-${g.id}`}
                />
              ))}
            </Sheet>
          )}
        </>
      )}
    </Section>
  );
};
