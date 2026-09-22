import {
  LoggerService,
  SchedulerServiceTaskRunner,
} from '@backstage/backend-plugin-api';
import { Config } from '@backstage/config';
import { EntityProvider, EntityProviderConnection } from '@backstage/plugin-catalog-node';
import { execFile } from 'child_process';
import { estateProjectionResponseToEntities } from './mapping';

const DEFAULT_OWNER = 'group:default/platform';

/**
 * Polls the estate projection on the schedule configured under
 * `catalog.projection.schedule` and turns every .py module into a catalogue
 * entity (crew#740 CP6). One provider, one full mutation per run: the
 * projection is the source of truth, so a run that no longer sees a module
 * removes its entity rather than leaving it stale.
 *
 * Unlike the Dagster provider (which polls a GraphQL API), this provider
 * shells out to `bin/catalog-projection --json`, a pure deterministic function
 * over Python source. The projection cannot drift from the code: it is the
 * mathematical guarantee (TOT/DET/IDP/REF/SCH) proved in bin/test-catalog-projection.
 */
export class EstateProjectionEntityProvider implements EntityProvider {
  private connection?: EntityProviderConnection;

  /** `providerConfig` is the `catalog.projection` sub-config, already sliced by
   * the caller so this class never re-derives the config path (LAW 46). */
  static fromConfig(
    providerConfig: Config,
    options: { logger: LoggerService; scheduler: SchedulerServiceTaskRunner },
  ): EstateProjectionEntityProvider {
    const command = providerConfig.getString('command');
    const fallbackOwner = providerConfig.getOptionalString('fallbackOwner') ?? DEFAULT_OWNER;
    const timeout = providerConfig.getOptionalNumber('timeout') ?? 120000;
    return new EstateProjectionEntityProvider(command, fallbackOwner, timeout, options.logger, options.scheduler);
  }

  constructor(
    private readonly command: string,
    private readonly fallbackOwner: string,
    private readonly timeout: number,
    private readonly logger: LoggerService,
    private readonly taskRunner: SchedulerServiceTaskRunner,
  ) {}

  getProviderName(): string {
    return 'estate-projection-entity-provider';
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
    this.logger.info(`Running estate projection: ${this.command}`);
    const entities = await fetchProjectionEntities(this.command, this.timeout, this.logger);
    const mapped = estateProjectionResponseToEntities(entities, {
      fallbackOwner: this.fallbackOwner,
    });
    await this.connection.applyMutation({
      type: 'full',
      entities: mapped.map(entity => ({
        entity,
        locationKey: this.getProviderName(),
      })),
    });
    this.logger.info(`Estate projection emitted ${mapped.length} entities`);
  }
}

/**
 * Runs the projection command as a subprocess and returns the parsed JSON
 * entity array. Throws on non-zero exit or malformed JSON.
 */
export async function fetchProjectionEntities(
  command: string,
  timeout: number,
  logger: LoggerService,
): Promise<any[]> {
  return new Promise((resolve, reject) => {
    execFile('sh', ['-c', command], { timeout, maxBuffer: 50 * 1024 * 1024 }, (error, stdout, stderr) => {
      if (error) {
        logger.error(`Projection command failed: ${error.message}`);
        if (stderr) logger.error(stderr.slice(0, 500));
        reject(error);
        return;
      }
      try {
        const entities = JSON.parse(stdout);
        if (!Array.isArray(entities)) {
          throw new Error(`Projection output is not a JSON array`);
        }
        resolve(entities);
      } catch (e) {
        logger.error(`Failed to parse projection JSON: ${(e as Error).message}`);
        reject(e);
      }
    });
  });
}