import { Entity } from '@backstage/catalog-model';
import {
  DagsterAssetNode,
  DagsterGraphQLResponse,
  DagsterRepositoryNode,
} from './types';

/** Options that do not come from the GraphQL response itself. */
export interface MappingOptions {
  /** `group:default/platform`-style ref, used when Dagster names no owner (crew#468). */
  fallbackOwner: string;
  /** Annotation value naming where these entities came from, for the entity inspector. */
  sourceLocation: string;
}

const ASSET_KIND = 'Component';
const JOB_KIND = 'Component';
const SCHEDULE_KIND = 'Resource';

/** Backstage entity names: `^[a-zA-Z0-9][a-zA-Z0-9_.-]*$`, max 63 characters
 * (backstage.io/docs/features/software-catalog/descriptor-format#name-format). */
function slug(parts: string[]): string {
  const joined = parts
    .join('-')
    .toLowerCase()
    .replace(/[^a-z0-9-_.]+/g, '-')
    .replace(/-+/g, '-')
    .replace(/^-|-$/g, '');
  return joined.slice(0, 63).replace(/^[-_.]+/, '') || 'unnamed';
}

export function assetEntityName(assetKeyPath: string[]): string {
  return slug(['dagster-asset', ...assetKeyPath]);
}

export function jobEntityName(jobName: string): string {
  return slug(['dagster-job', jobName]);
}

export function scheduleEntityName(scheduleName: string): string {
  return slug(['dagster-schedule', scheduleName]);
}

/** Dagster owner strings are either an email or `team:<name>` (docs.dagster.io/api/graphql,
 * AssetNode.owners). Falls back to the platform group when Dagster names nobody, matching the
 * fallback `bin/catalog-gen` uses for every other generated entity. */
function ownerRef(owners: string[], fallbackOwner: string): string {
  const first = owners[0];
  if (!first) return fallbackOwner;
  if (first.startsWith('team:')) {
    return `group:default/${slug([first.slice('team:'.length)])}`;
  }
  const localPart = first.split('@')[0];
  return `user:default/${slug([localPart])}`;
}

function assetToEntity(
  node: DagsterAssetNode,
  opts: MappingOptions,
): Entity {
  const name = assetEntityName(node.assetKey.path);
  return {
    apiVersion: 'backstage.io/v1alpha1',
    kind: ASSET_KIND,
    metadata: {
      name,
      title: node.assetKey.path.join('/'),
      description: node.description ?? `Dagster asset ${node.assetKey.path.join('/')}`,
      annotations: {
        'backstage.io/managed-by-location': opts.sourceLocation,
        'backstage.io/managed-by-origin-location': opts.sourceLocation,
        'dagster.io/asset-key': node.assetKey.path.join('/'),
      },
      tags: node.groupName ? [slug([node.groupName])] : undefined,
    },
    spec: {
      type: 'dagster-asset',
      lifecycle: 'production',
      owner: ownerRef(node.owners, opts.fallbackOwner),
      dependsOn: node.dependencyKeys.map(
        dep => `component:default/${assetEntityName(dep.path)}`,
      ),
    },
  };
}

function jobToEntity(
  repo: DagsterRepositoryNode,
  jobName: string,
  description: string | null,
  opts: MappingOptions,
): Entity {
  const name = jobEntityName(jobName);
  return {
    apiVersion: 'backstage.io/v1alpha1',
    kind: JOB_KIND,
    metadata: {
      name,
      title: jobName,
      description: description ?? `Dagster job ${jobName} in ${repo.name}`,
      annotations: {
        'backstage.io/managed-by-location': opts.sourceLocation,
        'backstage.io/managed-by-origin-location': opts.sourceLocation,
        'dagster.io/repository': repo.name,
        'dagster.io/job-name': jobName,
      },
    },
    spec: {
      type: 'dagster-job',
      lifecycle: 'production',
      owner: opts.fallbackOwner,
    },
  };
}

function scheduleToEntity(
  repo: DagsterRepositoryNode,
  schedule: DagsterRepositoryNode['schedules'][number],
  opts: MappingOptions,
): Entity {
  const name = scheduleEntityName(schedule.name);
  return {
    apiVersion: 'backstage.io/v1alpha1',
    kind: SCHEDULE_KIND,
    metadata: {
      name,
      title: schedule.name,
      description:
        schedule.description ?? `Dagster schedule ${schedule.name} (${schedule.cronSchedule})`,
      annotations: {
        'backstage.io/managed-by-location': opts.sourceLocation,
        'backstage.io/managed-by-origin-location': opts.sourceLocation,
        'dagster.io/repository': repo.name,
        'dagster.io/cron-schedule': schedule.cronSchedule,
      },
    },
    spec: {
      type: 'dagster-schedule',
      owner: opts.fallbackOwner,
      dependsOn: [`component:default/${jobEntityName(schedule.pipelineName)}`],
    },
  };
}

/**
 * Pure GraphQL-JSON -> Entity[] mapping (crew#468 CP1). No network, no config, no scheduler: the
 * whole point is that this function is tested against a recorded fixture
 * (tests/test_incident_crew468_dagster_entities_from_fixture.py and mapping.test.ts) with no
 * socket ever opened.
 */
export function dagsterResponseToEntities(
  response: DagsterGraphQLResponse,
  opts: MappingOptions,
): Entity[] {
  const assets = response.data.assetNodes.map(node => assetToEntity(node, opts));

  const jobs: Entity[] = [];
  const schedules: Entity[] = [];
  for (const repo of response.data.repositoriesOrError.nodes) {
    for (const job of repo.jobs) {
      jobs.push(jobToEntity(repo, job.name, job.description, opts));
    }
    for (const schedule of repo.schedules) {
      schedules.push(scheduleToEntity(repo, schedule, opts));
    }
  }

  return [...assets, ...jobs, ...schedules];
}
