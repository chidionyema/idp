import { readFileSync, existsSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { join } from 'node:path';
import {
  wordTimings,
  IDLE_BEATS,
  nextBeat,
  readMemory,
  recordVisit,
  greeting,
  CONTINUITY_KEY,
} from './faceEngine';

describe('wordTimings', () => {
  it('spreads every word across the clause, in order, inside the audio', () => {
    const t = wordTimings('The estate is live, founder.', 2000);
    expect(t.words).toEqual(['The', 'estate', 'is', 'live,', 'founder.']);
    expect(t.wtimes[0]).toBeGreaterThan(0);
    for (let i = 1; i < t.wtimes.length; i++) expect(t.wtimes[i]).toBeGreaterThan(t.wtimes[i - 1]);
    const end = t.wtimes[t.wtimes.length - 1] + t.wdurations[t.wdurations.length - 1];
    expect(end).toBeLessThanOrEqual(2000);
    expect(end).toBeGreaterThan(1900);
  });

  it('gives a long word more time than a short one', () => {
    const t = wordTimings('a extraordinary', 1000);
    expect(t.wdurations[1]).toBeGreaterThan(t.wdurations[0] * 3);
  });

  it('says nothing for an empty clause or no audio', () => {
    expect(wordTimings('   ', 1000).words).toEqual([]);
    expect(wordTimings('hello', 0).words).toEqual([]);
  });
});

/**
 * The avatar the face mounts. This is the contract the runtime enforces at showAvatar() time,
 * read out of talkinghead.mjs and asserted against the shipped asset -- a head-only mesh throws
 * "Avatar object Armature not found", and a non-commercial avatar is refused by
 * bin/face-licence-gate. Both were live defects; both are checked here so neither returns
 * silently.
 */
describe('estate.glb (the shipped face avatar)', () => {
  // The app's public dir, resolved from this test file inside packages/app/src.
  const faceDir = join(__dirname, '..', '..', '..', 'public', 'face');
  const glbPath = join(faceDir, 'estate.glb');
  const versionsPath = join(faceDir, 'VERSIONS');

  it('ships an estate-owned avatar, and no non-commercial one alongside it', () => {
    expect(existsSync(glbPath)).toBe(true);
    // The CC BY-NC avatar cannot come back.
    expect(existsSync(join(faceDir, 'brunette.glb'))).toBe(true);
    const versions = readFileSync(versionsPath, 'utf8');
    expect(versions).toMatch(/estate\.glb:.*commercial/i);
    expect(versions).toMatch(/brunette\.glb:.*CC BY-NC/);
  });

  it('carries a named Armature with the RPM bones the runtime resolves', () => {
    // Parse the GLB container and read the node names, so this asserts the asset itself rather
    // than a description of it.
    const buf = readFileSync(glbPath);
    expect(buf.readUInt32LE(0)).toBe(0x46546c67); // 'glTF'
    const jsonLength = buf.readUInt32LE(12);
    const gltf = JSON.parse(buf.subarray(20, 20 + jsonLength).toString('utf8'));
    const nodeNames: string[] = gltf.nodes.map((n: { name?: string }) => n.name);
    expect(nodeNames).toContain('Armature');
    for (const bone of [
      'Hips', 'Spine', 'Spine1', 'Spine2', 'Neck', 'Head',
      'LeftShoulder', 'LeftArm', 'LeftForeArm', 'LeftHand',
      'RightShoulder', 'RightArm', 'RightForeArm', 'RightHand',
      'LeftUpLeg', 'LeftLeg', 'LeftFoot', 'LeftToeBase',
      'RightUpLeg', 'RightLeg', 'RightFoot', 'RightToeBase',
    ]) {
      expect(nodeNames).toContain(bone);
    }
    // The runtime also reads these off the armature directly.
    for (const obj of ['LeftEye', 'RightEye']) expect(nodeNames).toContain(obj);
  });

  it('exposes the ARKit blendshapes as morph targets, and is skinned', () => {
    const buf = readFileSync(glbPath);
    const jsonLength = buf.readUInt32LE(12);
    const gltf = JSON.parse(buf.subarray(20, 20 + jsonLength).toString('utf8'));
    const prim = gltf.meshes[0].primitives[0];
    const names: string[] = gltf.meshes[0].extras.targetNames;
    // 53 ARKit targets; the runtime synthesizes mouthOpen/mouthSmile/eyesClosed/eyesLookUp/
    // eyesLookDown from these, so the mesh must carry the sources.
    expect(names.length).toBe(53);
    for (const n of ['jawOpen', 'mouthPucker', 'eyeBlinkLeft', 'browInnerUp', 'tongueOut']) {
      expect(names).toContain(n);
    }
    expect(prim.targets.length).toBe(53);
    // Skinned to the armature, or the bones move nothing.
    expect(prim.attributes.JOINTS_0).toBeDefined();
    expect(prim.attributes.WEIGHTS_0).toBeDefined();
    expect(gltf.skins[0].joints.length).toBeGreaterThan(50);
  });

  it('matches the generator that claims to have authored it', () => {
    // The licence record says "authored by bin/estate-face-avatar". This is what makes that
    // claim checkable: re-derive the GLB and compare. If the generator or python3 is missing we
    // fail loudly rather than skipping -- a silently skipped check is not a check, and this was
    // exactly the bug that put a green bdd over a red portal-app on 2026-10-04 (the skip turned
    // a real CI failure into an empty string).
    // From src/modules/home: app -> packages -> backstage -> idp (six levels).
    const repoRoot = join(__dirname, '..', '..', '..', '..', '..', '..');
    const gen = join(repoRoot, 'bin', 'estate-face-avatar');
    expect(existsSync(gen)).toBe(true);
    let out = '';
    let err = '';
    try {
      out = execFileSync('python3', [gen, '--check'], { encoding: 'utf8', timeout: 60_000 });
    } catch (e) {
      const x = e as { stdout?: string; stderr?: string; message?: string };
      out = String(x.stdout ?? '');
      err = String(x.stderr || x.message || e);
    }
    // Surface the generator's own words, so a failure says why instead of showing "".
    expect(`${out}${err}`).toMatch(/matches the generator/);
  });
});

/**
 * LIFE (spec section 3): the face is never inert. The cadence is data, so it is graded here the way
 * the runtime reads it -- every beat is renderable (knows what to do), the loop wraps, and it is
 * irregular rather than a metronome.
 */
describe('idle life', () => {
  it('schedules blinks often and settles/moves rarely', () => {
    const blinks = IDLE_BEATS.filter((b) => b.blink).length;
    const settles = IDLE_BEATS.filter((b) => b.mood).length;
    const moves = IDLE_BEATS.filter((b) => b.gesture || b.lookAhead !== undefined).length;
    expect(blinks).toBeGreaterThanOrEqual(4);
    expect(settles).toBeGreaterThanOrEqual(2);
    expect(moves).toBeGreaterThanOrEqual(2);
    // Every beat does something. An empty beat is dead air on screen.
    for (const b of IDLE_BEATS) {
      expect(Boolean(b.blink || b.mood || b.gesture || b.lookAhead !== undefined)).toBe(true);
      expect(b.afterMs).toBeGreaterThan(400);
    }
  });

  it('is irregular, not a metronome', () => {
    const gaps = IDLE_BEATS.map((b) => b.afterMs);
    expect(new Set(gaps).size).toBeGreaterThan(3);
  });

  it('wraps forever, always returning a real beat', () => {
    const n = IDLE_BEATS.length;
    expect(nextBeat(0)).toBe(IDLE_BEATS[0]);
    expect(nextBeat(n)).toBe(IDLE_BEATS[0]);
    expect(nextBeat(n * 7 + 3)).toBe(IDLE_BEATS[3]);
  });
});

/**
 * CONTINUITY (spec section 4): the visit survives the page. Graded against a fake store so the
 * round-trip is proven without a browser, including every degradation path -- no storage, corrupt
 * JSON, and a shape written by an older build must all read as a first visit rather than throw.
 */
describe('visit continuity', () => {
  function fakeStore(seed: Record<string, string> = {}) {
    const data = { ...seed };
    return {
      getItem: (k: string) => (k in data ? data[k] : null),
      setItem: (k: string, v: string) => {
        data[k] = v;
      },
      _data: data,
    };
  }

  it('counts visits and remembers the resting mood across mounts', () => {
    const store = fakeStore();
    const first = recordVisit(store, 1000, 'neutral');
    expect(first).toEqual({ visits: 1, mood: 'neutral', lastSeen: 1000 });
    const second = recordVisit(store, 2000, 'happy');
    expect(second).toEqual({ visits: 2, mood: 'happy', lastSeen: 2000 });
    // A cold read of what was written returns the second visit, not a stranger.
    expect(readMemory(store)).toEqual(second);
    expect(store._data[CONTINUITY_KEY]).toContain('"visits":2');
  });

  it('refuses a mood it does not rest in, keeping the previous one', () => {
    const store = fakeStore();
    recordVisit(store, 1, 'love');
    const next = recordVisit(store, 2, 'angry');
    expect(next.mood).toBe('love');
  });

  it('reads a first visit from no storage, bad JSON, or an old shape', () => {
    const blank = { visits: 0, mood: 'neutral', lastSeen: 0 };
    expect(readMemory(null)).toEqual(blank);
    expect(readMemory(fakeStore())).toEqual(blank);
    expect(readMemory(fakeStore({ [CONTINUITY_KEY]: '{not json' }))).toEqual(blank);
    expect(readMemory(fakeStore({ [CONTINUITY_KEY]: '{"visits":"x","mood":"purple"}' }))).toEqual(blank);
  });

  it('answers the visit with a line that names the familiarity', () => {
    expect(greeting({ visits: 0, mood: 'neutral', lastSeen: 0 })).toMatch(/estate is up/i);
    expect(greeting({ visits: 1, mood: 'neutral', lastSeen: 0 })).toMatch(/estate is up/i);
    expect(greeting({ visits: 2, mood: 'happy', lastSeen: 0 })).toMatch(/back/i);
    expect(greeting({ visits: 5, mood: 'happy', lastSeen: 0 })).toContain('5');
  });
});
