import {
  AVATAR_KEY,
  AVATARS,
  DEFAULT_AVATAR,
  parseAvatarUrl,
  readAvatar,
  resolveAvatar,
  saveAvatar,
} from './faceAvatars';

const mem = () => {
  const m = new Map<string, string>();
  return { getItem: (k: string) => m.get(k) ?? null, setItem: (k: string, v: string) => void m.set(k, v) };
};

describe('parseAvatarUrl', () => {
  it('accepts https/http .glb and same-origin absolute paths', () => {
    expect(parseAvatarUrl('https://cdn.example.com/a/me.glb')).toBe('https://cdn.example.com/a/me.glb');
    expect(parseAvatarUrl('/face/estate.glb', 'https://app.test')).toBe('https://app.test/face/estate.glb');
    expect(parseAvatarUrl('  http://x.test/Me.GLB  ')).toBe('http://x.test/Me.GLB');
  });
  it('rejects other schemes, non-glb, credentials, bare relatives and junk', () => {
    for (const bad of [
      '',
      'javascript:alert(1)',
      'data:model/gltf-binary;base64,AAAA',
      'file:///etc/x.glb',
      'https://x.test/me.png',
      'https://u:p@x.test/me.glb',
      'me.glb',
      'not a url',
    ]) {
      expect(parseAvatarUrl(bad)).toBeNull();
    }
  });
});

describe('resolveAvatar', () => {
  it('returns shipped avatars by id', () => {
    for (const a of AVATARS) expect(resolveAvatar(JSON.stringify({ id: a.id }))).toBe(a);
  });
  it('returns a custom avatar for a valid url', () => {
    const a = resolveAvatar(JSON.stringify({ url: 'https://x.test/me.glb' }));
    expect(a).toMatchObject({ id: 'custom', url: 'https://x.test/me.glb', custom: true });
  });
  it('falls back to the default for missing, unknown, corrupt or unsafe values', () => {
    for (const s of [null, '', '{', 'null', '{"id":"nope"}', '{"url":"javascript:x"}', '[]']) {
      expect(resolveAvatar(s)).toBe(DEFAULT_AVATAR);
    }
  });
});

describe('storage', () => {
  it('round-trips a shipped and a custom choice', () => {
    const s = mem();
    expect(saveAvatar(s, AVATARS[1])).toBe(true);
    expect(readAvatar(s)).toBe(AVATARS[1]);
    const c = resolveAvatar(JSON.stringify({ url: 'https://x.test/me.glb' }));
    saveAvatar(s, c);
    expect(readAvatar(s).url).toBe('https://x.test/me.glb');
    expect(s.getItem(AVATAR_KEY)).toBe('{"url":"https://x.test/me.glb"}');
  });
  it('survives storage that throws or is absent', () => {
    const boom = {
      getItem: () => {
        throw new Error('denied');
      },
      setItem: () => {
        throw new Error('denied');
      },
    };
    expect(readAvatar(boom)).toBe(DEFAULT_AVATAR);
    expect(saveAvatar(boom, AVATARS[1])).toBe(false);
    expect(readAvatar(null)).toBe(DEFAULT_AVATAR);
    expect(saveAvatar(null, AVATARS[1])).toBe(false);
  });
});
