import React, { useState, useEffect } from 'react';
import {
  Download,
  Play,
  ShieldAlert,
  ArrowRightLeft,
  Plus,
  Copy,
  Check,
  Terminal,
  FileCode2,
} from 'lucide-react';
import {
  synthesizeDeviceTransducerSdk,
  type OmegaCoreState,
  type OmegaSubstrateClass,
  type OmegaTransducerTargetLang,
  type OmegaKernelTickReceipt,
  type OmegaTeleportCapsule,
} from '../engine/omegaCore';

interface OmegaUniversalCoreViewProps {
  initialOmega: OmegaCoreState;
  onRefreshState: () => Promise<void>;
  onOpenIoGraph: () => void;
}

const SUBSTRATE_OPTIONS: Array<{ value: OmegaSubstrateClass; label: string }> = [
  { value: 'C_ABI_RTOS_FLIGHT', label: 'C99 / RTOS Bare-Metal (Drones, Rovers, Microcontrollers)' },
  { value: 'ROS2_RT_HUMANOID', label: 'ROS 2 PREEMPT_RT (Humanoid & Industrial Robotics)' },
  { value: 'OPENXR_SPATIAL_VISOR', label: 'OpenXR + WASI (Smart Glasses, Headsets, HUDs)' },
  { value: 'WASI_NN_CAMERA_ISP', label: 'ARM WASI-NN / ISP (Smart Cameras & Optical Sensors)' },
  { value: 'WASI_MOBILE_SANDBOX', label: 'WASI Mobile Sandbox (iOS & Android Field Nodes)' },
  { value: 'POSIX_DAEMON', label: 'POSIX Native Daemon (macOS, Linux, Edge Appliances)' },
  { value: 'WASM_BROWSER_CLOUD', label: 'WASM Component (Web Surfaces & Cloud Workers)' },
];

