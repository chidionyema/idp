import {
  LoggerService,
  SchedulerServiceTaskRunner,
} from '@backstage/backend-plugin-api';
import { Config } from '@backstage/config';
import { EntityProvider, EntityProviderConnection } from '@backstage/plugin-catalog-node';
import { fetchDagsterEntities } from './dagsterClient';
import { dagsterResponseToEntities } from './mapping';

const DEFAULT_OWNER = 'group:default/platform';

/**
 * Polls Dagster's GraphQL API on the schedule configured under
 * `catalog.providers.dagster.schedule` and turns every asset, job and schedule into a catalogue
 * entity (crew#468). One provider, one full mutation per run: Dagster is the source of truth, so
 * a run that no longer sees an asset removes its entity rather than leaving it stale.
 */
export class DagsterEntityProvider implements EntityProvider {
  private connection?: EntityProviderConnection;

  /** `providerConfig` is the `catalog.providers.dagster` sub-config, already sliced by the
   * caller so this class never re-derives the config path (LAW 46: no literal path repeated). */
  static fromConfig(
    providerConfig: Config,
    options: { logger: LoggerService; scheduler: SchedulerServiceTaskRunner },
  ): DagsterEntityProvider {
    const url = providerConfig.getString('url');
    const fallbackOwner = providerConfig.getOptionalString('fallbackOwner') ?? DEFAULT_OWNER;
    return new DagsterEntityProvider(url, fallbackOwner, options.logger, options.scheduler);
  }

  constructor(
    private readonly graphqlUrl: string,
    private readonly fallbackOwner: string,
    private readonly logger: LoggerService,
    private readonly taskRunner: SchedulerServiceTaskRunner,
  ) {}

  getProviderName(): string {
    return 'dagster-entity-provider';
  }

  async connect(connection: EntityProviderConnection): Promise<void> {
    this.connection = connection;
    await this.taskRunner.run({
      id: this.getProviderName(),
      fn: async () => {
        await this.run();
      },
    });
  }

  async run(): Promise<void> {
    if (!this.connection) {
      throw new Error(`${this.getProviderName()} run before connect`);
    }
    this.logger.info(`Polling Dagster GraphQL API at ${this.graphqlUrl}`);
    const response = await fetchDagsterEntities(this.graphqlUrl);
    const entities = dagsterResponseToEntities(response, {
      fallbackOwner: this.fallbackOwner,
      sourceLocation: `url:${this.graphqlUrl}`,
    });
    await this.connection.applyMutation({
      type: 'full',
      entities: entities.map(entity => ({
        entity,
        locationKey: this.getProviderName(),
      })),
    });
    this.logger.info(`Dagster entity provider emitted ${entities.length} entities`);
  }
}
