import {
  coreServices,
  createBackendModule,
  readSchedulerServiceTaskScheduleDefinitionFromConfig,
} from '@backstage/backend-plugin-api';
import { catalogProcessingExtensionPoint } from '@backstage/plugin-catalog-node';
import { DagsterEntityProvider } from './DagsterEntityProvider';

export { DagsterEntityProvider } from './DagsterEntityProvider';
export { dagsterResponseToEntities } from './mapping';
export { DAGSTER_ENTITIES_QUERY, fetchDagsterEntities } from './dagsterClient';

/**
 * Registers the Dagster entity provider with the catalog backend (crew#468 CP2). Read by
 * `packages/backend/src/index.ts` via `backend.add(...)`.
 */
export const catalogModuleDagsterEntityProvider = createBackendModule({
  pluginId: 'catalog',
  moduleId: 'dagster-entity-provider',
  register(reg) {
    reg.registerInit({
      deps: {
        catalog: catalogProcessingExtensionPoint,
        config: coreServices.rootConfig,
        logger: coreServices.logger,
        scheduler: coreServices.scheduler,
      },
      async init({ catalog, config, logger, scheduler }) {
        // Optional, not required: Dagster runs on the founder's laptop today (bin/scheduler-up)
        // and has no in-cluster deployment yet (crew#468 CP2). A production Backstage with no
        // DAGSTER_GRAPHQL_URL set must still start; it just carries no Dagster entities.
        const providerConfig = config.getOptionalConfig('catalog.providers.dagster');
        if (!providerConfig) {
          logger.info(
            'catalog.providers.dagster is not configured; skipping the Dagster entity provider',
          );
          return;
        }
        const taskRunner = scheduler.createScheduledTaskRunner(
          readSchedulerServiceTaskScheduleDefinitionFromConfig(
            providerConfig.getConfig('schedule'),
          ),
        );
        const provider = DagsterEntityProvider.fromConfig(providerConfig, {
          logger,
          scheduler: taskRunner,
        });
        catalog.addEntityProvider(provider);
      },
    });
  },
});

export default catalogModuleDagsterEntityProvider;