export const OmegaUniversalCoreView: React.FC<OmegaUniversalCoreViewProps> = ({
  initialOmega,
  onRefreshState,
  onOpenIoGraph,
}) => {
  const [omega, setOmega] = useState<OmegaCoreState>(initialOmega);
  const [selectedDeviceId, setSelectedDeviceId] = useState<string>(
    initialOmega.activeEmbodimentId || 'optimus-humanoid-robot'
  );
  const [teleportSourceId, setTeleportSourceId] = useState<string>('macbook-host-daemon');
  const [teleportTargetId, setTeleportTargetId] = useState<string>('spatial-ar-glasses');
  const [teleportMission, setTeleportMission] = useState<string>(
    initialOmega.activeMissionObjective
  );

  const [codegenTarget, setCodegenTarget] = useState<OmegaTransducerTargetLang>('WIT');
  const [copiedCode, setCopiedCode] = useState(false);

  // Custom Future Device Registration Form State
  const [customName, setCustomName] = useState('Subsea Hull Inspection ROV');
  const [customSubstrate, setCustomSubstrate] =
    useState<OmegaSubstrateClass>('C_ABI_RTOS_FLIGHT');
  const [customHz, setCustomHz] = useState('200');
  const [customSensors, setCustomSensors] = useState(
    'multibeam-sonar, depth-pressure-bar, hull-ultrasonic-gauge'
  );
  const [customActuators, setCustomActuators] = useState(
    'vectored-thrusters-6dof, manipulator-ndt-arm'
  );
  const [customMaxForce, setCustomMaxForce] = useState('28');
  const [customMaxVel, setCustomMaxVel] = useState('2.4');
  const [customFailsafe, setCustomFailsafe] = useState('POSITIVE_BUOYANCY_SURFACE_HOLD');
  const [formValidationError, setFormValidationError] = useState<string | null>(null);

  const [busy, setBusy] = useState(false);
  const [statusMessage, setStatusMessage] = useState<{
    tone: 'emerald' | 'amber' | 'rose';
    text: string;
  } | null>(null);

  useEffect(() => {
    setOmega(initialOmega);
  }, [initialOmega]);

  useEffect(() => {
    const es = new EventSource('/api/brain/stream');
    const onPulse = (ev: MessageEvent) => {
      try {
        const parsed = JSON.parse(ev.data) as { omegaCore?: OmegaCoreState };
        if (parsed.omegaCore) {
          setOmega(parsed.omegaCore);
        }
      } catch {
        // Ignore malformed SSE payload
      }
    };
    es.addEventListener('omega-pulse', onPulse);
    return () => {
      es.removeEventListener('omega-pulse', onPulse);
      es.close();
    };
  }, []);

  const selectedDevice =
    omega.embodiments.find((d) => d.deviceId === selectedDeviceId) ?? omega.embodiments[0];

  const latestCapsule: OmegaTeleportCapsule | undefined = omega.teleportHistory[0];
  const latestTick: OmegaKernelTickReceipt | undefined = omega.tickReceipts[0];
  const generatedSdk = synthesizeDeviceTransducerSdk(selectedDevice, codegenTarget);

  const totalTransducerLoc = omega.embodiments.reduce(
    (sum, d) => sum + d.transducerLinesOfCode,
    0
  );
  const blockedSafetyCount = omega.tickReceipts.filter(
    (r) => r.safetyVerdict !== 'PERMIT_NOMINAL'
  ).length;

  const handleStepDevice = async (simulateKineticBreach = false) => {
    setBusy(true);
    setStatusMessage(null);
    try {
      const res = await fetch('/api/omega/step', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          deviceId: selectedDevice.deviceId,
          simulateKineticBreach,
        }),
      });
      const data = await res.json();
      if (data.omegaCore) setOmega(data.omegaCore as OmegaCoreState);
      const tick = data.receipt as OmegaKernelTickReceipt | undefined;
      if (tick) {
        const passed = tick.safetyVerdict === 'PERMIT_NOMINAL';
        setStatusMessage({
          tone: passed ? 'emerald' : 'amber',
          text: passed
            ? `[${tick.tickId} · ${tick.controlLoopHz} Hz] Nominal Ring-0 execution on ${tick.deviceName} -> ${tick.effectiveActuation} (Proof ${tick.proofSha256.slice(0, 12)} · SFT +1.0).`
            : `[${tick.tickId} · GEBURAH CLAMPED] ${tick.safetyReasons.join(' ')} -> ${tick.effectiveActuation} (Synthesized ${tick.synthesizedAntibodyId} · DPO -1.0).`,
        });
      }
      await onRefreshState();
    } finally {
      setBusy(false);
    }
  };

  const handleTeleportCapsule = async () => {
    if (teleportSourceId === teleportTargetId) {
      setStatusMessage({
        tone: 'amber',
        text: 'Select distinct Source and Target devices to teleport the <= 4,096 B Omega Capsule.',
      });
      return;
    }
    setBusy(true);
    setStatusMessage(null);
    try {
      const res = await fetch('/api/omega/teleport', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sourceDeviceId: teleportSourceId,
          targetDeviceId: teleportTargetId,
          missionObjective: teleportMission,
        }),
      });
      const data = await res.json();
      if (data.omegaCore) setOmega(data.omegaCore as OmegaCoreState);
      setSelectedDeviceId(teleportTargetId);
      if (data.capsule) {
        const cap = data.capsule as OmegaTeleportCapsule;
        setStatusMessage({
          tone: 'emerald',
          text: `Teleported ${cap.capsuleId} (${cap.byteLength} B / 4,096 B) from ${cap.sourceDeviceId} -> ${cap.targetDeviceId} via ${cap.transportUsed} at Lamport #${cap.lamportClock} (0 kernel lines changed).`,
        });
      }
      await onRefreshState();
    } finally {
      setBusy(false);
    }
  };

  const handleRegisterFutureDevice = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormValidationError(null);
    if (!customName.trim()) {
      setFormValidationError('Device name is required to synthesize a hardware transducer.');
      return;
    }
    const sensors = customSensors
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean);
    const actuators = customActuators
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean);
    if (sensors.length === 0 || actuators.length === 0) {
      setFormValidationError(
        'Specify at least one Sense channel and one Actuate channel (comma-separated).'
      );
      return;
    }

    setBusy(true);
    setStatusMessage(null);
    try {
      const res = await fetch('/api/omega/register-device', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: customName.trim(),
          substrate: customSubstrate,
          controlLoopHz: Number(customHz) || 100,
          senseChannels: sensors,
          actuateChannels: actuators,
          linkTransports: ['Omega-4KB-Capsule-Mesh', 'mTLS-Telemetry'],
          maxContactForceNewtons: Number(customMaxForce) || 0,
          maxVelocityMps: Number(customMaxVel) || 0,
          minBatteryReservePct: 18,
          failSafeAction: customFailsafe.trim() || 'SAFE_HOLD_ZERO_ENERGY',
        }),
      });
      const data = await res.json();
      if (data.omegaCore) setOmega(data.omegaCore as OmegaCoreState);
      if (data.embodiment?.deviceId) {
        setSelectedDeviceId(data.embodiment.deviceId);
        setTeleportTargetId(data.embodiment.deviceId);
        setStatusMessage({
          tone: 'emerald',
          text: `Onboarded "${data.embodiment.name}" (${data.embodiment.controlLoopHz} Hz · ${data.embodiment.transducerLinesOfCode} LOC thin HAL glue · 0 lines of Omega Core modified).`,
        });
      }
      await onRefreshState();
    } finally {
      setBusy(false);
    }
  };

  const handleCopyGeneratedSdk = async () => {
    try {
      await navigator.clipboard.writeText(generatedSdk.code);
      setCopiedCode(true);
      window.setTimeout(() => setCopiedCode(false), 2000);
    } catch {
      setStatusMessage({
        tone: 'amber',
        text: `Generated ${generatedSdk.filename} ready in preview panel below.`,
      });
    }
  };

  return (
    <div className="space-y-6">
      {/* Executive Header: Codename OMEGA — The Binding Product */}
      <section
        aria-labelledby="omega-core-heading"
        className="bg-white dark:bg-[#0B101D] border border-slate-200 dark:border-slate-800 rounded-xl p-5 space-y-4"
      >
        <div className="flex flex-col xl:flex-row xl:items-start xl:justify-between gap-4 pb-4 border-b border-slate-200 dark:border-slate-800">
          <div className="space-y-1.5">
            <div className="flex flex-wrap items-center gap-2 text-xs font-mono text-amber-600 dark:text-amber-400 tabular-nums">
              <span>CODENAME: OMEGA (@meridian-estate/omega-core)</span>
              <span aria-hidden="true">·</span>
              <span>RING-0 PORTABLE MICROKERNEL (WASI + C99 ABI)</span>
              <span aria-hidden="true">·</span>
              <span>0 KERNEL REWRITES ACROSS HARDWARE</span>
            </div>
            <h1
              id="omega-core-heading"
              className="text-xl font-semibold text-slate-900 dark:text-slate-50 max-w-4xl"
            >
              Omega Universal Core: One Sovereign Kernel Across Laptops, Phones, Smart Glasses, Cameras, Drones &amp; Robotics
            </h1>
            <p className="text-xs text-slate-600 dark:text-slate-400 max-w-4xl leading-relaxed">
              Binds Chronos &amp; Tempo (<code className="font-mono">omega::time</code>), Estate Law &amp; Identity (
              <code className="font-mono">omega::law</code>), Genesis + IO (<code className="font-mono">omega::mind</code>),
              and 4 KB Spore + Antibody Training (<code className="font-mono">omega::memory</code>) into a single
              substrate-independent engine. New hardware implements only 3 thin transducer functions (
              <code className="font-mono">sense</code>, <code className="font-mono">actuate</code>,{' '}
              <code className="font-mono">link</code>) — you never build from scratch again.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2 shrink-0">
            <a
              href="/api/argon/export.tar.gz"
              download="omega-genesis-2100-complete.tar.gz"
              className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-semibold text-slate-950 bg-amber-400 hover:bg-amber-300 rounded-lg transition-colors whitespace-nowrap shrink-0"
            >
              <Download className="w-3.5 h-3.5" aria-hidden="true" />
              Download Omega + Estate (.tar.gz)
            </a>

            <a
              href="/api/omega/wit"
              download="omega.wit"
              className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-medium text-slate-800 dark:text-slate-100 bg-slate-100 dark:bg-slate-900 hover:bg-slate-200 dark:hover:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg transition-colors whitespace-nowrap shrink-0"
            >
              <FileCode2 className="w-3.5 h-3.5 text-cyan-600 dark:text-cyan-400" aria-hidden="true" />
              omega.wit
            </a>

            <a
              href="/api/omega/c-header"
              download="omega_hal.h"
              className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-medium text-slate-800 dark:text-slate-100 bg-slate-100 dark:bg-slate-900 hover:bg-slate-200 dark:hover:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg transition-colors whitespace-nowrap shrink-0"
            >
              <Terminal className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" aria-hidden="true" />
              omega_hal.h (C99/RTOS)
            </a>

            <button
              type="button"
              onClick={onOpenIoGraph}
              className="px-3 py-2 text-xs font-medium text-slate-700 dark:text-slate-200 bg-slate-100 dark:bg-slate-900 hover:bg-slate-200 dark:hover:bg-slate-800 border border-slate-200 dark:border-slate-800 rounded-lg transition-colors whitespace-nowrap shrink-0"
            >
              15-Pack Work Graph
            </button>
          </div>
        </div>

        {/* 4 Calibrated Tabular KPIs */}
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-3.5 font-mono tabular-nums">
          <div className="p-3.5 rounded-lg bg-slate-50 dark:bg-[#070B14] border border-slate-200 dark:border-slate-800/90 space-y-1">
            <div className="text-[11px] text-slate-500 dark:text-slate-400">
              ACTIVE DEVICE EMBODIMENTS
            </div>
            <div className="text-sm font-semibold text-slate-900 dark:text-slate-100">
              {omega.embodiments.length} Surfaces (10 Hz – 500 Hz)
            </div>
            <div className="text-[11px] text-emerald-600 dark:text-emerald-400">
              0 Kernel Lines Rewritten ({totalTransducerLoc} HAL LOC)
            </div>
          </div>

          <div className="p-3.5 rounded-lg bg-slate-50 dark:bg-[#070B14] border border-slate-200 dark:border-slate-800/90 space-y-1">
            <div className="text-[11px] text-slate-500 dark:text-slate-400">
              UNIFIED KERNEL SUBSYSTEMS
            </div>
            <div className="text-sm font-semibold text-cyan-700 dark:text-cyan-400">
              5 Syscall Domains · 15 Packs
            </div>
            <div className="text-[11px] text-slate-500 dark:text-slate-400">
              Time · Law · Mind · Memory · HAL
            </div>
          </div>

          <div className="p-3.5 rounded-lg bg-slate-50 dark:bg-[#070B14] border border-slate-200 dark:border-slate-800/90 space-y-1">
            <div className="text-[11px] text-slate-500 dark:text-slate-400">
              CROSS-DEVICE CAPSULE TELEPORT
            </div>
            <div className="text-sm font-semibold text-slate-900 dark:text-slate-100">
              {latestCapsule ? `${latestCapsule.byteLength} B / 4,096 B` : '<= 4,096 B Cap'}
            </div>
            <div className="text-[11px] text-amber-600 dark:text-amber-400">
              Lamport #{omega.lamportClock} · Active: {omega.activeEmbodimentId}
            </div>
          </div>

          <div className="p-3.5 rounded-lg bg-slate-50 dark:bg-[#070B14] border border-slate-200 dark:border-slate-800/90 space-y-1">
            <div className="text-[11px] text-slate-500 dark:text-slate-400">
              DIGITAL &amp; KINETIC SAFETY GATE
            </div>
            <div className="text-sm font-semibold text-emerald-700 dark:text-emerald-400">
              {omega.tickReceipts.length} Ticks · {blockedSafetyCount} Clamped Safe
            </div>
            <div className="text-[11px] text-slate-500 dark:text-slate-400">
              ISO-15066 &lt;=18N + Session Enforced
            </div>
          </div>
        </div>
      </section>

      {/* SECTION 01: ARCHITECTURAL CLARITY — WHY MODULE/DAEMON ALONE WAS INCOMPLETE & HOW 3 RINGS SOLVE IT */}
      <section
        aria-labelledby="omega-rings-heading"
        className="bg-white dark:bg-[#0B101D] border border-slate-200 dark:border-slate-800 rounded-xl p-5 space-y-4"
      >
        <div className="space-y-1 pb-3 border-b border-slate-200 dark:border-slate-800">
          <div className="text-xs font-mono text-cyan-700 dark:text-cyan-400 tabular-nums">
            01. Architecture &amp; Product Unification
          </div>
          <h2
            id="omega-rings-heading"
            className="text-base font-semibold text-slate-900 dark:text-slate-50"
          >
            Why a Plain Module or Daemon Breaks Across Hardware — and How Omega’s 3-Ring Kernel Binds Everything
          </h2>
          <p className="text-xs text-slate-600 dark:text-slate-400 max-w-4xl leading-relaxed">
            A code module is trapped in one language; an OS daemon is trapped on laptops/servers; an app traps your brain inside
            one screen. Omega separates your permanent intelligence (<strong>Ring 0</strong>) from the runtime shell (
            <strong>Ring 1</strong>) and thin hardware drivers (<strong>Ring 2</strong>).
          </p>
        </div>

        {/* 3 Rings Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div className="p-4 rounded-lg bg-slate-50 dark:bg-[#070B14] border border-slate-200 dark:border-slate-800 space-y-1.5">
            <div className="text-xs font-mono font-semibold text-amber-600 dark:text-amber-400">
              Ring 0 · Omega Core (Portable Microkernel)
            </div>
            <div className="text-sm font-semibold text-slate-900 dark:text-slate-100">
              100% Hardware-Blind Pure State Machine
            </div>
            <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
              Compiles once to <code className="font-mono">omega-core.wasm</code> (Web, Phone, Smart Glasses, Cloud) and{' '}
              <code className="font-mono">libomega.a</code> C99/Rust <code className="font-mono">no_std</code> (Cameras,
              PX4 Drones, ROS 2 Humanoids). Zero UI, zero sockets, zero hardware imports.
            </p>
          </div>

          <div className="p-4 rounded-lg bg-slate-50 dark:bg-[#070B14] border border-slate-200 dark:border-slate-800 space-y-1.5">
            <div className="text-xs font-mono font-semibold text-cyan-700 dark:text-cyan-400">
              Ring 1 · Omega Host Runner (Daemon / App / RTOS)
            </div>
            <div className="text-sm font-semibold text-slate-900 dark:text-slate-100">
              Thin Execution Carrier Per Environment
            </div>
            <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
              Runs as a background <code className="font-mono">bin/omega</code> daemon on MacBook/Linux, a Service Worker in
              Cloud/Web, a WASI sandbox on iOS/Android/Visors, or a 250–500 Hz real-time timer on Drones and Robots.
            </p>
          </div>

          <div className="p-4 rounded-lg bg-slate-50 dark:bg-[#070B14] border border-slate-200 dark:border-slate-800 space-y-1.5">
            <div className="text-xs font-mono font-semibold text-emerald-700 dark:text-emerald-400">
              Ring 2 · Omega HAL Transducer (&lt; 125 LOC / Device)
            </div>
            <div className="text-sm font-semibold text-slate-900 dark:text-slate-100">
              Only 3 Functions Written For Any New Device
            </div>
            <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
              Every current or future unimagined device implements only <code className="font-mono">sense()</code>,{' '}
              <code className="font-mono">actuate(verified_intent)</code>, and <code className="font-mono">link(capsule_4kb)</code>.
              Protocols, Ways of Working, Eval, and Safety travel automatically.
            </p>
          </div>
        </div>

        {/* 5 Unified Subsystems Table */}
        <div className="overflow-x-auto border border-slate-200 dark:border-slate-800 rounded-lg">
          <table className="w-full text-left border-collapse text-xs tabular-nums">
            <thead>
              <tr className="border-b border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-[#070B14] text-slate-500 dark:text-slate-400 font-mono">
                <th className="py-2.5 px-3 font-medium">Ring-0 Syscall</th>
                <th className="py-2.5 px-3 font-medium">Existing Machinery Unified</th>
                <th className="py-2.5 px-3 font-medium">Packs</th>
                <th className="py-2.5 px-3 font-medium">Role Across Devices, Drones &amp; Robotics</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
              {omega.subsystems.map((sub) => (
                <tr key={sub.subsystemId} className="hover:bg-slate-50/80 dark:hover:bg-slate-900/40">
                  <td className="py-2.5 px-3 font-mono font-semibold text-amber-600 dark:text-amber-400 whitespace-nowrap">
                    {sub.subsystemId}
                  </td>
                  <td className="py-2.5 px-3">
                    <div className="font-semibold text-slate-900 dark:text-slate-100">
                      {sub.legacyMachineryUnified}
                    </div>
                    <div className="text-[11px] text-slate-500 dark:text-slate-400">
                      {sub.kernelResponsibility}
                    </div>
                  </td>
                  <td className="py-2.5 px-3 font-mono text-cyan-700 dark:text-cyan-400 whitespace-nowrap">
                    {sub.canonicalPacksBound.join(' · ')}
                  </td>
                  <td className="py-2.5 px-3 text-slate-700 dark:text-slate-300 leading-relaxed">
                    {sub.roboticsAndDeviceRole}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* SECTION 02: LIVE MULTI-SURFACE EMBODIMENT MATRIX & KINETIC SAFETY STEPPER */}
      <section
        aria-labelledby="omega-embodiments-heading"
        className="bg-white dark:bg-[#0B101D] border border-slate-200 dark:border-slate-800 rounded-xl p-5 space-y-4"
      >
        <div className="flex flex-col xl:flex-row xl:items-start xl:justify-between gap-4 pb-3 border-b border-slate-200 dark:border-slate-800">
          <div className="space-y-1">
            <div className="text-xs font-mono text-cyan-700 dark:text-cyan-400 tabular-nums">
              02. Live Multi-Surface Embodiment &amp; Kinetic Safety Gate
            </div>
            <h2
              id="omega-embodiments-heading"
              className="text-base font-semibold text-slate-900 dark:text-slate-50"
            >
              Same Unmodified Omega Kernel Running Across {omega.embodiments.length} Hardware Embodiments
            </h2>
            <p className="text-xs text-slate-600 dark:text-slate-400 max-w-3xl">
              Select any surface below and step the Ring-0 kernel, or inject a physical safety breach (&gt;18 N force,
              geofence, or battery sag) to verify deterministic fail-safe clamping and Pass-0 Antibody training.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2 shrink-0">
            <button
              type="button"
              disabled={busy}
              onClick={() => handleStepDevice(false)}
              className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold text-slate-950 bg-amber-400 hover:bg-amber-300 disabled:opacity-40 rounded-lg transition-colors whitespace-nowrap shrink-0"
            >
              <Play className="w-3.5 h-3.5" aria-hidden="true" />
              Step Kernel on {selectedDevice.name.split(' ')[0]} ({selectedDevice.controlLoopHz} Hz)
            </button>

            <button
              type="button"
              disabled={busy}
              onClick={() => handleStepDevice(true)}
              className="px-3 py-2 text-xs font-semibold text-rose-800 dark:text-rose-200 bg-rose-50 dark:bg-rose-950/50 hover:bg-rose-100 dark:hover:bg-rose-900/60 border border-rose-300 dark:border-rose-800 rounded-lg transition-colors whitespace-nowrap shrink-0"
            >
              Test Kinetic Safety Breach (Must Clamp)
            </button>
          </div>
        </div>

        {statusMessage && (
          <div
            role="status"
            className={`px-3.5 py-2.5 rounded-lg border text-xs font-mono ${
              statusMessage.tone === 'emerald'
                ? 'bg-emerald-50/80 dark:bg-emerald-950/30 border-emerald-200 dark:border-emerald-800 text-emerald-800 dark:text-emerald-300'
                : statusMessage.tone === 'amber'
                  ? 'bg-amber-50/80 dark:bg-amber-950/30 border-amber-200 dark:border-amber-800 text-amber-800 dark:text-amber-300'
                  : 'bg-rose-50/80 dark:bg-rose-950/30 border-rose-200 dark:border-rose-800 text-rose-800 dark:text-rose-300'
            }`}
          >
            {statusMessage.text}
          </div>
        )}

        <div className="grid grid-cols-1 xl:grid-cols-12 gap-5">
          {/* Left 7 Cols: Selectable Embodiment Table */}
          <div className="xl:col-span-7 overflow-x-auto border border-slate-200 dark:border-slate-800 rounded-lg">
            <table className="w-full text-left border-collapse text-xs tabular-nums">
              <thead>
                <tr className="border-b border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-[#070B14] text-slate-500 dark:text-slate-400 font-mono">
                  <th className="py-2.5 px-3 font-medium">Hardware Surface &amp; Binary</th>
                  <th className="py-2.5 px-3 font-medium text-right">Loop</th>
                  <th className="py-2.5 px-3 font-medium text-right">HAL Glue</th>
                  <th className="py-2.5 px-3 font-medium">Inspect</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
                {omega.embodiments.map((dev) => {
                  const isSelected = dev.deviceId === selectedDevice.deviceId;
                  return (
                    <tr
                      key={dev.deviceId}
                      className={`transition-colors ${
                        isSelected
                          ? 'bg-amber-50/60 dark:bg-amber-500/10'
                          : 'hover:bg-slate-50/80 dark:hover:bg-slate-900/40'
                      }`}
                    >
                      <td className="py-2.5 px-3 space-y-0.5">
                        <div className="font-semibold text-slate-900 dark:text-slate-100">
                          {dev.name}
                        </div>
                        <div className="font-mono text-[11px] text-slate-500 dark:text-slate-400">
                          {dev.substrate} · {dev.binaryArtifact}
                        </div>
                      </td>
                      <td className="py-2.5 px-3 text-right font-mono font-semibold text-cyan-700 dark:text-cyan-400 whitespace-nowrap">
                        {dev.controlLoopHz} Hz
                      </td>
                      <td className="py-2.5 px-3 text-right font-mono text-slate-700 dark:text-slate-300 whitespace-nowrap">
                        {dev.transducerLinesOfCode} LOC · 0 Core
                      </td>
                      <td className="py-2.5 px-3 whitespace-nowrap">
                        <button
                          type="button"
                          onClick={() => setSelectedDeviceId(dev.deviceId)}
                          className={`px-2.5 py-1 text-[11px] font-medium rounded transition-colors whitespace-nowrap ${
                            isSelected
                              ? 'bg-amber-400 text-slate-950 font-semibold'
                              : 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700'
                          }`}
                        >
                          {isSelected ? 'Selected' : 'Select'}
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Right 5 Cols: Selected Device HAL Contract & Latest Kernel Receipt */}
          <div className="xl:col-span-5 p-4 rounded-xl bg-slate-50 dark:bg-[#070B14] border border-slate-200 dark:border-slate-800 space-y-3 text-xs">
            <div className="space-y-0.5 pb-2.5 border-b border-slate-200 dark:border-slate-800">
              <div className="font-mono text-[11px] text-amber-600 dark:text-amber-400">
                ACTIVE TRANSDUCER INSPECTOR · {selectedDevice.controlLoopHz} HZ
              </div>
              <div className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                {selectedDevice.name}
              </div>
            </div>

            <div className="space-y-2 font-mono text-[11px]">
              <div>
                <span className="text-slate-500">1. sense() channels: </span>
                <span className="text-slate-800 dark:text-slate-200">
                  {selectedDevice.senseChannels.join(' · ')}
                </span>
              </div>
              <div>
                <span className="text-slate-500">2. actuate() channels: </span>
                <span className="text-cyan-700 dark:text-cyan-300">
                  {selectedDevice.actuateChannels.join(' · ')}
                </span>
              </div>
              <div>
                <span className="text-slate-500">3. link() transports: </span>
                <span className="text-slate-800 dark:text-slate-200">
                  {selectedDevice.linkTransports.join(' · ')}
                </span>
              </div>
              <div>
                <span className="text-slate-500">Kinetic Envelope: </span>
                <span className="text-emerald-700 dark:text-emerald-400">
                  Force &lt;={selectedDevice.safetyEnvelope.maxContactForceNewtons}N · Vel &lt;=
                  {selectedDevice.safetyEnvelope.maxVelocityMps}m/s · MinBat{' '}
                  {selectedDevice.safetyEnvelope.minBatteryReservePct}%
                </span>
              </div>
              <div>
                <span className="text-slate-500">Hardware Fail-Safe: </span>
                <span className="text-amber-700 dark:text-amber-300">
                  {selectedDevice.safetyEnvelope.failSafeAction}
                </span>
              </div>
            </div>

            {latestTick && (
              <div className="pt-2.5 border-t border-slate-200 dark:border-slate-800 space-y-1 font-mono text-[11px]">
                <div className="flex items-center justify-between gap-2">
                  <span className="font-semibold text-slate-900 dark:text-slate-100">
                    Latest Tick: {latestTick.tickId} ({latestTick.deviceId})
                  </span>
                  <span
                    className={
                      latestTick.safetyVerdict === 'PERMIT_NOMINAL'
                        ? 'text-emerald-600 dark:text-emerald-400 font-semibold'
                        : 'text-rose-600 dark:text-rose-400 font-semibold'
                    }
                  >
                    {latestTick.safetyVerdict}
                  </span>
                </div>
                <div className="text-slate-600 dark:text-slate-300 [overflow-wrap:anywhere]">
                  {latestTick.effectiveActuation}
                </div>
                {latestTick.safetyReasons.length > 0 && (
                  <div className="text-rose-600 dark:text-rose-400 flex items-start gap-1">
                    <ShieldAlert className="w-3.5 h-3.5 shrink-0 mt-0.5" aria-hidden="true" />
                    <span>{latestTick.safetyReasons.join(' ')}</span>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </section>

      {/* SECTION 03: <= 4,096 B CROSS-DEVICE CAPSULE TELEPORTATION */}
      <section
        aria-labelledby="omega-teleport-heading"
        className="bg-white dark:bg-[#0B101D] border border-slate-200 dark:border-slate-800 rounded-xl p-5 space-y-4"
      >
        <div className="space-y-1 pb-3 border-b border-slate-200 dark:border-slate-800">
          <div className="text-xs font-mono text-cyan-700 dark:text-cyan-400 tabular-nums">
            03. Seamless Cross-Device Capsule Teleportation (&lt;= 4,096 B)
          </div>
          <h2
            id="omega-teleport-heading"
            className="text-base font-semibold text-slate-900 dark:text-slate-50"
          >
            Move Active Mission, Real-Name Session &amp; Antibodies Across Devices Without Losing Context
          </h2>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 items-end">
          <div className="lg:col-span-3 space-y-1">
            <label
              htmlFor="teleport-source"
              className="block text-[11px] font-medium text-slate-600 dark:text-slate-400"
            >
              Source Surface
            </label>
            <select
              id="teleport-source"
              value={teleportSourceId}
              onChange={(e) => setTeleportSourceId(e.target.value)}
              className="w-full px-2.5 py-2 text-xs font-mono bg-slate-50 dark:bg-[#070B14] border border-slate-300 dark:border-slate-700 rounded-lg text-slate-900 dark:text-slate-100"
            >
              {omega.embodiments.map((d) => (
                <option key={d.deviceId} value={d.deviceId}>
                  {d.name}
                </option>
              ))}
            </select>
          </div>

          <div className="lg:col-span-3 space-y-1">
            <label
              htmlFor="teleport-target"
              className="block text-[11px] font-medium text-slate-600 dark:text-slate-400"
            >
              Target Embodiment
            </label>
            <select
              id="teleport-target"
              value={teleportTargetId}
              onChange={(e) => setTeleportTargetId(e.target.value)}
              className="w-full px-2.5 py-2 text-xs font-mono bg-slate-50 dark:bg-[#070B14] border border-slate-300 dark:border-slate-700 rounded-lg text-slate-900 dark:text-slate-100"
            >
              {omega.embodiments.map((d) => (
                <option key={d.deviceId} value={d.deviceId}>
                  {d.name}
                </option>
              ))}
            </select>
          </div>

          <div className="lg:col-span-4 space-y-1">
            <label
              htmlFor="teleport-mission"
              className="block text-[11px] font-medium text-slate-600 dark:text-slate-400"
            >
              Continuous Mission Intent Carried in &lt;= 4 KB Capsule
            </label>
            <input
              id="teleport-mission"
              type="text"
              value={teleportMission}
              onChange={(e) => setTeleportMission(e.target.value)}
              className="w-full px-3 py-2 text-xs font-mono bg-slate-50 dark:bg-[#070B14] border border-slate-300 dark:border-slate-700 rounded-lg text-slate-900 dark:text-slate-100"
            />
          </div>

          <div className="lg:col-span-2">
            <button
              type="button"
              disabled={busy}
              onClick={handleTeleportCapsule}
              className="w-full inline-flex items-center justify-center gap-1.5 px-3.5 py-2 text-xs font-semibold text-slate-950 bg-amber-400 hover:bg-amber-300 disabled:opacity-40 rounded-lg transition-colors whitespace-nowrap"
            >
              <ArrowRightLeft className="w-3.5 h-3.5" aria-hidden="true" />
              Teleport State
            </button>
          </div>
        </div>

        {latestCapsule && (
          <div className="p-3.5 rounded-lg bg-slate-50 dark:bg-[#070B14] border border-slate-200 dark:border-slate-800 font-mono text-[11px] space-y-1 tabular-nums">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="font-semibold text-emerald-700 dark:text-emerald-400">
                {latestCapsule.capsuleId} · {latestCapsule.sourceDeviceId} → {latestCapsule.targetDeviceId} ({latestCapsule.byteLength} B / 4,096 B)
              </span>
              <span className="text-slate-500">
                Transport: {latestCapsule.transportUsed} · SHA {latestCapsule.capsuleSha256.slice(0, 16)}…
              </span>
            </div>
            <div className="text-slate-600 dark:text-slate-300 [overflow-wrap:anywhere]">
              {latestCapsule.payloadJson}
            </div>
          </div>
        )}
      </section>

      {/* SECTION 04: UNIMAGINED FUTURE DEVICE ONBOARDING & MULTI-TARGET SDK GENERATOR */}
      <section
        aria-labelledby="omega-future-sdk-heading"
        className="bg-white dark:bg-[#0B101D] border border-slate-200 dark:border-slate-800 rounded-xl p-5 space-y-4"
      >
        <div className="space-y-1 pb-3 border-b border-slate-200 dark:border-slate-800">
          <div className="text-xs font-mono text-amber-600 dark:text-amber-400 tabular-nums">
            04. Zero-Rewrite Future Device Onboarding &amp; Transducer SDK Generator
          </div>
          <h2
            id="omega-future-sdk-heading"
            className="text-base font-semibold text-slate-900 dark:text-slate-50"
          >
            Plug In Hardware You Haven’t Even Invented Yet — Synthesize WIT, C99, Rust no_std &amp; ROS 2 Glue
          </h2>
        </div>

        <div className="grid grid-cols-1 xl:grid-cols-12 gap-5">
          {/* Left 5 Cols: Custom Hardware Onboarding Form */}
          <form
            onSubmit={handleRegisterFutureDevice}
            className="xl:col-span-5 p-4 rounded-xl bg-slate-50 dark:bg-[#070B14] border border-slate-200 dark:border-slate-800 space-y-3"
          >
            <div className="text-xs font-semibold text-slate-900 dark:text-slate-100">
              Declare New Hardware Transducer (0 Kernel Edits)
            </div>

            {formValidationError && (
              <div
                role="alert"
                className="p-2.5 rounded border border-rose-300 dark:border-rose-800 bg-rose-50 dark:bg-rose-950/40 text-xs text-rose-700 dark:text-rose-300"
              >
                {formValidationError}
              </div>
            )}

            <div className="space-y-1">
              <label
                htmlFor="future-device-name"
                className="block text-[11px] font-medium text-slate-600 dark:text-slate-400"
              >
                Future Device / Robot Name
              </label>
              <input
                id="future-device-name"
                type="text"
                value={customName}
                onChange={(e) => setCustomName(e.target.value)}
                className="w-full px-3 py-1.5 text-xs font-mono bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-lg text-slate-900 dark:text-slate-100"
              />
            </div>

            <div className="space-y-1">
              <label
                htmlFor="future-device-substrate"
                className="block text-[11px] font-medium text-slate-600 dark:text-slate-400"
              >
                Target Binary Substrate
              </label>
              <select
                id="future-device-substrate"
                value={customSubstrate}
                onChange={(e) => setCustomSubstrate(e.target.value as OmegaSubstrateClass)}
                className="w-full px-2.5 py-1.5 text-xs font-mono bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-lg text-slate-900 dark:text-slate-100"
              >
                {SUBSTRATE_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>

            <div className="grid grid-cols-3 gap-2">
              <div className="space-y-1">
                <label
                  htmlFor="future-hz"
                  className="block text-[11px] font-medium text-slate-600 dark:text-slate-400"
                >
                  Loop (Hz)
                </label>
                <input
                  id="future-hz"
                  type="number"
                  value={customHz}
                  onChange={(e) => setCustomHz(e.target.value)}
                  className="w-full px-2.5 py-1.5 text-xs font-mono bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-lg text-slate-900 dark:text-slate-100"
                />
              </div>

              <div className="space-y-1">
                <label
                  htmlFor="future-force"
                  className="block text-[11px] font-medium text-slate-600 dark:text-slate-400"
                >
                  Max Force (N)
                </label>
                <input
                  id="future-force"
                  type="number"
                  step="0.5"
                  value={customMaxForce}
                  onChange={(e) => setCustomMaxForce(e.target.value)}
                  className="w-full px-2.5 py-1.5 text-xs font-mono bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-lg text-slate-900 dark:text-slate-100"
                />
              </div>

              <div className="space-y-1">
                <label
                  htmlFor="future-vel"
                  className="block text-[11px] font-medium text-slate-600 dark:text-slate-400"
                >
                  Max Vel (m/s)
                </label>
                <input
                  id="future-vel"
                  type="number"
                  step="0.1"
                  value={customMaxVel}
                  onChange={(e) => setCustomMaxVel(e.target.value)}
                  className="w-full px-2.5 py-1.5 text-xs font-mono bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-lg text-slate-900 dark:text-slate-100"
                />
              </div>
            </div>

            <div className="space-y-1">
              <label
                htmlFor="future-sensors"
                className="block text-[11px] font-medium text-slate-600 dark:text-slate-400"
              >
                sense() Channels (comma-separated)
              </label>
              <input
                id="future-sensors"
                type="text"
                value={customSensors}
                onChange={(e) => setCustomSensors(e.target.value)}
                className="w-full px-3 py-1.5 text-xs font-mono bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-lg text-slate-900 dark:text-slate-100"
              />
            </div>

            <div className="space-y-1">
              <label
                htmlFor="future-actuators"
                className="block text-[11px] font-medium text-slate-600 dark:text-slate-400"
              >
                actuate() Channels (comma-separated)
              </label>
              <input
                id="future-actuators"
                type="text"
                value={customActuators}
                onChange={(e) => setCustomActuators(e.target.value)}
                className="w-full px-3 py-1.5 text-xs font-mono bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-lg text-slate-900 dark:text-slate-100"
              />
            </div>

            <div className="space-y-1">
              <label
                htmlFor="future-failsafe"
                className="block text-[11px] font-medium text-slate-600 dark:text-slate-400"
              >
                Hardware Fail-Safe Mode
              </label>
              <input
                id="future-failsafe"
                type="text"
                value={customFailsafe}
                onChange={(e) => setCustomFailsafe(e.target.value)}
                className="w-full px-3 py-1.5 text-xs font-mono bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-lg text-slate-900 dark:text-slate-100"
              />
            </div>

            <button
              type="submit"
              disabled={busy}
              className="w-full inline-flex items-center justify-center gap-1.5 py-2 px-3.5 text-xs font-semibold text-slate-950 bg-amber-400 hover:bg-amber-300 disabled:opacity-40 rounded-lg transition-colors whitespace-nowrap"
            >
              <Plus className="w-3.5 h-3.5" aria-hidden="true" />
              Bind Hardware to Omega Core (0 Core Edits)
            </button>
          </form>

          {/* Right 7 Cols: Live Synthesized Transducer Code */}
          <div className="xl:col-span-7 border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden flex flex-col">
            <div className="px-3.5 py-2.5 bg-slate-50 dark:bg-[#070B14] border-b border-slate-200 dark:border-slate-800 flex flex-wrap items-center justify-between gap-2">
              <div
                role="tablist"
                aria-label="Transducer SDK Target Language"
                className="flex flex-wrap items-center gap-1"
              >
                {(
                  [
                    { id: 'WIT', label: 'WASI WIT' },
                    { id: 'C99_ABI', label: 'C99 Firmware' },
                    { id: 'RUST_NO_STD', label: 'Rust no_std' },
                    { id: 'ROS2_PYTHON', label: 'ROS 2 Robotics' },
                  ] as const
                ).map((t) => (
                  <button
                    key={t.id}
                    type="button"
                    role="tab"
                    aria-selected={codegenTarget === t.id}
                    onClick={() => setCodegenTarget(t.id)}
                    className={`px-2.5 py-1 text-xs font-medium rounded transition-colors whitespace-nowrap shrink-0 ${
                      codegenTarget === t.id
                        ? 'bg-slate-900 text-white dark:bg-amber-400 dark:text-slate-950 font-semibold'
                        : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100'
                    }`}
                  >
                    {t.label}
                  </button>
                ))}
              </div>

              <button
                type="button"
                onClick={handleCopyGeneratedSdk}
                className="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-mono text-slate-700 dark:text-slate-200 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors whitespace-nowrap shrink-0"
              >
                {copiedCode ? (
                  <Check className="w-3.5 h-3.5 text-emerald-500" aria-hidden="true" />
                ) : (
                  <Copy className="w-3.5 h-3.5 text-amber-500" aria-hidden="true" />
                )}
                {copiedCode ? 'Copied' : generatedSdk.filename}
              </button>
            </div>

            <pre className="flex-1 p-4 bg-slate-950 text-slate-100 font-mono text-[11px] leading-relaxed overflow-x-auto">
              <code>{generatedSdk.code}</code>
            </pre>
          </div>
        </div>
      </section>
    </div>
  );
};
