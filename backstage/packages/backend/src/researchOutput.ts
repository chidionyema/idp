// The research department, on the record. The research-engine (GPT Researcher, namespace
// research) fires hourly and writes what it verified to the `research` database on the estate's
// one Postgres (platform/estate-db/cluster/databases.yaml: database research, owner research).
// Until this plugin existed the claims were invisible: Backstage showed only the pod, and the
// founder was asked to read them with kubectl and psql -- which is not a surface (founder,
// 2026-10-10, live). This serves them at:
//
//   GET /api/research-output/claims?limit=12
//
// The credential follows the estate's secrets-not-from-env-vars policy (platform/backstage/base/
// catalogue.yaml lines 73-76, same pattern as prospector's file_secrets.py): the password file is
// mounted from secret `research-db` (overlays/oke/research-db-external-secret.yaml, vault entry
// estate-db property research-password -- the exact field the engine's own ExternalSecret reads)
// and is RE-READ on every request, so a vault rotation takes effect without a pod restart.
//
// The role is `research`, the same one the engine itself connects as, and the query is a plain
// read-only SELECT of three measured columns -- the plugin cannot write a row even in principle.
//
// Failure is an envelope, never a 500 (see featureRegister.ts and every fleetview route): a
// claim board nobody can read must say so, not render an outage as an empty page.
import { createBackendPlugin, coreServices } from '@backstage/backend-plugin-api';
import { Router } from 'express';
import fs from 'fs/promises';
import { Client } from 'pg';

const CLAIMS_PATH = '/claims';
const DEFAULT_SECRET_FILE = '/run/secrets/research-db/POSTGRES_PASSWORD';
const DEFAULT_HOST = 'estate-rw.estate-db.svc.cluster.local';
const DEFAULT_LIMIT = 12;
const MAX_LIMIT = 50;
const CONNECT_TIMEOUT_MS = 3_000;
const STATEMENT_TIMEOUT_MS = 4_000;

export type Claim = {
  created_at: string;
  status: string;
  statement: string;
};

// The seams the tests drive: where the password comes from and what opens the connection.
export type ClaimsIo = {
  readSecret: (path: string) => Promise<string>;
  connect: (config: {
    host: string;
    port: number;
    database: string;
    user: string;
    password: string;
    connectionTimeoutMillis: number;
    statement_timeout: number;
  }) => {
    connect: () => Promise<void>;
    query: (sql: string, values: unknown[]) => Promise<{ rows: any[] }>;
    end: () => Promise<void>;
  };
};

export const productionIo: ClaimsIo = {
  readSecret: path => fs.readFile(path, 'utf-8'),
  // pg's Client satisfies the seam structurally: connect(), query(sql, values) and end().
  connect: config => new Client(config),
};

export const fetchClaims = async (
  io: ClaimsIo,
  opts: {
    secretFile: string;
    host: string;
    limit: number;
    port?: number;
    database?: string;
    user?: string;
  },
): Promise<Claim[]> => {
  const limit = Math.max(1, Math.min(MAX_LIMIT, Math.floor(opts.limit) || DEFAULT_LIMIT));
  const password = (await io.readSecret(opts.secretFile)).trim();
  if (!password) {
    throw new Error(`research db credential at ${opts.secretFile} is empty`);
  }
  const client = io.connect({
    host: opts.host,
    port: opts.port ?? 5432,
    database: opts.database ?? 'research',
    user: opts.user ?? 'research',
    password,
    connectionTimeoutMillis: CONNECT_TIMEOUT_MS,
    statement_timeout: STATEMENT_TIMEOUT_MS,
  });
  try {
    // connect() first, and awaited. pg queues a query issued on an unconnected Client and never
    // runs it, and connectionTimeoutMillis only starts counting inside connect() -- the version of
    // this file without it held every request open forever (measured live 2026-10-13: the guest
    // call to /claims never answered, and /fleet's research pill never left "unreachable").
    await client.connect();
    // Only columns measured to exist on the claims table (psql, 2026-10-10); newest first.
    const result = await client.query(
      'SELECT created_at, status, statement FROM claims ORDER BY created_at DESC LIMIT $1',
      [limit],
    );
    // The shape is guaranteed by the SELECT above, not by the wire format -- researchOutput
    // .test.ts asserts that exact SQL string.
    return result.rows as Claim[];
  } finally {
    await client.end().catch(() => {});
  }
};

export const claimsEnvelope = async (
  io: ClaimsIo,
  rawLimit: string | undefined,
  opts: { secretFile: string; host: string; port?: number; user?: string },
): Promise<{ body: Record<string, unknown>; status: number }> => {
  const limit = rawLimit ? parseInt(rawLimit, 10) : DEFAULT_LIMIT;
  try {
    const claims = await fetchClaims(io, { ...opts, limit });
    return {
      body: {
        available: true,
        count: claims.length,
        claims,
        source: 'estate-db/research.claims',
      },
      status: 200,
    };
  } catch (err: any) {
    return {
      body: {
        available: false,
        error: `research claims unavailable: ${err?.message ?? String(err)}`,
      },
      status: 503,
    };
  }
};

export const researchOutputPlugin = createBackendPlugin({
  pluginId: 'research-output',
  register(reg) {
    reg.registerInit({
      deps: {
        httpRouter: coreServices.httpRouter,
        logger: coreServices.logger,
      },
      async init({ httpRouter, logger }) {
        const router = Router();

        router.get(CLAIMS_PATH, async (req, res) => {
          const { body, status } = await claimsEnvelope(productionIo, req.query.limit as string, {
            // All overridable so a dev machine can point at a tunnel without editing code;
            // in-cluster the defaults are the names the engine itself uses. The laptop's
            // /fleet sets them in bin/fleetview-frontend-launchd: bin/idp-research-tunnel's
            // port-forward, as research_reader -- a role that cannot write a claim.
            secretFile: process.env.RESEARCH_DB_PASSWORD_FILE ?? DEFAULT_SECRET_FILE,
            host: process.env.RESEARCH_DB_HOST ?? DEFAULT_HOST,
            port: process.env.RESEARCH_DB_PORT ? Number(process.env.RESEARCH_DB_PORT) : undefined,
            user: process.env.RESEARCH_DB_USER || undefined,
          });
          if (status !== 200) {
            logger.warn(String(body.error));
          }
          res.status(status);
          res.contentType('application/json');
          res.send(body);
        });

        httpRouter.use(router);
        logger.info('research-output plugin mounted at /api/research-output/');
      },
    });
  },
});

export default researchOutputPlugin;
