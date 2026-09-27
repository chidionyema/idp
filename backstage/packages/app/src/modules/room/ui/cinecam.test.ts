import { CineCam, fovFor, fromLookAt, slerp } from './cinecam';
import type { Cue } from './cinecam';

describe('fovFor', () => {
  it('matches expected fov for 50mm', () => {
    expect(fovFor(50)).toBeCloseTo(39.6, 1);
  });
});

describe('fromLookAt', () => {
  it('looking down -Z from (0,0,10) toward origin gives identity-like quaternion', () => {
    const q = fromLookAt([0, 0, 10], [0, 0, 0]);
    expect(q[0]).toBeCloseTo(0, 3);
    expect(q[1]).toBeCloseTo(0, 3);
    expect(q[2]).toBeCloseTo(0, 3);
    expect(q[3]).toBeCloseTo(1, 3);
  });
});

describe('slerp', () => {
  it('endpoints match inputs', () => {
    const a: [number, number, number, number] = [0, 0, 0, 1];
    const b = fromLookAt([10, 0, 0], [0, 0, 0]);

    const at0 = slerp(a, b, 0);
    expect(at0[0]).toBeCloseTo(a[0], 3);
    expect(at0[1]).toBeCloseTo(a[1], 3);
    expect(at0[2]).toBeCloseTo(a[2], 3);
    expect(at0[3]).toBeCloseTo(a[3], 3);

    const at1 = slerp(a, b, 1);
    expect(at1[0]).toBeCloseTo(b[0], 3);
    expect(at1[1]).toBeCloseTo(b[1], 3);
    expect(at1[2]).toBeCloseTo(b[2], 3);
    expect(at1[3]).toBeCloseTo(b[3], 3);

    const mid = slerp(a, b, 0.5);
    const len = Math.sqrt(mid[0] * mid[0] + mid[1] * mid[1] + mid[2] * mid[2] + mid[3] * mid[3]);
    expect(len).toBeCloseTo(1, 4);
  });

  it('takes the shortest path on sign flip', () => {
    const result = slerp([0, 0, 0, 1], [0, 0, 0, -1], 0.5);
    expect(result[3]).toBeCloseTo(1, 4);

    const b: [number, number, number, number] = [0, -0.7071068, 0, -0.7071068];
    const result2 = slerp([0, 0, 0, 1], b, 0.5);
    expect(result2[3]).toBeGreaterThan(0);
  });
});

describe('CineCam state machine', () => {
  it('runs idle -> travelling -> holding -> idle', () => {
    const cam = new CineCam({ position: [0, 30, 90], quaternion: [0, 0, 0, 1], fov: 50 });
    expect(cam.state).toBe('idle');

    const bogus = {
      target_id: 't1',
      shot_type: 'BOGUS' as unknown as Cue['shot_type'],
      monologue: '',
      focal_length: 50,
      dolly_speed: 0.5,
      timestamp: '2026-09-27T00:00:00Z',
    };
    expect(cam.onCue(bogus, [0, 0, 0])).toBe(false);
    expect(cam.state).toBe('idle');

    const cue: Cue = {
      target_id: 't1',
      shot_type: 'MACRO_DOV',
      monologue: 'close up',
      focal_length: 85,
      dolly_speed: 0.2,
      timestamp: '2026-09-27T00:00:00Z',
    };
    expect(cam.onCue(cue, [10, 0, 0])).toBe(true);
    expect(cam.state).toBe('travelling');

    for (let i = 0; i < 8; i++) {
      cam.step(0.25);
    }
    expect(cam.state).toBe('holding');

    const target = [10, 0, 0];
    const dx = cam.pose.position[0] - target[0];
    const dy = cam.pose.position[1] - target[1];
    const dz = cam.pose.position[2] - target[2];
    const dist = Math.sqrt(dx * dx + dy * dy + dz * dz);
    expect(dist).toBeCloseTo(Math.sqrt(12 * 12 + 3 * 3), 1);
    expect(cam.pose.fov).toBeCloseTo(fovFor(85), 2);

    for (let i = 0; i < 16; i++) {
      cam.step(0.25);
    }
    expect(cam.state).toBe('idle');
  });

  it('ignores sync while travelling', () => {
    const cam = new CineCam({ position: [0, 30, 90], quaternion: [0, 0, 0, 1], fov: 50 });
    const cue: Cue = {
      target_id: 't1',
      shot_type: 'MACRO_DOV',
      monologue: 'close up',
      focal_length: 85,
      dolly_speed: 0.2,
      timestamp: '2026-09-27T00:00:00Z',
    };
    cam.onCue(cue, [10, 0, 0]);
    cam.sync({ position: [999, 999, 999], quaternion: [0, 0, 0, 1], fov: 50 });
    const pose = cam.step(0.01);
    expect(pose.position[0]).toBeLessThan(900);
  });

  it('ORBIT_FOCUS keeps orbiting while holding', () => {
    const cam = new CineCam({ position: [0, 30, 90], quaternion: [0, 0, 0, 1], fov: 50 });
    const cue: Cue = {
      target_id: 't1',
      shot_type: 'ORBIT_FOCUS',
      monologue: 'orbit',
      focal_length: 50,
      dolly_speed: 0.5,
      timestamp: '2026-09-27T00:00:00Z',
    };
    cam.onCue(cue, [0, 0, 0]);

    for (let i = 0; i < 5; i++) {
      cam.step(0.25);
    }
    expect(cam.state).toBe('holding');

    const before = cam.pose.position;
    cam.step(0.25);
    const after = cam.pose.position;

    expect(Math.abs(after[0] - before[0])).toBeGreaterThan(0.01);

    const radiusXZ = Math.sqrt(after[0] * after[0] + after[2] * after[2]);
    expect(radiusXZ).toBeCloseTo(50 * 0.6, 1);
  });
});
