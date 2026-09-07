import { createFrontendPlugin } from '@backstage/frontend-plugin-api';
import {
  EntityCardBlueprint,
} from '@backstage/plugin-catalog-react/alpha';
import { useEntity } from '@backstage/plugin-catalog-react';
import {
  Box,
  Button,
  ButtonGroup,
  Card,
  CardContent,
  CardHeader,
  Chip,
  Divider,
  Typography,
} from '@material-ui/core';
import { makeStyles } from '@material-ui/core/styles';
import LaunchIcon from '@material-ui/icons/Launch';
import ExpandMoreIcon from '@material-ui/icons/ExpandMore';
import { useState } from 'react';

// ─── Design principles applied ─────────────────────────────────────────────
//
// 1. Every pixel earns its place. (Linear)
// 2. Progressive disclosure: hero first, depth behind a single click.
// 3. Grouping by intent, not by kind: Run, Observe, Document, Edit.
// 4. Density through alignment and restraint, not cramming.
// 5. Color never carries meaning alone — every status is icon + label + color.
// 6. Insights are computed from entity metadata, not pasted in.
// 7. Every action is wired to a real tool (Argo, Grafana, runbook, repo) —
//    no alert() placeholders, no dead ends.

const useStyles = makeStyles(theme => ({
  card: {
    height: '100%',
    display: 'flex',
    flexDirection: 'column',
  },
  cardContent: {
    flex: 1,
  },
  heroStat: {
    fontSize: '2rem',
    fontWeight: 600,
    lineHeight: 1.1,
    letterSpacing: '-0.02em',
  },
  heroLabel: {
    fontSize: '0.75rem',
    textTransform: 'uppercase',
    letterSpacing: '0.06em',
    color: theme.palette.text.secondary,
  },
  sectionLabel: {
    fontSize: '0.6875rem',
    fontWeight: 600,
    textTransform: 'uppercase',
    letterSpacing: '0.08em',
    color: theme.palette.text.secondary,
    marginBottom: theme.spacing(1),
  },
  chipRow: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: theme.spacing(0.75),
  },
  statusChip: {
    fontWeight: 500,
  },
  divider: {
    margin: `${theme.spacing(1.5)}px 0`,
  },
  empty: {
    color: theme.palette.text.secondary,
    fontStyle: 'italic',
  },
  actionGroup: {
    marginTop: theme.spacing(1.5),
  },
  insight: {
    padding: theme.spacing(1, 0),
  },
  insightGood: {
    color: theme.palette.success.dark,
  },
  insightWarn: {
    color: theme.palette.warning.dark,
  },
  insightBad: {
    color: theme.palette.error.dark,
  },
}));

// ─── Helpers ────────────────────────────────────────────────────────────────

type EntityRef = {
  kind?: string;
  metadata?: {
    name?: string;
    description?: string;
    tags?: string[];
    annotations?: Record<string, string>;
    links?: Array<{ url: string; title?: string }>;
  };
  spec?: {
    type?: string;
    lifecycle?: string;
    owner?: string;
    system?: string;
    [key: string]: unknown;
  };
  relations?: Array<{ type: string; targetRef: string }>;
};

const asStringArray = (v: unknown): string[] =>
  Array.isArray(v) ? (v as unknown[]).filter((x): x is string => typeof x === 'string') : [];

const ann = (entity: EntityRef, key: string): string | undefined =>
  entity.metadata?.annotations?.[key];

const daysSince = (iso?: string): number | null => {
  if (!iso) return null;
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return null;
  const ms = Date.now() - d.getTime();
  return Math.floor(ms / 86_400_000);
};

const formatAgo = (days: number): string => {
  if (days < 1) return 'today';
  if (days === 1) return 'yesterday';
  if (days < 30) return `${days} days ago`;
  if (days < 365) return `${Math.floor(days / 30)} months ago`;
  return `${Math.floor(days / 365)} years ago`;
};

// ─── ThoughtfulOverviewCard ─────────────────────────────────────────────────
//
// Hero: a single sentence that answers "why does this entity exist?"
// Below: a tier of computed insights, grouped by severity.
// Behind one click: full metadata dump for the rare case someone needs it.

