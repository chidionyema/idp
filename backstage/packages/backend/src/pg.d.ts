// Minimal declaration for the one surface researchOutput.ts uses from `pg` (the dependency
// ships without types, and @types/pg is not in the lockfile). If the plugin ever needs more of
// the client than query/end/connect, take @types/pg properly: add it to
// packages/backend/package.json AND commit the refreshed yarn.lock in the same change, because
// CI installs with --immutable.
declare module 'pg' {
  export interface ClientConfig {
    host?: string;
    port?: number;
    database?: string;
    user?: string;
    password?: string;
    connectionTimeoutMillis?: number;
    statement_timeout?: number;
  }

  export interface QueryResultRow {
    [column: string]: any;
  }

  export class Client {
    constructor(config?: ClientConfig);
    connect(): Promise<void>;
    query(sql: string, values?: unknown[]): Promise<{ rows: QueryResultRow[] }>;
    end(): Promise<void>;
  }
}
