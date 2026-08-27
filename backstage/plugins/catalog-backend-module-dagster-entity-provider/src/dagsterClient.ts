import { DagsterGraphQLResponse } from './types';

/**
 * Minimal query for crew#468: asset lineage and ownership, plus every job and schedule per
 * repository. Field names follow docs.dagster.io/api/graphql (AssetNode, RepositoryConnection);
 * `jobs` is aliased from `pipelines`, which is the field Dagster's schema actually exposes.
 */
export const DAGSTER_ENTITIES_QUERY = `
  query BackstageCatalogEntities {
    assetNodes {
      id
      assetKey { path }
      dependencyKeys { path }
      owners
      groupName
      description
    }
    repositoriesOrError {
      ... on RepositoryConnection {
        nodes {
          name
          location { name }
          jobs: pipelines {
            name
            description
          }
          schedules {
            name
            cronSchedule
            pipelineName
            description
          }
        }
      }
    }
  }
`;

/**
 * Executes the query against Dagster's GraphQL endpoint. Node 22 (this repo's minimum, see
 * backstage/package.json engines) ships global fetch, so no HTTP client dependency is added
 * (LAW 43: the runtime already does this).
 */
export async function fetchDagsterEntities(
  graphqlUrl: string,
): Promise<DagsterGraphQLResponse> {
  const res = await fetch(graphqlUrl, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ query: DAGSTER_ENTITIES_QUERY }),
  });
  if (!res.ok) {
    throw new Error(
      `Dagster GraphQL request to ${graphqlUrl} failed: ${res.status} ${res.statusText}`,
    );
  }
  const body = (await res.json()) as DagsterGraphQLResponse;
  if (!body?.data) {
    throw new Error(`Dagster GraphQL response from ${graphqlUrl} carried no data`);
  }
  return body;
}