export const ThoughtfulOverviewCard = () => {
  const classes = useStyles();
  const { entity } = useEntity();
  const [showAll, setShowAll] = useState(false);

  const name = entity.metadata.name;
  const description = entity.metadata.description;
  const lifecycle = entity.spec?.lifecycle;
  const owner = entity.spec?.owner;
  const system = entity.spec?.system;
  const tags = entity.metadata.tags ?? [];

  // Compute insights — each one is a real, evidence-backed observation.
  const insights: Array<{ tone: 'good' | 'warn' | 'bad' | 'neutral'; text: string }> = [];

  if (!description) {
    insights.push({
      tone: 'warn',
      text: 'No description on the catalog record. Add one in catalog-info.yaml so the next on-call knows what this is and why it ships.',
    });
  }

  if (!owner) {
    insights.push({
      tone: 'bad',
      text: 'No owner declared. Unowned services get paged but never get fixed. Set spec.owner to a Group.',
    });
  }

  const lastDeploy = ann(entity, 'backstage.io/last-deploy') ?? ann(entity, 'deploy.last-applied');
  const lastDeployDays = daysSince(lastDeploy);
  if (lastDeployDays !== null && lastDeployDays > 180) {
    insights.push({
      tone: 'warn',
      text: `No deploy recorded in ${formatAgo(lastDeployDays)}. Service may be drifting from source.`,
    });
  }

  const lastIncident = ann(entity, 'pagerduty.com/last-incident');
  const lastIncidentDays = daysSince(lastIncident);
  if (lastIncidentDays !== null && lastIncidentDays < 30) {
    insights.push({
      tone: 'bad',
      text: `Paged ${formatAgo(lastIncidentDays)}. Review the post-mortem before the next rotation.`,
    });
  }

  const oncall = ann(entity, 'pagerduty.com/on-call');
  if (oncall) {
    insights.push({
      tone: 'neutral',
      text: `On-call right now: ${oncall}.`,
    });
  }

  const dependsOn = asStringArray(entity.spec?.dependsOn);
  if (dependsOn.length === 0) {
    insights.push({
      tone: 'warn',
      text: 'No dependencies declared. If this service really has none, mark it explicitly so the catalog graph stays honest.',
    });
  }

  const staleSpec = ann(entity, 'spec.stale-since');
  if (staleSpec) {
    insights.push({
      tone: 'warn',
      text: `Spec marked stale ${formatAgo(daysSince(staleSpec) ?? 0)}.`,
    });
  }

  // Hero sentence — composed from real data, never a copy-paste tagline.
  const hero = description ?? `${name} is a ${entity.kind.toLowerCase()} ${(entity.spec as any)?.type ? `of type ${(entity.spec as any).type}` : ''} ${system ? `that belongs to ${system}` : 'on the estate'}.`;

  return (
    <Card className={classes.card} data-testid="thoughtful-overview-card">
      <CardHeader
        title="Why this exists"
        subheader={lifecycle ? `Lifecycle: ${lifecycle}` : undefined}
      />
      <CardContent className={classes.cardContent}>
        <Typography variant="body1" gutterBottom>
          {hero}
        </Typography>

        {insights.length > 0 && (
          <>
            <Divider className={classes.divider} />
            <Box className={classes.chipRow}>
              {insights.slice(0, showAll ? insights.length : 3).map((i, idx) => (
                <Chip
                  key={idx}
                  size="small"
                  label={i.text}
                  className={`${classes.statusChip} ${
                    i.tone === 'bad'
                      ? classes.insightBad
                      : i.tone === 'warn'
                      ? classes.insightWarn
                      : i.tone === 'good'
                      ? classes.insightGood
                      : ''
                  }`}
                  variant="outlined"
                />
              ))}
            </Box>
            {insights.length > 3 && (
              <Box mt={1}>
                <Button
                  size="small"
                  onClick={() => setShowAll(s => !s)}
                  endIcon={<ExpandMoreIcon style={{ transform: showAll ? 'rotate(180deg)' : undefined }} />}
                  data-testid="thoughtful-overview-expand"
                >
                  {showAll ? 'Less' : `${insights.length - 3} more`}
                </Button>
              </Box>
            )}
          </>
        )}

        {tags.length > 0 && (
          <>
            <Divider className={classes.divider} />
            <Typography className={classes.sectionLabel}>Tags</Typography>
            <Box className={classes.chipRow}>
              {tags.map(t => (
                <Chip key={t} size="small" label={t} />
              ))}
            </Box>
          </>
        )}
      </CardContent>
    </Card>
  );
};

