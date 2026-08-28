/**
 * Shapes returned by the Dagster GraphQL API (docs.dagster.io/api/graphql), trimmed to the
 * fields the query in dagsterClient.ts asks for. Dagster's own API docs warn the schema is not
 * frozen, so this stays a narrow slice rather than the generated SDK.
 */

/** An asset node, from `assetNodes`. `owners` holds either an email or `team:<name>` (Dagster
 * convention: docs.dagster.io/api/graphql, AssetNode.owners). */
export interface DagsterAssetNode {
  id: string;
  assetKey: { path: string[] };
  dependencyKeys: { path: string[] }[];
  owners: string[];
  groupName: string | null;
  description: string | null;
}

/** One schedule, from a repository's `schedules` field. */
export interface DagsterSchedule {
  name: string;
  cronSchedule: string;
  pipelineName: string;
  description: string | null;
}

/** One job (`pipelines` in the GraphQL schema; Dagster jobs are pipelines under the hood). */
export interface DagsterJob {
  name: string;
  description: string | null;
}

export interface DagsterRepositoryNode {
  name: string;
  location: { name: string };
  jobs: DagsterJob[];
  schedules: DagsterSchedule[];
}

export interface DagsterGraphQLResponse {
  data: {
    assetNodes: DagsterAssetNode[];
    repositoriesOrError: {
      nodes: DagsterRepositoryNode[];
    };
  };
}
