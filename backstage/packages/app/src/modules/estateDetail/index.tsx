// The owned estate entity overview (founder, on the portal redesign: "clicking needs more
// detail and overview"). Before this every catalogue click landed on the stock Backstage
// generic Overview tab, which renders type/owner/description and little else -- so a founder
// or a buyer's engineer clicking an estate Resource or System saw no finer estate state, and
// anything whose home was a GitHub link stayed a dead-end in a new tab.
//
// This registers a first-class "Estate" content tab on the entity page (new frontend system,
// via the same EntityContentBlueprint the shipped metrics module already uses) for every
// estate-generated entity that carries at least one generated `estate/*` annotation. It
// renders the facts bin/catalog-gen actually wrote on the entity: kind/type, the generated
// status/rows/port/coupling annotations, its System and Owner relations, and every metadata
// link -- so the click-through IS the overview, not a link to somewhere else.

import { Entity } from '@backstage/catalog-model';
import { useEntity, useRelatedEntities } from '@backstage/plugin-catalog-react';
import { EntityContentBlueprint } from '@backstage/plugin-catalog-react/alpha';
// The estate's own reader helpers, kept pure and React-free in home/estate; the hand-authored
// founder-surface/component the health poller reaches carries estate/health + checked-at, and
// this page says, in the same state words the home uses, whether the thing is running.
import { HEALTH_LABEL, checkedAgo, healthOf } from '../home/estate';
import Box from '@material-ui/core/Box';
import Card from '@material-ui/core/Card';
import CardContent from '@material-ui/core/CardContent';
import Chip from '@material-ui/core/Chip';
import Grid from '@material-ui/core/Grid';
import Link from '@material-ui/core/Link';
import Typography from '@material-ui/core/Typography';

/** A generated entity carries at least one estate/* annotation (bin/catalog-gen writes
 * `estate/<field>` for every real estate row). */
const isEstateGenerated = (entity: Entity) =>
  Boolean(entity.metadata.annotations) &&
  Object.keys(entity.metadata.annotations ?? {}).some(a => a.startsWith('estate/'));

/** A catalogue Component: in this catalogue a component is the estate's own hand-authored
 * founder-surface, platform layer, or platform service - an estate citizen the estate can author
 * an overview for (founder fifth note: a hand surface with only the well-known backstage keys
 * still needs a click-through that is more than the stock stub), whether or not the live probe
 * has yet stamped it with estate/health. */
const isComponent = (entity: Entity) => entity.kind.toLowerCase() === 'component';

/** Fact names worth showing first, in a stable order, mapped to a human label. */
const FACT_LABEL: Record<string, string> = {
  'estate/kind': 'Kind',
  'estate/rows': 'Rows',
  'estate/mb': 'Size',
  'estate/referenced': 'Referenced',
  'estate/coupling': 'Coupling',
  'estate/last-status': 'Last status',
  'estate/fired-24h': 'Fired 24h',
  'estate/refused-24h': 'Refused 24h',
  'estate/age-h': 'Age (h)',
  'estate/max-age-days': 'Max age (days)',
  'estate/stale': 'Stale',
  'estate/health': 'Health',
  'estate/image': 'Image',
  'estate/port': 'Port',
  'estate/bind': 'Bind',
  'estate/process': 'Process',
  'estate/loaded': 'Loaded',
  'estate/interval-s': 'Interval (s)',
};
const PREFERRED = Object.keys(FACT_LABEL);
const HEALTH_CHECKED = 'estate/health-checked-at';
const HEALTH = 'estate/health';

/** A generated annotation key -> readable column label. Unknown estate/ fields are shown
 * under their raw key with dashes and the estate/ prefix stripped. */
const displayLabel = (key: string) =>
  FACT_LABEL[key] ?? key.replace('estate/', '').replace(/-/g, ' ');

/** Turn a Backstage ref (`kind:namespace/name`, `namespace/name` or bare `name`) into an
 * in-catalogue deep link, so the Belongs-to card takes a person from one entity to the next
 * without leaving the portal (directive 4's dead-end-GitHub-link gap, in reverse). */