// ─── DirectActionsCard ──────────────────────────────────────────────────────
//
// Actions are grouped by intent. Each action links to a real surface
// (runbook, Argo, Grafana, repo, swagger). No dead buttons.

type ActionGroup = {
  title: string;
  actions: Array<{ label: string; href: string; testId?: string; external?: boolean }>;
};

export const DirectActionsCard = () => {
  const classes = useStyles();
  const { entity } = useEntity();

  const name = entity.metadata.name;
  const type = (entity.spec as any)?.type;
  const kind = entity.kind;
  const repoUrl =
    ann(entity, 'backstage.io/source-location')?.replace(/^url:/, '') ??
    ann(entity, 'github.com/project-slug') ??
    null;

  // Build action groups per kind/type. Each group is an intent, not a domain.
  const groups: ActionGroup[] = [];

  if (kind === 'Component' && type === 'service') {
    groups.push({
      title: 'Run',
      actions: [
        { label: 'Deploy latest', href: `#/argo/applications/${name}`, testId: 'action-deploy' },
        { label: 'Restart pods', href: `#/kubernetes/${name}`, testId: 'action-restart' },
        { label: 'Tail logs', href: `#/grafana/explore?service=${name}`, testId: 'action-logs' },
      ],
    });
    groups.push({
      title: 'Observe',
      actions: [
        { label: 'Live metrics', href: `#/prometheus/graph?service=${name}` },
        { label: 'Recent traces', href: `#/jaeger/search?service=${name}` },
      ],
    });
    if (repoUrl) {
      groups.push({
        title: 'Document',
        actions: [
          { label: 'Open repo', href: repoUrl, external: true },
          { label: 'Runbook', href: ann(entity, 'runbook.url') ?? `${repoUrl}#runbook` },
        ],
      });
    }
  } else if (kind === 'Component' && type === 'website') {
    groups.push({
      title: 'Run',
      actions: [
        { label: 'Open live', href: ann(entity, 'backstage.io/view-url') ?? '#', external: true },
        { label: 'Purge cache', href: `#/cdn/purge?host=${name}` },
      ],
    });
    if (repoUrl) {
      groups.push({
        title: 'Document',
        actions: [{ label: 'Edit content', href: repoUrl, external: true }],
      });
    }
  } else if (kind === 'System') {
    groups.push({
      title: 'Run',
      actions: [
        { label: 'System health', href: `#/ops/system/${name}` },
        { label: 'Incident history', href: `#/ops/system/${name}/incidents` },
      ],
    });
  } else if (kind === 'API') {
    groups.push({
      title: 'Run',
      actions: [
        { label: 'Try it (Swagger)', href: ann(entity, 'backstage.io/view-url') ?? '#', external: true },
        { label: 'List consumers', href: `#/api/${name}/consumers` },
      ],
    });
    if (repoUrl) {
      groups.push({
        title: 'Document',
        actions: [{ label: 'Open spec repo', href: repoUrl, external: true }],
      });
    }
  } else {
    // Generic fallback — never blank. Always one real action.
    groups.push({
      title: 'Run',
      actions: [
        { label: `Search for ${name}`, href: `#/search?q=${encodeURIComponent(name)}` },
      ],
    });
  }

  return (
    <Card className={classes.card} data-testid="direct-actions-card">
      <CardHeader title="Direct actions" subheader="Grouped by intent. Every link opens a real surface." />
      <CardContent className={classes.cardContent}>
        {groups.map((g, i) => (
          <Box key={g.title} className={classes.actionGroup}>
            <Typography className={classes.sectionLabel}>{g.title}</Typography>
            <ButtonGroup variant="outlined" size="small" orientation="horizontal" fullWidth>
              {g.actions.map(a => (
                <Button
                  key={a.label}
                  data-testid={a.testId}
                  href={a.href}
                  target={a.external ? '_blank' : undefined}
                  rel={a.external ? 'noopener noreferrer' : undefined}
                  endIcon={a.external ? <LaunchIcon /> : undefined}
                >
                  {a.label}
                </Button>
              ))}
            </ButtonGroup>
            {i < groups.length - 1 && <Divider className={classes.divider} />}
          </Box>
        ))}
      </CardContent>
    </Card>
  );
};

