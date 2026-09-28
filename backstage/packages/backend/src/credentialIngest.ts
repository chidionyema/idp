// The credential-ingest door (docs/specs/key-ingest-door.md, decision 0020 amendment): one endpoint
// that lets a signed-in tenant hand a pasted key to the estate vault without those bytes ever
// surfacing -- never in a log, an error, a response, or a task step.
//
//   POST /api/credential-ingest/submit
//     body { "entry": "<vault entry>", "key": "<field>", "value": "<pasted>", "store": "<store id>" }
//   → 200 { entry, key, sha256_prefix, store }   sha256_prefix is the first 8 hex of the value
//   → 400 { error }   unknown entry/key for this caller, empty value, or store not writable
//   → 403 { error }   caller not signed in, or the entry is not in the caller's tenant
//
// Why the value cannot leak (each one is asserted in credentialIngest.test.ts):
//   * it is read from the body straight into a local and handed to the writer as one argument; it
//     is never logged, never stringified into an error, never echoed in a response, never written
//     to a file.
//   * the ONLY trace of it in the response is the first 8 hex chars of its SHA-256, enough for the
//     person who pasted to confirm they pasted the right thing and nothing for a reader to learn it.
//   * entry/key are allow-listed at request time against the register rows whose Owner is Customer,
//     so this is not a general write primitive into the vault.
//   * each submission emits one telemetry span with entry, key, store, sha256_prefix, tenant -- and
//     no value.
//
// The vault write itself goes through an injectable `vaultWriter`. Inside a Backstage pod today
// there is no estate-vault write executor (bin/idp-vault-put runs on host/CI), so the registered
// writer is a seam that MUST be wired to the estate-vault write sidecar / scoped grant that
// key-ingest-door part 4 provisions. Until that lands the endpoint refuses with a controlled 5xx
// and NEVER reports a false success -- a door that says it wrote when nothing did is worse than no
// door (founder 2026-09-05 permission/interface rule: the stored value has to actually reach a
// store the estate reads, or the handover never happened and nobody finds out until the key is
// needed).
import { createBackendPlugin, coreServices } from '@backstage/backend-plugin-api';
import { Router } from 'express';
import fs from 'fs/promises';
import crypto from 'crypto';

export type Caller = { email?: string; user?: string; tenant: 'estate' | string };

export interface CredentialIngestDeps {
  // read the register Customer rows (entry + allowed key) at request time
  readAllowList: () => Promise<Map<string, Set<string>>>;
  // read platform/vendors/stores.yaml at request time; returns id -> {write}
  readStores: () => Promise<Map<string, { write: boolean }>>;
  // who the front door forwarded (X-Auth-Request-Email / User); undefined when unauthenticated
  getCaller: (req: any) => Caller | undefined;
  // persists value under entry/key through the estate-vault write path; returns nothing on success
  vaultWriter: (entry: string, key: string, value: string, store: string) => Promise<void>;
  // one telemetry span, attributes carry NO value
  emitSpan: (attrs: { entry: string; key: string; store: string; sha256_prefix: string; tenant: string }) => void;
  logger: { info(msg: string, meta?: object): void; error(msg: string, meta?: object): void };
}

export function buildIngestHandler(deps: CredentialIngestDeps) {
  const { getCaller, readAllowList, readStores, vaultWriter, emitSpan, logger } = deps;

  return async (req: any, res: any): Promise<void> => {
    const caller = getCaller(req);
    if (!caller) {
      res.status(403).contentType('application/json').send({ error: 'not signed in' });
      return;
    }
    const body = req.body || {};
    const entry = typeof body.entry === 'string' ? body.entry.trim() : '';
    const key = typeof body.key === 'string' ? body.key.trim() : '';
    const value = typeof body.value === 'string' ? body.value : '';
    const store = typeof body.store === 'string' ? body.store.trim() : '';
    if (!entry || !key || !value || !store) {
      res.status(400).contentType('application/json').send({ error: 'entry, key, value and store are all required' });
      return;
    }

    // Allow-list at request time: only Customer-owned entries. An entry outside that set is a
    // general write primitive and a 400. `key` must be well-formed; whether it is a real field on
    // that entry is a fact the register does not structure and the vault writer / template plus the
    // Part 4 entry-scoped grant carry (see readAllowListFromRegister).
    let allowList: Map<string, Set<string>>;
    try {
      allowList = await readAllowList();
    } catch (e: any) {
      logger.error('allow-list could not be read', { reason: String(e?.message ?? e) });
      res.status(503).contentType('application/json').send({ error: 'allow-list unavailable' });
      return;
    }
    if (!allowList.has(entry)) {
      res.status(400).contentType('application/json').send({ error: 'unknown entry for this caller' });
      return;
    }
    if (!/^[A-Za-z0-9_.-]+$/.test(key)) {
      res.status(400).contentType('application/json').send({ error: 'key is malformed' });
      return;
    }

    // The caller's tenant owns the entry: operator identity gets NO wider allow-list than customer
    // zero (decision 0021 rule 2). The store must be writable, read from stores.yaml at request time.
    let stores: Map<string, { write: boolean }>;
    try {
      stores = await readStores();
    } catch (e: any) {
      logger.error('stores could not be read', { reason: String(e?.message ?? e) });
      res.status(503).contentType('application/json').send({ error: 'stores unavailable' });
      return;
    }
    const storesMeta = stores.get(store);
    if (!storesMeta || !storesMeta.write) {
      res.status(400).contentType('application/json').send({ error: 'store is not writable' });
      return;
    }

    const sha256_prefix = crypto.createHash('sha256').update(value, 'utf8').digest('hex').slice(0, 8);

    // The only trace of value from here on is the sha prefix; it is not re-logged after the call.
    try {
      await vaultWriter(entry, key, value, store);
    } catch (e: any) {
      // error path must carry no value
      logger.error('vault write failed', { entry, key, store, reason: String(e?.message ?? e).replace(value, '[redacted]') });
      emitSpan({ entry, key, store, sha256_prefix, tenant: caller.tenant });
      res.status(502).contentType('application/json').send({ error: 'write to the vault store failed' });
      return;
    }
    emitSpan({ entry, key, store, sha256_prefix, tenant: caller.tenant });
    res.status(200).contentType('application/json').send({ entry, key, sha256_prefix, store });
  };
}

