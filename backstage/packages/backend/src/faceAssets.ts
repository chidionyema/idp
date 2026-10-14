// The face's static assets (packages/app/public/face/: brunette.glb, talkinghead.mjs, three/...)
// served with caching that actually caches. Before this plugin they went out through the app
// backend's static handler, measured live 2026-10 on catalogue.mumchimp.com/face/brunette.glb:
//
//   cache-control: public, max-age=0
//   etag: W/"480b78-0"
//   last-modified: Thu, 01 Jan 1970 00:00:00 GMT
//
// The image's COPY layers flatten every mtime to the epoch, so the weak size+mtime ETag changes
// only when the byte count does -- a same-size asset swap would be served stale -- and the
// last-modified header says nothing at all.
//
// This route answers instead with a STRONG ETag taken from a sha256 of the bytes, and
// `cache-control: public, no-cache`: the browser keeps the file and revalidates on each visit,
// and an unchanged avatar costs a 304 rather than 2.9 MB. Not `immutable`: the filenames are not
// content-hashed (faceEngine.ts loads /face/brunette.glb by name), so a year-long max-age would
// pin a replaced avatar in every browser that had seen the old one.
//
// Mounted on the root router at /face, which DefaultRootHttpRouter consults before the app's
// index handler; a path this does not find falls through to it unchanged.
import { coreServices, createBackendPlugin, resolvePackagePath } from '@backstage/backend-plugin-api';
import { createHash } from 'crypto';
import { createReadStream } from 'fs';
import fs from 'fs/promises';
import * as path from 'path';

export const FACE_CACHE_CONTROL = 'public, no-cache';

const CONTENT_TYPES: Record<string, string> = {
  '.glb': 'model/gltf-binary',
  '.mjs': 'text/javascript; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
};

// The slice of express's req/res this handler touches, so the tests drive it with plain objects.
export type FaceRequest = { method: string; path: string; headers: Record<string, string | string[] | undefined> };
export type FaceResponse = {
  status: (code: number) => FaceResponse;
  setHeader: (name: string, value: string) => unknown;
  end: () => unknown;
};
export type FaceIo = {
  stat: (file: string) => Promise<{ isFile: () => boolean; size: number; mtimeMs: number }>;
  hash: (file: string) => Promise<string>;
  pipe: (file: string, res: FaceResponse) => void;
};

export const productionIo: FaceIo = {
  stat: file => fs.stat(file),
  hash: file =>
    new Promise((resolve, reject) => {
      const digest = createHash('sha256');
      createReadStream(file)
        .on('data', chunk => digest.update(chunk))
        .on('error', reject)
        .on('end', () => resolve(digest.digest('hex')));
    }),
  pipe: (file, res) => {
    createReadStream(file).pipe(res as unknown as NodeJS.WritableStream);
  },
};

const etagMatches = (header: string | string[] | undefined, etag: string): boolean => {
  if (!header) return false;
  const value = Array.isArray(header) ? header.join(',') : header;
  return value.split(',').some(tag => {
    const t = tag.trim();
    return t === '*' || t === etag || t === `W/${etag}`;
  });
};

export const createFaceAssetHandler = (root: string, io: FaceIo = productionIo) => {
  const resolvedRoot = path.resolve(root);
  // Hashed once per (file, size, mtime): the image's files never change while the pod lives, and
  // a 2.9 MB sha256 on every request would be the cost this route exists to remove.
  const etags = new Map<string, string>();

  return async (req: FaceRequest, res: FaceResponse, next: (err?: unknown) => void) => {
    if (req.method !== 'GET' && req.method !== 'HEAD') return next();
    let rel: string;
    try {
      rel = decodeURIComponent(req.path);
    } catch {
      return next();
    }
    const file = path.resolve(resolvedRoot, `.${path.posix.normalize(`/${rel}`)}`);
    if (!file.startsWith(`${resolvedRoot}${path.sep}`)) return next();

    try {
      const stat = await io.stat(file);
      if (!stat.isFile()) return next();
      const key = `${file}:${stat.size}:${stat.mtimeMs}`;
      let etag = etags.get(key);
      if (!etag) {
        etag = `"sha256-${(await io.hash(file)).slice(0, 32)}"`;
        etags.set(key, etag);
      }

      res.setHeader('Cache-Control', FACE_CACHE_CONTROL);
      res.setHeader('ETag', etag);
      if (etagMatches(req.headers['if-none-match'], etag)) {
        res.status(304).end();
        return undefined;
      }
      res.setHeader('Content-Type', CONTENT_TYPES[path.extname(file)] ?? 'application/octet-stream');
      res.setHeader('Content-Length', String(stat.size));
      res.status(200);
      if (req.method === 'HEAD') {
        res.end();
        return undefined;
      }
      io.pipe(file, res);
      return undefined;
    } catch {
      // Missing file (or unreadable): not ours to answer -- the app handler has the last word.
      return next();
    }
  };
};

export default createBackendPlugin({
  pluginId: 'face-assets',
  register(env) {
    env.registerInit({
      deps: { rootHttpRouter: coreServices.rootHttpRouter, logger: coreServices.logger },
      async init({ rootHttpRouter, logger }) {
        // public/ is copied to the root of the app's dist by the frontend build.
        const root = resolvePackagePath('app', 'dist', 'face');
        rootHttpRouter.use('/face', createFaceAssetHandler(root) as any);
        logger.info(`serving /face from ${root} with strong ETags`);
      },
    });
  },
});
