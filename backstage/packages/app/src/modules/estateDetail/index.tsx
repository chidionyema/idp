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
import { useEntity } from '@backstage/plugin-catalog-react';
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
 * `estate/<field>` for every real estate row; a hand-authored founder/platform component has
 * the well-known backstage keys but none of ours, so it is not this tab's subject). */
const isEstateGenerated = (entity: Entity) =>
  Boolean(entity.metadata.annotations) &&
  Object.keys(entity.metadata.annotations ?? {}).some(a => a.startsWith('estate/'));

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
const formatRefLink = (ref: string, defaultKind: string) => {
  const kindRaw = ref.includes(':') ? ref.slice(0, ref.indexOf(':')) : defaultKind;
  const rest = ref.includes(':') ? ref.slice(ref.indexOf(':') + 1) : ref;
  const [ns, name] = rest.includes('/') ? rest.split('/') : ['default', rest];
  const href = `/catalog/${kindRaw.toLowerCase()}/${ns ? ns : 'default'}/${name}`;
  return <Link href={href}>{name}</Link>;
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

// The tab is a component of the catalogue: a probed founder-surface (a Component the estate's
// health probe stamped estate/health + checked-at onto, via bin/catalog-gen) or any generated
// estate-ledger row carries at least one estate/* annotation, so it appears. A hand-authored
// entity with only the well-known backstage keys is not this tab's subject.
const estateOverviewContent = EntityContentBlueprint.make({
  name: 'estate-overview',
  params: {
    path: '/estate',
    title: 'Estate',
    filter: isEstateGenerated,
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
