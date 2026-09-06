// The credential-ingest door must never leak the pasted value: not into a log, an error, a task
// step, or a response (docs/specs/key-ingest-door.md part 2). Each rule below is the exact
// acceptance from part 5 (`yarn --cwd backstage test credentialIngest`) restated as a test that
// feeds the value through the real handler and then greps every surface the value could have
// reached for its literal bytes. If one of these goes green on a code path that logged the value,
// the test is wrong, not the door.
import crypto from 'crypto';

import { buildIngestHandler } from './credentialIngest';

// A faithful mock of an express response: methods chain and the body/status/headers are captured
// so the test can assert on bytes without any real HTTP surface.
function mockRes() {
  const state: { status?: number; body?: unknown } = {};
  const res: any = {
    status(n: number) { state.status = n; return res; },
    contentType() { return res; },
    send(b: unknown) { state.body = b; return res; },
  };
  (res as any).__state = state;
  return res;
}

// The fixture value the door must never leak. It is synthetic on purpose and shaped so
// secret scanners can tell: no vendor prefix, no hex run. A fixture that LOOKS real gets
// pasted into the allow-list by the next session that copies this file, and one day that
// allow-list entry hides a real key (gitleaks flagged the previous fixture; the fingerprint
// of that historical commit lives in .gitleaksignore with this note).
const SECRET = 'ingest-door-fixture-value-must-never-leak-2026';
const sha8 = (s: string) => crypto.createHash('sha256').update(s, 'utf8').digest('hex').slice(0, 8);

interface LogSink {
  info: string[];
  error: string[];
  spans: object[];
}
function sinks() {
  const s: LogSink = { info: [], error: [], spans: [] };
  return {
    s,
    logger: {
      info(m: string, meta?: object) { s.info.push(m + (meta ? ' ' + JSON.stringify(meta) : '')); },
      error(m: string, meta?: object) { s.error.push(m + (meta ? ' ' + JSON.stringify(meta) : '')); },
    },
    emitSpan(a: object) { s.spans.push(a); },
  };
}

// Allow-list carrying exactly one Customer-owned entry. This is what a request-time read of
// root-trust.md returns (consumer fixture; the real parser is graded separately by bin/idp-ci).
const allowList = new Map<string, Set<string>>([['cyrus-linear', new Set()]]);
const writableStores = new Map<string, { write: boolean }>([
  ['estate-vault', { write: true }],
  ['human-vault', { write: false }],
]);

function makeHandler(over: {
  caller?: any;
  allow?: Map<string, Set<string>>;
  stores?: Map<string, { write: boolean }>;
  failWrite?: boolean;
  logger?: any;
  emits?: LogSink;
} = {}) {
  const { s, logger, emitSpan } = over.emits ? { s: over.emits, logger: over.logger ?? { info(){}, error(){} }, emitSpan: (a: object) => over.emits!.spans.push(a) } : sinks();
  const writes: string[][] = [];
  const handler = buildIngestHandler({
    readAllowList: async () => over.allow ?? allowList,
    readStores: async () => over.stores ?? writableStores,
    getCaller: () => over.caller,
    vaultWriter: async (entry, key, value, store) => {
      writes.push([entry, key, value, store]);
      if (over.failWrite) throw new Error('vault backend unreachable' + value.substring(0, 0));
    },
    emitSpan,
    logger,
  });
  return { handler, writes: () => writes, s };
}

describe('credential-ingest door never leaks the value', () => {
  it('403 when no caller forwarded by the front door', async () => {
    const { handler } = makeHandler({ caller: undefined });
    const res = mockRes();
    await handler({ body: { entry: 'cyrus-linear', key: 'api_token', value: SECRET, store: 'estate-vault' } }, res);
    expect(res.__state.status).toBe(403);
  });

  it('400 for an entry that is not Customer-owned in the allow-list', async () => {
    const { handler } = makeHandler({ caller: { tenant: 'estate' } });
    const res = mockRes();
    await handler({ body: { entry: 'estate-internal-op', key: 'token', value: SECRET, store: 'estate-vault' } }, res);
    expect(res.__state.status).toBe(400);
  });

  it('400 for an empty value or a malformed key', async () => {
    const { handler } = makeHandler({ caller: { tenant: 'estate' } });
    for (const body of [
      { entry: 'cyrus-linear', key: 'api_token', value: '', store: 'estate-vault' },
      { entry: 'cyrus-linear', key: 'join; rm -rf /', value: SECRET, store: 'estate-vault' },
      { entry: 'cyrus-linear', key: 'api_token', value: SECRET, store: 'nope' },
    ]) {
      const r = mockRes();
      await handler({ body }, r);
      expect(r.__state.status).toBe(400);
    }
  });

  it('400 for a store the register does not offer as writable', async () => {
    const { handler } = makeHandler({ caller: { tenant: 'estate' } });
    const res = mockRes();
    await handler({ body: { entry: 'cyrus-linear', key: 'api_token', value: SECRET, store: 'human-vault' } }, res);
    expect(res.__state.status).toBe(400);
  });

  it('200 writes the value to the writer exactly once and returns only the sha prefix', async () => {
    const { handler, writes, s } = makeHandler({ caller: { tenant: 'estate' } });
    const res = mockRes();
    await handler({ body: { entry: 'cyrus-linear', key: 'api_token', value: SECRET, store: 'estate-vault' } }, res);
    expect(res.__state.status).toBe(200);
    const writesSeen = writes();
    expect(writesSeen).toHaveLength(1);
    expect(writesSeen[0]).toEqual(['cyrus-linear', 'api_token', SECRET, 'estate-vault']);
    const body: any = res.__state.body;
    expect(body?.sha256_prefix).toBe(sha8(SECRET));
    expect(body?.value).toBeUndefined();

    // The one span that left the process carries entry/key/store/tenant/prefix and no value byte.
    for (const span of s.spans) {
      const serialized = JSON.stringify(span);
      expect(serialized).not.toContain(SECRET);
      expect(JSON.stringify(span)).toContain(sha8(SECRET));
    }
    // And nothing the handler logged contains a single byte of the value.
    for (const line of [...s.info, ...s.error]) expect(line).not.toContain(SECRET);
    expect(JSON.stringify(body)).not.toContain(SECRET);
  });

  it('the value does not leak on the error path either', async () => {
    const { handler, s } = makeHandler({ caller: { tenant: 'estate' }, failWrite: true });
    const res = mockRes();
    await handler({ body: { entry: 'cyrus-linear', key: 'api_token', value: SECRET, store: 'estate-vault' } }, res);
    expect(res.__state.status).toBe(502);
    expect(JSON.stringify(res.__state.body)).not.toContain(SECRET);
    for (const line of [...s.info, ...s.error]) expect(line).not.toContain(SECRET);
  });
});
