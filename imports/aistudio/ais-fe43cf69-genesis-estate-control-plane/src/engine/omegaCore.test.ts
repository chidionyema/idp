import test from 'node:test';
import assert from 'node:assert/strict';
import {
  OMEGA_CAPSULE_MAX_BYTES,
  createInitialOmegaCoreState,
  stepOmegaKernel,
  packOmegaTeleportCapsule,
  verifyAndHydrateOmegaCapsule,
  teleportOmegaStateAcrossDevices,
  registerCustomDeviceEmbodiment,
  synthesizeDeviceTransducerSdk,
} from './omegaCore';

test('Omega Ring-0 Kernel executes identically across all 7 built-in surfaces (Laptop, Web, Phone, Glasses, Camera, Drone, Humanoid) with 0 kernel rewrites', () => {
  const state = createInitialOmegaCoreState('2026-11-12T08:30:00.000Z');
  assert.equal(state.subsystems.length, 5);
  assert.equal(state.embodiments.length, 7);

  for (const device of state.embodiments) {
    assert.equal(device.kernelRewriteLines, 0);
    const receipt = stepOmegaKernel(state, {
      deviceId: device.deviceId,
      sessionId: 'ses-aurelius-io-01',
      actorDid: 'did:estate:principal:aurelius-marcus',
      actorRealName: 'Aurelius Marcus (Chief Principal)',
    });
    assert.equal(receipt.safetyVerdict, 'PERMIT_NOMINAL');
    assert.equal(receipt.trainingDatasetKind, 'SFT_GOLD_TRAJECTORY');
    assert.equal(receipt.proofSha256.length, 64);
  }
});

test('omega::law Kinetic & Digital Geburah clamps unsafe >18N robotic torque, drone envelope breaches, and unowned sessions into Fail-Safe + Antibody', () => {
  const state = createInitialOmegaCoreState('2026-11-12T08:30:00.000Z');

  // 1. Humanoid kinetic breach (>18N contact force + <0.45m human proximity) triggers ZERO_TORQUE_COMPLIANT_IMPEDANCE_HOLD
  const robotBlocked = stepOmegaKernel(state, {
    deviceId: 'optimus-humanoid-robot',
    sessionId: 'ses-aurelius-io-01',
    actorDid: 'did:estate:principal:aurelius-marcus',
    actorRealName: 'Aurelius Marcus (Chief Principal)',
    simulateKineticBreach: true,
  });
  assert.equal(robotBlocked.safetyVerdict, 'HALT_KINETIC_SAFETY_ENVELOPE');
  assert.match(robotBlocked.effectiveActuation, /ZERO_TORQUE_COMPLIANT_IMPEDANCE_HOLD/);
  assert.equal(robotBlocked.trainingDatasetKind, 'DPO_REJECTION_PAIR');
  assert.ok(robotBlocked.synthesizedAntibodyId?.startsWith('AB-OMEGA-'));
  assert.ok(robotBlocked.safetyReasons.length >= 2);

  // 2. Unowned / sessionless hardware actuation attempt is blocked by AGENTS.md Line-1 law
  const unownedBlocked = stepOmegaKernel(state, {
    deviceId: 'aerial-uav-drone',
    sessionId: null,
    actorDid: 'anonymous',
    actorRealName: 'Anonymous',
    simulateUnownedSession: true,
  });
  assert.equal(unownedBlocked.safetyVerdict, 'HALT_ESTATE_LAW_UNOWNED');
  assert.match(unownedBlocked.effectiveActuation, /RTL_HOVER_AT_SAFE_ALTITUDE/);
});

test('Omega <= 4,096 B Capsule teleports live mission & Lamport clock across Laptop -> AR Glasses -> Humanoid and rejects tampered digests', () => {
  const state = createInitialOmegaCoreState('2026-11-12T08:30:00.000Z');
  const priorClock = state.lamportClock;

  const hop1 = teleportOmegaStateAcrossDevices(state, {
    sourceDeviceId: 'macbook-host-daemon',
    targetDeviceId: 'spatial-ar-glasses',
    missionObjective: 'Inspect warehouse aisle B4 via AR visor and hand off pick target to Optimus.',
  });
  assert.equal(hop1.ok, true);
  assert.ok(hop1.capsule.byteLength <= OMEGA_CAPSULE_MAX_BYTES);
  assert.equal(state.activeEmbodimentId, 'spatial-ar-glasses');
  assert.ok(state.lamportClock > priorClock);

  const hop2 = teleportOmegaStateAcrossDevices(state, {
    sourceDeviceId: 'spatial-ar-glasses',
    targetDeviceId: 'optimus-humanoid-robot',
  });
  assert.equal(hop2.ok, true);
  assert.equal(state.activeEmbodimentId, 'optimus-humanoid-robot');
  assert.equal(
    state.activeMissionObjective,
    'Inspect warehouse aisle B4 via AR visor and hand off pick target to Optimus.'
  );

  // Tamper with payloadJson and verify hydration deterministically fails closed
  const rawCapsule = packOmegaTeleportCapsule(state, {
    sourceDeviceId: 'optimus-humanoid-robot',
    targetDeviceId: 'mobile-field-phone',
  });
  const tampered = {
    ...rawCapsule,
    payloadJson: rawCapsule.payloadJson.replace('mobile-field-phone', 'hijacked-device'),
    byteLength: new TextEncoder().encode(
      rawCapsule.payloadJson.replace('mobile-field-phone', 'hijacked-device')
    ).byteLength,
  };
  const rejected = verifyAndHydrateOmegaCapsule(state, tampered);
  assert.equal(rejected.ok, false);
  assert.match(rejected.reason ?? '', /TAMPER_DETECTED/);
});

test('Unimagined Future Device onboarding registers custom hardware with 0 kernel rewrites and synthesizes WIT, C99, Rust no_std, and ROS2 transducers', () => {
  const state = createInitialOmegaCoreState('2026-11-12T08:30:00.000Z');
  const rov = registerCustomDeviceEmbodiment(state, {
    name: 'Subsea Inspection ROV',
    substrate: 'C_ABI_RTOS_FLIGHT',
    controlLoopHz: 200,
    senseChannels: ['multibeam-sonar', 'hull-ultrasonic-gauge'],
    actuateChannels: ['vectored-thrusters-6dof', 'ndt-probe-arm'],
    linkTransports: ['Acoustic-4KB-Link', 'Fiber-Tether'],
    maxContactForceNewtons: 30,
    maxVelocityMps: 2.5,
    minBatteryReservePct: 20,
    failSafeAction: 'POSITIVE_BUOYANCY_ASCENT',
  });

  assert.equal(rov.deviceId, 'subsea-inspection-rov');
  assert.equal(rov.kernelRewriteLines, 0);
  assert.equal(state.embodiments.length, 8);

  const tick = stepOmegaKernel(state, {
    deviceId: rov.deviceId,
    sessionId: 'ses-aurelius-io-01',
    actorDid: 'did:estate:principal:aurelius-marcus',
    actorRealName: 'Aurelius Marcus (Chief Principal)',
  });
  assert.equal(tick.safetyVerdict, 'PERMIT_NOMINAL');

  for (const target of ['WIT', 'C99_ABI', 'RUST_NO_STD', 'ROS2_PYTHON'] as const) {
    const sdk = synthesizeDeviceTransducerSdk(rov, target);
    assert.ok(sdk.code.includes('subsea-inspection-rov') || sdk.code.includes('Subsea Inspection ROV'));
    assert.ok(sdk.code.includes('POSITIVE_BUOYANCY_ASCENT'));
  }
});
