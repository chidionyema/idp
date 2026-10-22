// Which face the estate wears. Pure: the registry of avatars the app ships, how a stored or typed
// choice resolves to one, and how it is remembered. faceEngine.setAvatar does the actual model swap.
//
// LICENCE: brunette.glb is CC BY-NC 4.0 (tracked debt, idp#5673); the registry carries each
// avatar's licence so the Persona tab can show it rather than hide it.

export const FACE_ASSETS_PATH = '/face/';
export const AVATAR_KEY = 'estate.face.avatar.v1';

export interface Avatar {
  id: string;
  label: string;
  url: string;
  body: 'F' | 'M';
  licence: string;
  custom?: boolean;
}

export const AVATARS: Avatar[] = [
  {
    id: 'brunette',
    label: 'Brunette',
    url: `${FACE_ASSETS_PATH}brunette.glb`,
    body: 'F',
    licence: 'CC BY-NC 4.0 (non-commercial)',
  },
  {
    id: 'estate',
    label: 'Estate (geometric)',
    url: `${FACE_ASSETS_PATH}estate.glb`,
    body: 'F',
    licence: 'estate-owned',
  },
];

export const DEFAULT_AVATAR: Avatar = AVATARS[0];

/** A GLB the user typed: http(s) with a .glb path, or a same-origin absolute path. Anything else is null. */
export function parseAvatarUrl(input: string, origin = 'http://localhost'): string | null {
  const raw = input.trim();
  if (!raw) return null;
  let u: URL;
  try {
    u = new URL(raw, origin);
  } catch {
    return null;
  }
  if (u.protocol !== 'https:' && u.protocol !== 'http:') return null;
  if (u.username || u.password) return null;
  if (!u.pathname.toLowerCase().endsWith('.glb')) return null;
  // A bare relative string like "x.glb" would silently become same-origin; require intent.
  if (!/^https?:\/\//i.test(raw) && !raw.startsWith('/')) return null;
  return u.href;
}

export function customAvatar(url: string): Avatar {
  return { id: 'custom', label: 'Custom GLB', url, body: 'F', licence: 'supplied by you', custom: true };
}

/** Resolve a stored value ({id} or {url}) to an avatar. Unknown, malformed or missing is the default. */
export function resolveAvatar(stored: string | null, origin?: string): Avatar {
  if (!stored) return DEFAULT_AVATAR;
  try {
    const v = JSON.parse(stored) as { id?: unknown; url?: unknown };
    if (typeof v.url === 'string') {
      const url = parseAvatarUrl(v.url, origin);
      if (url) return customAvatar(url);
    }
    if (typeof v.id === 'string') {
      const hit = AVATARS.find(a => a.id === v.id);
      if (hit) return hit;
    }
  } catch {
    /* corrupt value: fall through to the default */
  }
  return DEFAULT_AVATAR;
}

type Store = Pick<Storage, 'getItem' | 'setItem'> | null;

export function readAvatar(store: Store, origin?: string): Avatar {
  try {
    return resolveAvatar(store?.getItem(AVATAR_KEY) ?? null, origin);
  } catch {
    return DEFAULT_AVATAR;
  }
}

/** Remember the choice. A browser that refuses storage still swaps for this visit; returns whether it stuck. */
export function saveAvatar(store: Store, a: Avatar): boolean {
  try {
    store?.setItem(AVATAR_KEY, JSON.stringify(a.custom ? { url: a.url } : { id: a.id }));
    return store != null;
  } catch {
    return false;
  }
}
