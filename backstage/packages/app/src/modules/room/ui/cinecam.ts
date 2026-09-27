export type Vec3 = [number, number, number];
export type Quat = [number, number, number, number];

export type ShotType = 'ORBIT_FOCUS' | 'PANORAMIC_SWEEP' | 'MACRO_DOV';

export interface Cue {
  target_id: string;
  shot_type: ShotType;
  monologue: string;
  focal_length: number;
  dolly_speed: number;
  timestamp: string;
}

export interface Pose {
  position: Vec3;
  quaternion: Quat;
  fov: number;
}

export const HOLD_S = 4;
export const SENSOR_MM = 36;

function vecSub(a: Vec3, b: Vec3): Vec3 {
  return [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
}

function vecAdd(a: Vec3, b: Vec3): Vec3 {
  return [a[0] + b[0], a[1] + b[1], a[2] + b[2]];
}

function vecScale(a: Vec3, s: number): Vec3 {
  return [a[0] * s, a[1] * s, a[2] * s];
}

function vecLen(a: Vec3): number {
  return Math.sqrt(a[0] * a[0] + a[1] * a[1] + a[2] * a[2]);
}

function vecNormalize(a: Vec3): Vec3 {
  const len = vecLen(a);
  if (len === 0) return [0, 0, 0];
  return [a[0] / len, a[1] / len, a[2] / len];
}

function vecDot(a: Vec3, b: Vec3): number {
  return a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
}

function vecCross(a: Vec3, b: Vec3): Vec3 {
  return [
    a[1] * b[2] - a[2] * b[1],
    a[2] * b[0] - a[0] * b[2],
    a[0] * b[1] - a[1] * b[0],
  ];
}

function vecLerp(a: Vec3, b: Vec3, t: number): Vec3 {
  return [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t];
}

function copyPose(p: Pose): Pose {
  return {
    position: [p.position[0], p.position[1], p.position[2]],
    quaternion: [p.quaternion[0], p.quaternion[1], p.quaternion[2], p.quaternion[3]],
    fov: p.fov,
  };
}

export function fovFor(focalMm: number): number {
  return 2 * Math.atan(SENSOR_MM / (2 * focalMm)) * (180 / Math.PI);
}

export function normalizeQuat(q: Quat): Quat {
  const len = Math.sqrt(q[0] * q[0] + q[1] * q[1] + q[2] * q[2] + q[3] * q[3]);
  if (len === 0) return [0, 0, 0, 1];
  return [q[0] / len, q[1] / len, q[2] / len, q[3] / len];
}

export function fromLookAt(eye: Vec3, target: Vec3, up: Vec3 = [0, 1, 0]): Quat {
  let z = vecSub(eye, target);
  if (vecLen(z) === 0) return [0, 0, 0, 1];
  z = vecNormalize(z);

  let useUp = up;
  if (Math.abs(vecDot(z, up)) > 0.999) {
    useUp = [0, 0, 1];
  }

  const x = vecNormalize(vecCross(useUp, z));
  const y = vecCross(z, x);

  const m00 = x[0], m01 = y[0], m02 = z[0];
  const m10 = x[1], m11 = y[1], m12 = z[1];
  const m20 = x[2], m21 = y[2], m22 = z[2];

  const trace = m00 + m11 + m22;
  let qx: number, qy: number, qz: number, qw: number;

  if (trace > 0) {
    const s = 0.5 / Math.sqrt(trace + 1.0);
    qw = 0.25 / s;
    qx = (m21 - m12) * s;
    qy = (m02 - m20) * s;
    qz = (m10 - m01) * s;
  } else if (m00 > m11 && m00 > m22) {
    const s = 2.0 * Math.sqrt(1.0 + m00 - m11 - m22);
    qw = (m21 - m12) / s;
    qx = 0.25 * s;
    qy = (m01 + m10) / s;
    qz = (m02 + m20) / s;
  } else if (m11 > m22) {
    const s = 2.0 * Math.sqrt(1.0 + m11 - m00 - m22);
    qw = (m02 - m20) / s;
    qx = (m01 + m10) / s;
    qy = 0.25 * s;
    qz = (m12 + m21) / s;
  } else {
    const s = 2.0 * Math.sqrt(1.0 + m22 - m00 - m11);
    qw = (m10 - m01) / s;
    qx = (m02 + m20) / s;
    qy = (m12 + m21) / s;
    qz = 0.25 * s;
  }

  return normalizeQuat([qx, qy, qz, qw]);
}

export function slerp(a: Quat, b: Quat, t: number): Quat {
  let [bx, by, bz, bw] = b;
  let dot = a[0] * bx + a[1] * by + a[2] * bz + a[3] * bw;

  if (dot < 0) {
    dot = -dot;
    bx = -bx;
    by = -by;
    bz = -bz;
    bw = -bw;
  }

  if (dot > 0.9995) {
    const result: Quat = [
      a[0] + (bx - a[0]) * t,
      a[1] + (by - a[1]) * t,
      a[2] + (bz - a[2]) * t,
      a[3] + (bw - a[3]) * t,
    ];
    return normalizeQuat(result);
  }

  const theta0 = Math.acos(dot);
  const theta = theta0 * t;
  const sinTheta0 = Math.sin(theta0);
  const s0 = Math.cos(theta) - (dot * Math.sin(theta)) / sinTheta0;
  const s1 = Math.sin(theta) / sinTheta0;

  const result: Quat = [
    s0 * a[0] + s1 * bx,
    s0 * a[1] + s1 * by,
    s0 * a[2] + s1 * bz,
    s0 * a[3] + s1 * bw,
  ];
  return normalizeQuat(result);
}

export function easeInOutCubic(t: number): number {
  const c = Math.min(1, Math.max(0, t));
  return c < 0.5 ? 4 * c * c * c : 1 - Math.pow(-2 * c + 2, 3) / 2;
}

export type CineState = 'idle' | 'travelling' | 'holding';

export class CineCam {
  state: CineState = 'idle';
  pose: Pose;
  from: Pose;
  goal: Pose;
  cue: Cue | null = null;
  target: Vec3 = [0, 0, 0];
  progress = 0;
  holdLeft = 0;
  orbitAngle = 0;
  radius = 0;
  lift = 0;

  constructor(initial: Pose) {
    this.pose = copyPose(initial);
    this.from = copyPose(initial);
    this.goal = copyPose(initial);
  }

  sync(p: Pose): void {
    if (this.state !== 'idle') return;
    this.pose = copyPose(p);
  }

  onCue(cue: Cue, targetPos: Vec3): boolean {
    if (cue.shot_type !== 'ORBIT_FOCUS' && cue.shot_type !== 'PANORAMIC_SWEEP' && cue.shot_type !== 'MACRO_DOV') {
      return false;
    }

    this.from = copyPose(this.pose);
    this.cue = cue;
    this.target = targetPos;

    let d: Vec3 = [this.pose.position[0] - targetPos[0], 0, this.pose.position[2] - targetPos[2]];
    if (vecLen(d) === 0) {
      d = [0, 0, 1];
    } else {
      d = vecNormalize(d);
    }
    this.orbitAngle = Math.atan2(d[2], d[0]);

    const focalLength = cue.focal_length > 0 ? cue.focal_length : 50;

    let radius: number;
    let lift: number;
    if (cue.shot_type === 'ORBIT_FOCUS') {
      radius = focalLength * 0.6;
      lift = radius * 0.35;
    } else if (cue.shot_type === 'PANORAMIC_SWEEP') {
      radius = 110;
      lift = 45;
    } else {
      radius = 12;
      lift = 3;
    }
    this.radius = radius;
    this.lift = lift;

    const goalPosition: Vec3 = vecAdd(targetPos, [
      Math.cos(this.orbitAngle) * radius,
      lift,
      Math.sin(this.orbitAngle) * radius,
    ]);

    this.goal = {
      position: goalPosition,
      quaternion: fromLookAt(goalPosition, targetPos),
      fov: fovFor(focalLength),
    };

    this.progress = 0;
    this.state = 'travelling';
    return true;
  }

  step(dt: number): Pose {
    const clampedDt = Math.min(0.25, Math.max(0, dt));

    if (this.state === 'idle') {
      return copyPose(this.pose);
    }

    if (this.state === 'travelling') {
      const dollySpeed = this.cue ? Math.min(1, Math.max(0, this.cue.dolly_speed)) : 0;
      const speed = 0.25 + dollySpeed * 1.75;
      this.progress = Math.min(1, this.progress + clampedDt * speed);
      const e = easeInOutCubic(this.progress);

      this.pose = {
        position: vecLerp(this.from.position, this.goal.position, e),
        quaternion: slerp(this.from.quaternion, this.goal.quaternion, e),
        fov: this.from.fov + (this.goal.fov - this.from.fov) * e,
      };

      if (this.progress >= 1) {
        this.state = 'holding';
        this.holdLeft = HOLD_S;
        this.pose = copyPose(this.goal);
      }

      return copyPose(this.pose);
    }

    // holding
    this.holdLeft -= clampedDt;
    if (this.cue && this.cue.shot_type === 'ORBIT_FOCUS') {
      this.orbitAngle += 0.25 * clampedDt;
      const position: Vec3 = vecAdd(this.target, [
        Math.cos(this.orbitAngle) * this.radius,
        this.lift,
        Math.sin(this.orbitAngle) * this.radius,
      ]);
      this.pose = {
        position,
        quaternion: fromLookAt(position, this.target),
        fov: this.pose.fov,
      };
    }
    if (this.holdLeft <= 0) {
      this.state = 'idle';
    }
    return copyPose(this.pose);
  }
}
