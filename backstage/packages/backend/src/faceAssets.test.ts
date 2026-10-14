// The /face route, fed a fake io the same way researchOutput.test.ts feeds its door: what is
// asserted is the headers it sets, that a matching If-None-Match costs a 304 and no body, and
// that anything it does not own (traversal, other methods, missing files) falls through.
import { createFaceAssetHandler, FACE_CACHE_CONTROL, type FaceIo, type FaceRequest } from './faceAssets';
import * as path from 'path';

const ROOT = path.resolve('/srv/app/dist/face');
const HASH = 'ab'.repeat(32);
const ETAG = `"sha256-${HASH.slice(0, 32)}"`;

function fakeIo(files: Record<string, number>) {
  const hashed: string[] = [];
  const piped: string[] = [];
  const io: FaceIo = {
    stat: async file => {
      const size = files[path.relative(ROOT, file)];
      if (size === undefined) throw Object.assign(new Error('ENOENT'), { code: 'ENOENT' });
      return { isFile: () => true, size, mtimeMs: 0 };
    },
    hash: async file => {
      hashed.push(file);
      return HASH;
    },
    pipe: file => {
      piped.push(file);
    },
  };
  return { io, hashed, piped };
}

function fakeRes() {
  const res = {
    code: 0,
    headers: {} as Record<string, string>,
    ended: false,
    status(code: number) {
      res.code = code;
      return res;
    },
    setHeader(name: string, value: string) {
      res.headers[name.toLowerCase()] = value;
    },
    end() {
      res.ended = true;
    },
  };
  return res;
}

const req = (p: string, extra: Partial<FaceRequest> = {}): FaceRequest => ({
  method: 'GET',
  path: p,
  headers: {},
  ...extra,
});

describe('createFaceAssetHandler', () => {
  it('serves the avatar with a strong content ETag and revalidating cache-control', async () => {
    const { io, piped } = fakeIo({ 'brunette.glb': 2911724 });
    const res = fakeRes();
    const next = jest.fn();
    await createFaceAssetHandler(ROOT, io)(req('/brunette.glb'), res, next);

    expect(next).not.toHaveBeenCalled();
    expect(res.code).toBe(200);
    expect(res.headers['cache-control']).toBe(FACE_CACHE_CONTROL);
    expect(res.headers.etag).toBe(ETAG);
    expect(res.headers.etag.startsWith('W/')).toBe(false);
    expect(res.headers['content-type']).toBe('model/gltf-binary');
    expect(res.headers['content-length']).toBe('2911724');
    expect(piped).toEqual([path.join(ROOT, 'brunette.glb')]);
  });

  it('answers a matching If-None-Match with 304 and no body', async () => {
    const { io, piped } = fakeIo({ 'brunette.glb': 2911724 });
    const res = fakeRes();
    await createFaceAssetHandler(ROOT, io)(
      req('/brunette.glb', { headers: { 'if-none-match': `"other", ${ETAG}` } }),
      res,
      jest.fn(),
    );
    expect(res.code).toBe(304);
    expect(res.ended).toBe(true);
    expect(res.headers.etag).toBe(ETAG);
    expect(piped).toEqual([]);
  });

  it('answers HEAD with headers only', async () => {
    const { io, piped } = fakeIo({ 'talkinghead.mjs': 1234 });
    const res = fakeRes();
    await createFaceAssetHandler(ROOT, io)(req('/talkinghead.mjs', { method: 'HEAD' }), res, jest.fn());
    expect(res.code).toBe(200);
    expect(res.headers['content-type']).toBe('text/javascript; charset=utf-8');
    expect(res.ended).toBe(true);
    expect(piped).toEqual([]);
  });

  it('hashes each file once, not on every request', async () => {
    const { io, hashed } = fakeIo({ 'brunette.glb': 2911724 });
    const handler = createFaceAssetHandler(ROOT, io);
    await handler(req('/brunette.glb'), fakeRes(), jest.fn());
    await handler(req('/brunette.glb'), fakeRes(), jest.fn());
    expect(hashed).toHaveLength(1);
  });

  it.each([
    ['a missing file', req('/nope.glb')],
    ['a traversal out of the face dir', req('/../index.html')],
    ['an encoded traversal', req('/%2e%2e/index.html')],
    ['a non-GET method', req('/brunette.glb', { method: 'POST' })],
  ])('falls through on %s', async (_name, r) => {
    const { io, piped } = fakeIo({ 'brunette.glb': 2911724 });
    const res = fakeRes();
    const next = jest.fn();
    await createFaceAssetHandler(ROOT, io)(r, res, next);
    expect(next).toHaveBeenCalledTimes(1);
    expect(res.code).toBe(0);
    expect(piped).toEqual([]);
  });
});