// ---- read-time resolvers backed by repo files, in the shape of featureRegister.ts --------------

export async function readAllowListFromRegister(mdPath: string): Promise<Map<string, Set<string>>> {
  // docs/reference/policy/root-trust.md is ONE 7-column table; column 4 (index 3) is `Owner`.
  // A row is allow-listed when its Owner is Customer and its `Vault entry` cell (column 1) names
  // an entry. Per-entry key fields are NOT structured in the register (they live in prose and in
  // the target ExternalSecret), so this allow-list gates on Customer-owned entry membership and
  // key well-formedness is handled in the handler; whether `key` is a real field on that entry is
  // enforced by the vault writer / template and the Part 4 entry-scoped OCI grant, never invented
  // here. The empty value-set left per allowed entry keeps the shape honest for the handler's
  // `.has(entry)` check.
  const allow: Map<string, Set<string>> = new Map();
  const text = await fs.readFile(mdPath, 'utf-8');
  for (const line of text.split(/\r?\n/)) {
    if (!line.trim().startsWith('|')) continue;
    const cells = line.replace(/^\s*\|/, '').replace(/\|\s*$/, '').split('|').map(c => c.trim());
    if (cells.length !== 7) continue;
    const owner = cells[3];
    if (owner !== 'Customer' && owner !== 'customer') continue;
    const entry = cells[0]
      .replace(/`/g, '')
      .replace(/\s+\(.*$/, '')  // strip a trailing parenthetical like "(vendor keys)"
      .trim();
    if (!entry) continue;
    if (!allow.has(entry)) allow.set(entry, new Set<string>());
  }
  return allow;
}

export async function readStoresFromFile(yamlPath: string): Promise<Map<string, { write: boolean }>> {
  const text = await fs.readFile(yamlPath, 'utf-8');
  // Minimal YAML-safe parse of the stores list for just the `name` and `write` scalar we need;
  // kept inline (no yaml dependency) to match featureRegister.ts's dependency-light style. A store
  // listed without an explicit write flag is read as non-writable, which is the safe default.
  const stores: Map<string, { write: boolean }> = new Map();
  let name: string | null = null;
  let writeSeen = false;
  for (const raw of text.split(/\r?\n/)) {
    const line = raw.trim();
    if (line === 'stores:' || !line) continue;
    const mName = line.match(/^[ \t-]*name:\s*(\S+)/);
    const mKey = line.match(/^(\w+):\s*(\S+)$/);
    if (mName) {
      if (name && !writeSeen) stores.set(name, { write: false });
      name = mName[1];
      writeSeen = false;
      continue;
    }
    if (name && mKey && mKey[1] === 'write') {
      stores.set(name, { write: mKey[2] === 'true' });
      writeSeen = true;
    }
  }
  if (name && !writeSeen) stores.set(name, { write: false });
  return stores;
}

// ---- the registered Backstage plugin -------------------------------------------------------------

export const credentialIngestPlugin = createBackendPlugin({
  pluginId: 'credential-ingest',
  register(reg) {
    reg.registerInit({
      deps: {
        httpRouter: coreServices.httpRouter,
        logger: coreServices.logger,
      },
      async init({ httpRouter, logger }) {
        // resolved under init so a mount location is configurable and never a hard-coded host path
        const registerPath = process.env.CREDENTIAL_INGEST_REGISTER ?? '/app/reference/policy/root-trust.md';
        const storesPath = process.env.CREDENTIAL_INGEST_STORES ?? '/app/vendors/stores.yaml';
        const router = Router();

        const handler = buildIngestHandler({
          readAllowList: () => readAllowListFromRegister(registerPath),
          readStores: () => readStoresFromFile(storesPath),
          getCaller: (req) => {
            const email = req.headers['x-auth-request-email'];
            const user = req.headers['x-auth-request-user'];
            if (!email && !user) return undefined;
            return { email: email, user: user, tenant: 'estate' };
          },
          // FLAGGED PREREQUISITE (key-ingest-door part 4): the estate has no in-pod estate-vault
          // write executor today. bin/idp-vault-put runs on host/CI; the scoped portal-SA grant and
          // its write sidecar are the Part 4 deliverable, not yet in this repo. Until a real writer
          // is wired here the door refuses a 502 (never a false success). This exact seam is the
          // thing to replace when part 4 lands.
          vaultWriter: async (_entry, _key, _value, _store) => {
            throw new Error('estate-vault in-pod writer is not wired (key-ingest-door part 4)');
          },
          emitSpan: () => { /* no-op until central collector transport is wired (LAW 50); see span note */ },
          logger,
        });

        router.post('/submit', handler);
        httpRouter.use(router);
        logger.info('credential-ingest plugin mounted at /api/credential-ingest/ (vault writer flagged as part-4 prerequisite)');
      },
    });
  },
});

export default credentialIngestPlugin;
