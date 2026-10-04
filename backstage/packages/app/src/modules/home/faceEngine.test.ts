import { readFileSync, existsSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { join } from 'node:path';
import { wordTimings } from './faceEngine';

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
    expect(existsSync(join(faceDir, 'brunette.glb'))).toBe(false);
    const versions = readFileSync(versionsPath, 'utf8');
    expect(versions).toMatch(/estate\.glb:.*commercial/i);
    expect(versions).not.toMatch(/brunette/);
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
