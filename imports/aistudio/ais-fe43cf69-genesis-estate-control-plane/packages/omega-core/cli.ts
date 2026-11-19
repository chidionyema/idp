import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import {
  createInitialOmegaCoreState,
  stepOmegaKernel,
  teleportOmegaStateAcrossDevices,
  registerCustomDeviceEmbodiment,
  synthesizeDeviceTransducerSdk,
  type OmegaCoreState,
  type OmegaTransducerTargetLang,
} from './index.ts';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, '../..');
const STATE_PATH = path.join(REPO_ROOT, '.ops', 'omega-core-state.json');

function loadState(): OmegaCoreState {
  try {
    if (fs.existsSync(STATE_PATH)) {
      return JSON.parse(fs.readFileSync(STATE_PATH, 'utf8')) as OmegaCoreState;
    }
  } catch {
    // Fall back to clean seed state
  }
  return createInitialOmegaCoreState();
}

function saveState(state: OmegaCoreState): void {
  fs.mkdirSync(path.dirname(STATE_PATH), { recursive: true });
  fs.writeFileSync(STATE_PATH, JSON.stringify(state, null, 2), 'utf8');
}

function getFlag(args: string[], flag: string, fallback: string): string {
  const idx = args.indexOf(flag);
  if (idx >= 0 && idx + 1 < args.length) return args[idx + 1];
  return fallback;
}

const [, , subcommand = 'status', ...rest] = process.argv;
const state = loadState();

if (subcommand === 'status') {
  console.log(
    JSON.stringify(
      {
        kernel: '@meridian-estate/omega-core',
        version: state.kernelVersion,
        lamportClock: state.lamportClock,
        activeEmbodimentId: state.activeEmbodimentId,
        activeSessionId: state.activeSessionId,
        activeStewardRealName: state.activeStewardRealName,
        subsystemsUnified: state.subsystems.map((s) => s.subsystemId),
        embodimentCount: state.embodiments.length,
        kernelRewriteLinesAcrossAllDevices: 0,
      },
      null,
      2
    )
  );
  process.exit(0);
}

if (subcommand === 'embodiments') {
  console.log(
    JSON.stringify(
      state.embodiments.map((e) => ({
        deviceId: e.deviceId,
        name: e.name,
        substrate: e.substrate,
        controlLoopHz: e.controlLoopHz,
        transducerLinesOfCode: e.transducerLinesOfCode,
        kernelRewriteLines: e.kernelRewriteLines,
        failSafeAction: e.safetyEnvelope.failSafeAction,
      })),
      null,
      2
    )
  );
  process.exit(0);
}

if (subcommand === 'step') {
  const deviceId = getFlag(rest, '--device', state.activeEmbodimentId);
  const breach = rest.includes('--kinetic-breach');
  const receipt = stepOmegaKernel(state, {
    deviceId,
    sessionId: state.activeSessionId,
    actorDid: state.activeStewardDid,
    actorRealName: state.activeStewardRealName,
    simulateKineticBreach: breach,
  });
  saveState(state);
  console.log(JSON.stringify(receipt, null, 2));
  process.exit(0);
}

if (subcommand === 'teleport') {
  const from = getFlag(rest, '--from', state.activeEmbodimentId);
  const to = getFlag(rest, '--to', 'optimus-humanoid-robot');
  const out = teleportOmegaStateAcrossDevices(state, {
    sourceDeviceId: from,
    targetDeviceId: to,
  });
  saveState(state);
  console.log(JSON.stringify(out, null, 2));
  process.exit(out.ok ? 0 : 1);
}

if (subcommand === 'codegen') {
  const deviceId = getFlag(rest, '--device', 'optimus-humanoid-robot');
  const rawTarget = getFlag(rest, '--target', 'WIT').toUpperCase();
  const target: OmegaTransducerTargetLang =
    rawTarget === 'C99' || rawTarget === 'C99_ABI'
      ? 'C99_ABI'
      : rawTarget === 'RUST' || rawTarget === 'RUST_NO_STD'
        ? 'RUST_NO_STD'
        : rawTarget === 'ROS2' || rawTarget === 'ROS2_PYTHON'
          ? 'ROS2_PYTHON'
          : 'WIT';
  const device = state.embodiments.find((d) => d.deviceId === deviceId) ?? state.embodiments[0];
  const sdk = synthesizeDeviceTransducerSdk(device, target);
  console.log(sdk.code);
  process.exit(0);
}

if (subcommand === 'register-device') {
  const name = getFlag(rest, '--name', 'Autonomous Marine ROV');
  const hz = Number(getFlag(rest, '--hz', '120'));
  const created = registerCustomDeviceEmbodiment(state, {
    name,
    substrate: 'C_ABI_RTOS_FLIGHT',
    controlLoopHz: hz,
    senseChannels: ['sonar-multibeam', 'depth-pressure-bar', 'thruster-current'],
    actuateChannels: ['vectored-thruster-6dof', 'manipulator-claw'],
    linkTransports: ['Acoustic-Modem-4KB', 'Tether-Ethernet'],
    maxContactForceNewtons: 25,
    maxVelocityMps: 3.2,
    minBatteryReservePct: 20,
    failSafeAction: 'POSITIVE_BUOYANCY_SURFACE_HOLD',
  });
  saveState(state);
  console.log(JSON.stringify(created, null, 2));
  process.exit(0);
}

console.error(
  'Usage: bin/omega [status | embodiments | step --device <id> [--kinetic-breach] | teleport --from <id> --to <id> | codegen --device <id> --target <WIT|C99|RUST|ROS2> | register-device --name <name>]'
);
process.exit(1);
