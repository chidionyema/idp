import { SchedulerServiceTaskScheduleDefinitionConfig } from '@backstage/backend-plugin-api';

export interface Config {
  catalog?: {
    projection?: {
      /**
       * The shell command that runs the projection and emits a JSON array of
       * Backstage entities to stdout. Defaults to `bin/catalog-projection --json .`.
       * @visibility backend
       */
      command: string;
      /**
       * How often to run the projection and re-derive the full set of entities.
       * @visibility backend
       */
      schedule: SchedulerServiceTaskScheduleDefinitionConfig;
      /**
       * Fallback owner for entities that name no owner in the projection.
       * Defaults to `group:default/platform`.
       * @visibility backend
       */
      fallbackOwner?: string;
      /**
       * Subprocess timeout in milliseconds. Defaults to 120000.
       * @visibility backend
       */
      timeout?: number;
    };
  };
}