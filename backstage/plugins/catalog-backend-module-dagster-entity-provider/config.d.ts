import { SchedulerServiceTaskScheduleDefinitionConfig } from '@backstage/backend-plugin-api';

export interface Config {
  catalog?: {
    providers?: {
      /**
       * Configuration for the Dagster entity provider (crew#468): every asset, job and
       * schedule Dagster knows about becomes a catalogue entity. Optional; a Backstage with
       * no `dagster` block here simply runs without it (no Dagster deployed yet).
       */
      dagster?: {
        /**
         * The Dagster GraphQL endpoint to poll, e.g. `${DAGSTER_GRAPHQL_URL:-...}` so no
         * host is ever a literal in this file (LAW 46).
         * @visibility backend
         */
        url: string;
        /**
         * How often to poll Dagster and re-derive the full set of entities.
         * @visibility backend
         */
        schedule: SchedulerServiceTaskScheduleDefinitionConfig;
      };
    };
  };
}
