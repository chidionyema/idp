/**
 * Incident test for crew#468: before this provider existed, every Dagster asset, job and
 * schedule needed a hand-written catalog-info.yaml, which drifted the moment the pipeline
 * changed. Rule: the mapping from Dagster's GraphQL JSON to catalogue entities is a pure
 * function, proved against a recorded fixture, with no socket ever opened (rung 4).
 */
import fs from 'fs';
import path from 'path';
import {
  assetEntityName,
  dagsterResponseToEntities,
  jobEntityName,
  scheduleEntityName,
} from './mapping';
import { DagsterGraphQLResponse } from './types';

const OPTS = {
  fallbackOwner: 'group:default/platform',
  sourceLocation: 'url:http://dagster.example.internal/graphql',
};

describe('dagsterResponseToEntities (crew#468)', () => {
  const originalFetch = global.fetch;

  beforeEach(() => {
    // The mapping is pure: proves rung 4 never opens a socket by making any fetch a hard failure.
    global.fetch = jest.fn(() => {
      throw new Error('mapping.ts must never call fetch');
    }) as unknown as typeof fetch;
  });

  afterEach(() => {
    global.fetch = originalFetch;
  });

  const fixturePath = path.join(__dirname, '..', '__fixtures__', 'dagster-response.json');
  const response = JSON.parse(
    fs.readFileSync(fixturePath, 'utf8'),
  ) as DagsterGraphQLResponse;

  it('emits one Component per asset, one Component per job, one Resource per schedule', () => {
    const entities = dagsterResponseToEntities(response, OPTS);
    const byKind = (kind: string) => entities.filter(e => e.kind === kind);

    expect(byKind('Component').length).toBe(3 /* assets */ + 1 /* job */);
    expect(byKind('Resource').length).toBe(1 /* schedule */);
    expect(entities).toHaveLength(5);
  });

  it('carries dependsOn from Dagster asset lineage', () => {
    const entities = dagsterResponseToEntities(response, OPTS);
    const cleaned = entities.find(
      e => e.metadata.name === assetEntityName(['warehouse', 'orders_cleaned']),
    );
    expect(cleaned?.spec?.dependsOn).toEqual([
      `component:default/${assetEntityName(['warehouse', 'raw_orders'])}`,
    ]);
  });

  it('resolves owner from a Dagster team owner', () => {
    const entities = dagsterResponseToEntities(response, OPTS);
    const rawOrders = entities.find(
      e => e.metadata.name === assetEntityName(['warehouse', 'raw_orders']),
    );
    expect(rawOrders?.spec?.owner).toBe('group:default/data-platform');
  });

  it('resolves owner from a Dagster user owner email', () => {
    const entities = dagsterResponseToEntities(response, OPTS);
    const cleaned = entities.find(
      e => e.metadata.name === assetEntityName(['warehouse', 'orders_cleaned']),
    );
    expect(cleaned?.spec?.owner).toBe('user:default/ada');
  });

  it('falls back to the platform group when Dagster names no owner', () => {
    const entities = dagsterResponseToEntities(response, OPTS);
    const snapshot = entities.find(
      e => e.metadata.name === assetEntityName(['catalogue', 'entity_snapshot']),
    );
    expect(snapshot?.spec?.owner).toBe('group:default/platform');
  });

  it('emits a Resource per schedule that depends on its job', () => {
    const entities = dagsterResponseToEntities(response, OPTS);
    const schedule = entities.find(
      e => e.metadata.name === scheduleEntityName('reconcile_catalogue_hourly'),
    );
    expect(schedule?.kind).toBe('Resource');
    expect(schedule?.spec?.dependsOn).toEqual([
      `component:default/${jobEntityName('reconcile_catalogue')}`,
    ]);
  });
});