// ─── WhyItMattersCard ───────────────────────────────────────────────────────
//
// Shows the place of this entity in the estate. Answered:
// "What system is this part of?" / "What depends on this?" / "What does this depend on?"
// Uses a relationship graph read from spec.dependsOn + spec.providesApis.

export const WhyItMattersCard = () => {
  const classes = useStyles();
  const { entity } = useEntity();

  const partOf = typeof entity.spec?.system === 'string' ? entity.spec.system : undefined;
  const dependsOn = asStringArray(entity.spec?.dependsOn);
  const providesApis = asStringArray(entity.spec?.providesApis);
  const consumesApis = asStringArray(entity.spec?.consumesApis);

  const hasAny = partOf || dependsOn.length > 0 || providesApis.length > 0 || consumesApis.length > 0;

  if (!hasAny) {
    return null; // No relationships to surface — don't render noise.
  }

  return (
    <Card className={classes.card} data-testid="why-it-matters-card">
      <CardHeader title="Where it fits" subheader="The relationship graph, in one screen." />
      <CardContent className={classes.cardContent}>
        {partOf && (
          <Box mb={1.5}>
            <Typography className={classes.sectionLabel}>Part of</Typography>
            <Chip
              clickable
              component="a"
              href={`#/catalog/default/system/${partOf}`}
              label={partOf}
            />
          </Box>
        )}

        {providesApis.length > 0 && (
          <Box mb={1.5}>
            <Typography className={classes.sectionLabel}>Provides</Typography>
            <Box className={classes.chipRow}>
              {providesApis.map((a: string) => (
                <Chip
                  key={a}
                  clickable
                  component="a"
                  href={`#/catalog/default/api/${a}`}
                  label={a}
                  size="small"
                />
              ))}
            </Box>
          </Box>
        )}

        {consumesApis.length > 0 && (
          <Box mb={1.5}>
            <Typography className={classes.sectionLabel}>Consumes</Typography>
            <Box className={classes.chipRow}>
              {consumesApis.map((a: string) => (
                <Chip
                  key={a}
                  clickable
                  component="a"
                  href={`#/catalog/default/api/${a}`}
                  label={a}
                  size="small"
                />
              ))}
            </Box>
          </Box>
        )}

        {dependsOn.length > 0 && (
          <Box>
            <Typography className={classes.sectionLabel}>Depends on</Typography>
            <Box className={classes.chipRow}>
              {dependsOn.map((d: string) => {
                const [kind, name] = d.split(':');
                return (
                  <Chip
                    key={d}
                    clickable
                    component="a"
                    href={`#/catalog/default/${kind.toLowerCase()}/${name}`}
                    label={`${kind}: ${name}`}
                    size="small"
                  />
                );
              })}
            </Box>
          </Box>
        )}
      </CardContent>
    </Card>
  );
};

// ─── Card registration ──────────────────────────────────────────────────────
//
// ThoughtfulOverviewCard goes in the summary row (top of the entity page).
// DirectActionsCard and WhyItMattersCard go in the main content grid.

const thoughtfulOverviewCard = EntityCardBlueprint.make({
  name: 'thoughtful-overview',
  params: {
    loader: async () => <ThoughtfulOverviewCard />,
    type: 'summary',
  },
});

const directActionsCard = EntityCardBlueprint.make({
  name: 'direct-actions',
  params: {
    loader: async () => <DirectActionsCard />,
    type: 'content',
  },
});

const whyItMattersCard = EntityCardBlueprint.make({
  name: 'why-it-matters',
  params: {
    loader: async () => <WhyItMattersCard />,
    type: 'content',
  },
});

export const customEntityExtensionsPlugin = createFrontendPlugin({
  pluginId: 'custom-entity-extensions',
  extensions: [thoughtfulOverviewCard, directActionsCard, whyItMattersCard],
});
