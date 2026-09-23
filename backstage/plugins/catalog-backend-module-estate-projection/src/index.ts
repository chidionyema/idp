import {
  coreServices,
  createBackendModule,
  readSchedulerServiceTaskScheduleDefinitionFromConfig,
} from '@backstage/backend-plugin-api';
import { catalogProcessingExtensionPoint } from '@backstage/plugin-catalog-node';
import { EstateProjectionEntityProvider } from './EstateProjectionEntityProvider';

/**
 * Registers the estate projection entity provider with the catalog backend
 * (crew#740 CP6). Read by `packages/backend/src/index.ts` via `backend.add(...)`.
 *
 * Optional: a Backstage with no `catalog.projection` block here starts without
 * error; it simply carries no projection entities. The projection is a pure
 * function over source and cannot drift from the code, so a missing config is
 * not a broken-catalog condition.
 */
export const catalogModuleEstateProjectionEntityProvider = createBackendModule({
  pluginId: 'catalog',
  moduleId: 'estate-projection-entity-provider',
  register(reg) {
    reg.registerInit({
      deps: {
        catalog: catalogProcessingExtensionPoint,
        config: coreServices.rootConfig,
        logger: coreServices.logger,
        scheduler: coreServices.scheduler,
      },
      async init({ catalog, config, logger, scheduler }) {
        const providerConfig = config.getOptionalConfig('catalog.projection');
        if (!providerConfig) {
          logger.info(
            'catalog.projection is not configured; skipping the estate projection entity provider',
          );
          return;
        }
        const taskRunner = scheduler.createScheduledTaskRunner(
          readSchedulerServiceTaskScheduleDefinitionFromConfig(
            providerConfig.getConfig('schedule'),
          ),
        );
        const provider = EstateProjectionEntityProvider.fromConfig(providerConfig, {
          logger,
          scheduler: taskRunner,
        });
        catalog.addEntityProvider(provider);
      },
    });
  },
});

export { EstateProjectionEntityProvider } from './EstateProjectionEntityProvider';
export { estateProjectionResponseToEntities } from './mapping';