const formatRefLink = (ref: string, defaultKind: string, label?: string) => {
  const kindRaw = ref.includes(':') ? ref.slice(0, ref.indexOf(':')) : defaultKind;
  const rest = ref.includes(':') ? ref.slice(ref.indexOf(':') + 1) : ref;
  const [ns, name] = rest.includes('/') ? rest.split('/') : ['default', rest];
  const href = `/catalog/${kindRaw.toLowerCase()}/${ns ? ns : 'default'}/${name}`;
  return <Link href={href}>{label ?? name}</Link>;
};

const NeighboursCard = () => {
  const { entity } = useEntity();
  const depends = useRelatedEntities(entity, { type: 'dependsOn' });
  const usedBy = useRelatedEntities(entity, { type: 'dependencyOf' });
  // Both families are read together, so one round of fetching decides the card's state.
  const loading = depends.loading ?? usedBy.loading;
  const error = depends.error ?? usedBy.error;
  const pairs: { label: string; list: Entity[] }[] = [
    { label: 'It depends on', list: depends.entities ?? [] },
    { label: 'Used by', list: usedBy.entities ?? [] },
  ];
  const shown = pairs.filter(p => p.list.length > 0);
  if (loading) {
    return (
      <Card variant="outlined">
        <CardContent>
          <Typography variant="overline">What it talks to</Typography>
          <Typography variant="body2" color="textSecondary">
            Reading its catalogue relations…
          </Typography>
        </CardContent>
      </Card>
    );
  }
  // When the catalogue could not be read, that is not the same as "nothing is wired" -
  // claiming the graph is empty because we could not ask it would be exactly the invention
  // rule 13 forbids, so the card says the real thing: it could not tell.
  if (error) {
    return (
      <Card variant="outlined">
        <CardContent>
          <Typography variant="overline">What it talks to</Typography>
          <Typography variant="body2" color="textSecondary">
            The catalogue did not answer; who this talks to is not shown.
          </Typography>
        </CardContent>
      </Card>
    );
  }
  // Zero relations is a real read-back: the graph genuinely names no neighbour. Stated
  // plainly, never wired to something the graph does not vouch for.
  if (shown.length === 0) {
    return (
      <Card variant="outlined">
        <CardContent>
          <Typography variant="overline">What it talks to</Typography>
          <Typography variant="body2" color="textSecondary">
            Nothing else in the catalogue is wired to it yet.
          </Typography>
        </CardContent>
      </Card>
    );
  }
  return (
    <Card variant="outlined">
      <CardContent>
        <Typography variant="overline">What it talks to</Typography>
        {shown.map(pair => (
          <Box key={pair.label} my={1}>
            <Typography variant="body2">{pair.label}</Typography>
            {pair.list.map(e => {
              const s = e.spec as { type?: unknown } | undefined;
              const t = typeof s?.type === 'string' ? s.type : undefined;
              const kind = e.kind.toLowerCase();
              const ref = `${kind}:${e.metadata.namespace ?? 'default'}/${e.metadata.name}`;
              const shownName = e.metadata.title ?? e.metadata.name;
              const label = `${shownName}${t ? ` - ${t}` : ''}`;
              return (
                <Typography variant="body2" key={ref}>
                  {formatRefLink(ref, kind, label)}
                </Typography>
              );
            })}
          </Box>
        ))}
      </CardContent>
    </Card>
  );
};

