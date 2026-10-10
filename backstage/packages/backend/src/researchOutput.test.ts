// The claims door, fed by a fake io the same way credentialIngest.test.ts feeds its real
// handler a fake express response: what is asserted is the SQL the door runs, the envelope it
// returns, and that failure is a 503 envelope -- never a thrown 500, and never a row written.
import { claimsEnvelope, fetchClaims, productionIo, type ClaimsIo } from './researchOutput';
// Static, named imports of the node builtins: jest's CJS transform turns these into plain
// require() calls -- the one import shape with no interop or dynamic-import machinery that
// could differ between the runner and the deploy. Measured: the dynamic-import version of
// this suite failed in CI with an empty failure body (b2275), unprintable by jest.
import { mkdtemp, writeFile } from 'fs/promises';
import { tmpdir } from 'os';
import * as path from 'path';

function fakeIo(rows: Array<{ created_at: string; status: string; statement: string }>) {
  const calls: { sql: string; values: unknown[]; config: Record<string, unknown> }[] = [];
  const io: ClaimsIo = {
    readSecret: async path => {
      if (path.endsWith('empty')) return '   ';
      return 'fixture-password-not-a-real-credential';
    },
    connect: config => {
      const client = {
        query: async (sql: string, values: unknown[]) => {
          calls.push({ sql, values, config: config as Record<string, unknown> });
          return { rows };
        },
        end: async () => {},
      };
      return client;
    },
  };
  return { io, calls };
}

const ROWS = [
  { created_at: '2026-10-10T13:25:00.000000+00:00', status: 'verified', statement: 'claim one' },
  { created_at: '2026-10-09T14:00:00.000000+00:00', status: 'verified', statement: 'claim two' },
];

describe('fetchClaims', () => {
  it('runs one read-only SELECT of the three measured columns, newest first, LIMIT parameterised', async () => {
    const { io, calls } = fakeIo(ROWS);
    const claims = await fetchClaims(io, { secretFile: '/run/secrets/research-db/POSTGRES_PASSWORD', host: 'estate-rw.estate-db.svc.cluster.local', limit: 12 });
    expect(claims).toEqual(ROWS);
    expect(calls).toHaveLength(1);
    expect(calls[0].sql).toBe(
      'SELECT created_at, status, statement FROM claims ORDER BY created_at DESC LIMIT $1',
    );
    expect(calls[0].values).toEqual([12]);
    // The connection is the engine's own identity on the estate's one Postgres, read-only by role.
    expect(calls[0].config.database).toBe('research');
    expect(calls[0].config.user).toBe('research');
    expect(calls[0].config.host).toBe('estate-rw.estate-db.svc.cluster.local');
    expect(calls[0].config.statement_timeout).toBeGreaterThan(0);
  });

  it('clamps the limit into 1..50', async () => {
    const { io, calls } = fakeIo([]);
    await fetchClaims(io, { secretFile: '/x', host: 'h', limit: 9999 });
    expect(calls[0].values).toEqual([50]);
    // 0 and NaN are falsy and fall through to the default -- a caller asking for "zero claims"
    // gets the default dozen, which is the sane reading of an unset-ish limit.
    await fetchClaims(io, { secretFile: '/x', host: 'h', limit: 0 });
    expect(calls[1].values).toEqual([12]);
    await fetchClaims(io, { secretFile: '/x', host: 'h', limit: Number.NaN });
    expect(calls[2].values).toEqual([12]);
  });

  it('refuses an empty credential file', async () => {
    const { io, calls } = fakeIo(ROWS);
    await expect(
      fetchClaims(io, { secretFile: '/run/secrets/research-db/empty', host: 'h', limit: 12 }),
    ).rejects.toThrow(/empty/);
    expect(calls).toHaveLength(0);
  });
});

describe('claimsEnvelope', () => {
  const opts = { secretFile: '/run/secrets/research-db/POSTGRES_PASSWORD', host: 'h' };

  it('answers 200 with the available envelope on success', async () => {
    const { io } = fakeIo(ROWS);
    const { body, status } = await claimsEnvelope(io, '5', opts);
    expect(status).toBe(200);
    expect(body).toEqual({
      available: true,
      count: 2,
      claims: ROWS,
      source: 'estate-db/research.claims',
    });
  });

  it('answers 503 with the unavailable envelope when the password file is missing', async () => {
    const io: ClaimsIo = {
      readSecret: async () => {
        throw new Error("ENOENT: no such file or directory, open '/run/secrets/research-db/POSTGRES_PASSWORD'");
      },
      connect: () => {
        throw new Error('must not be reached');
      },
    };
    const { body, status } = await claimsEnvelope(io, undefined, opts);
    expect(status).toBe(503);
    expect(body.available).toBe(false);
    expect(String(body.error)).toContain('research claims unavailable');
    expect(String(body.error)).toContain('ENOENT');
  });

  it('answers 503 when the database is unreachable', async () => {
    const io: ClaimsIo = {
      readSecret: async () => 'fixture-password-not-a-real-credential',
      connect: () => {
        throw new Error('connect ECONNREFUSED 10.0.0.1:5432');
      },
    };
    const { body, status } = await claimsEnvelope(io, undefined, opts);
    expect(status).toBe(503);
    expect(String(body.error)).toContain('ECONNREFUSED');
  });
});

describe('productionIo', () => {
  it('reads the mounted password file through fs/promises', async () => {
    // Real read of a fixture file: the seam is fs, so the test reads a real path.
    const dir = await mkdtemp(path.join(tmpdir(), 'research-output-'));
    const file = path.join(dir, 'POSTGRES_PASSWORD');
    await writeFile(file, 'fixture-password-not-a-real-credential\n');
    const password = await productionIo.readSecret(file);
    expect(password).toBe('fixture-password-not-a-real-credential\n');
  });
});