export const EstateOverview = ({ now }: { now?: number }) => {
  const { entity } = useEntity();
  if (!entity) return null;
  const md = entity.metadata;
  const ann = (md.annotations ?? {}) as Record<string, string>;
  const spec = (entity.spec ?? {}) as Record<string, unknown>;
  const systemRef = typeof spec.system === 'string' ? spec.system : '';
  const ownerRef = typeof spec.owner === 'string' ? spec.owner : '';
  // Does the estate's health poller speak about this catalogue entry? A hand-authored,
  // home-routed founder-surface or component the poller reaches carries a live verdict
  // (estate/health) even though it has none of the generated estate/<fact> block (a Resource
  // stacked in a system is not itself the live thing being probed, so it keeps only its
  // generated facts). `now` is trapped for deterministic tests; unset means wall-clock.
  const kind = entity.kind.toLowerCase();
  const live = kind === 'component' && typeof ann[HEALTH] === 'string' && ann[HEALTH] !== '';
  const at = now ?? Date.now();
  const healthWord = live ? HEALTH_LABEL[healthOf(entity, at)] : null;
  // Only when the poller recorded a checked time do we say how long ago; a never-checked thing
  // carries no stale claim (rule 13: no invented age).
  const recency = live && typeof ann[HEALTH_CHECKED] === 'string' ? checkedAgo(entity, at) : null;
  // The estate facts that matter, in the generator's own preferred order first, then any
  // remaining generated facts, excluding the machine-only health-checked timestamp.
  const factKeys = PREFERRED.filter(k => ann[k] !== undefined && ann[k] !== '')
    .concat(
      Object.keys(ann)
        .filter(k => k.startsWith('estate/') && !PREFERRED.includes(k) && k !== HEALTH_CHECKED)
        .sort(),
    );
  const tags = md.tags ?? [];
  const links = (md.links ?? []) as { url: string; title: string }[];
  return (
    <Box data-testid="estate-overview">
      <Grid container spacing={2}>
        <Grid item xs={12} md={7}>
          <Card variant="outlined">
            <CardContent>
              <Typography component="h2" gutterBottom>
                {md.title ?? md.name}
              </Typography>
              {typeof spec.type === 'string' && spec.type && (
                <Typography variant="body2" color="textSecondary">
                  Type: {spec.type}
                </Typography>
              )}
              {md.description && (
                <Typography variant="body2" color="textSecondary" gutterBottom>
                  {md.description}
                </Typography>
              )}
              {live && healthWord && (
                <Box my={1}>
                  <Typography variant="body2">
                    <span>{healthWord}</span>
                    {recency && <span>, {recency}</span>}
                  </Typography>
                </Box>
              )}
              {tags.length > 0 && (
                <Box my={1}>
                  {tags.map(t => (
                    <Chip key={t} size="small" label={t} style={{ marginRight: 4 }} />
                  ))}
                </Box>
              )}
              {factKeys.length > 0 && (
                <Grid container spacing={1} style={{ marginTop: 6 }}>
                  {factKeys.map(k => (
                    <Grid item xs={6} sm={4} key={k}>
                      <Typography variant="caption" color="textSecondary" display="block">
                        {displayLabel(k)}
                      </Typography>
                      <Typography variant="body2">{ann[k]}</Typography>
                    </Grid>
                  ))}
                </Grid>
              )}
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={5}>
          {systemRef.length + ownerRef.length > 0 && (
            <Card variant="outlined">
              <CardContent>
                <Typography variant="overline">Belongs to</Typography>
                {systemRef && (
                  <Typography variant="body2">System {formatRefLink(systemRef, 'system')}</Typography>
                )}
                {ownerRef && (
                  <Typography variant="body2">Owner {formatRefLink(ownerRef, 'group')}</Typography>
                )}
              </CardContent>
            </Card>
          )}
          {/* What it talks to: real catalogue relations, both directions. */}
          <NeighboursCard />
          {links.length > 0 && (
            <Card variant="outlined">
              <CardContent>
                <Typography variant="overline">Where it lives</Typography>
                {links.map((l, i) => (
                  <Typography variant="body2" key={`${l.title ?? 'link'}-${i}`}>
                    <Link href={l.url} target="_blank" rel="noopener noreferrer">
                      {l.title ?? l.url}
                    </Link>
                  </Typography>
                ))}
              </CardContent>
            </Card>
          )}
        </Grid>
      </Grid>
    </Box>
  );
};

// The Estate tab is every catalogue Component (a founder-surface, platform layer, or service -
// estate citizens a person clicks on the home and the estate should answer for, even when the
// live probe has not yet stamped them) PLUS any generated estate row (a Resource/System in the
// catalogue, e.g. a ledger that carries estate/* facts). Stock data that carries no estate
// meaning is not this tab's subject.
const isEstateSubject = (entity: Entity) =>
  isEstateGenerated(entity) || isComponent(entity);

const estateOverviewContent = EntityContentBlueprint.make({
  name: 'estate-overview',
  params: {
    path: '/estate',
    title: 'Estate',
    filter: isEstateSubject,
    loader: async () => <EstateOverview />,
  },
});

// Registered onto the catalog plugin, alongside the namespace filter module, so the tab lands
// on every entity page without touching stock Backstage internals.
import { createFrontendModule } from '@backstage/frontend-plugin-api';

export const estateDetailModule = createFrontendModule({
  pluginId: 'catalog',
  extensions: [estateOverviewContent],
});
