import React, { useState } from 'react';
import { 
  Monitor, 
  Globe, 
  Smartphone, 
  Apple, 
  Watch, 
  Glasses, 
  Bot, 
  CheckCircle2, 
  Terminal, 
  Eye, 
  MousePointer, 
  Layers, 
  ShieldCheck, 
  Activity, 
  Compass, 
  Cpu,
  Video,
  Play,
  RotateCcw
} from 'lucide-react';
import { DriverType } from '../types/otto';
import { ScreenshotDiffViewer } from './ScreenshotDiffViewer';

export const HandsDrivers: React.FC = () => {
  const [selectedDriver, setSelectedDriver] = useState<DriverType>('desktop');
  const [activeVerb, setActiveVerb] = useState<string>('look');
  const [actionHistory, setActionHistory] = useState<Array<{ verb: string; target: string; result: string; proof: string; latency: number }>>([
    { verb: 'look', target: 'Display 0 [2560x1440]', result: 'Accessibility tree parsed (142 nodes)', proof: 'sha256:4a10f8', latency: 42 },
    { verb: 'find', target: 'Button[name="Merge Airlock"]', result: 'Located at (x: 1140, y: 720)', proof: 'sha256:bb2910', latency: 28 },
    { verb: 'tap', target: 'Button[name="Merge Airlock"]', result: 'CGEvent mouse click dispatched', proof: 'sha256:91ca02', latency: 34 },
    { verb: 'assert', target: 'State == "Merged"', result: 'Screenshot diff delta: 0.00% variance verified', proof: 'sha256:ee8812', latency: 51 }
  ]);
  const [isExecuting, setIsExecuting] = useState(false);
  const [robotJoints, setRobotJoints] = useState({
    base: 45,
    shoulder: -30,
    elbow: 90,
    wrist1: 15,
    wrist2: 0,
    gripper: 80
  });

  // Canonical verbs from Section 3
  const VERBS = ['look', 'find', 'tap', 'type', 'scroll', 'swipe', 'open', 'read', 'wait for', 'assert'];

  const executeVerb = (verb: string) => {
    setActiveVerb(verb);
    setIsExecuting(true);

    setTimeout(() => {
      let targetDesc = '';
      let resultDesc = '';

      switch (selectedDriver) {
        case 'desktop':
          targetDesc = verb === 'type' ? 'Terminal: "cargo build --release"' : 'System Preferences > Privacy';
          resultDesc = 'CGEvent + AXUIElement mutation confirmed with screenshot diff';
          break;
        case 'browser':
          targetDesc = verb === 'type' ? 'input#search-query' : 'DOM tree: https://cloud.internal';
          resultDesc = 'Playwright CDP text readback verified (200 OK)';
          break;
        case 'android':
          targetDesc = 'com.estate.authenticator:id/btn_approve';
          resultDesc = 'UI Automator 2.0 view hierarchy node validated via adb';
          break;
        case 'iphone':
          targetDesc = 'XCUIElementTypeButton["Allow Notifications"]';
          resultDesc = 'xcrun devicectl accessibility event confirmed';
          break;
        case 'watch':
          targetDesc = 'WatchConnectivity Haptic Bus (Wrist Glance)';
          resultDesc = 'Haptic tap sequence dispatched to Apple Watch Ultra 2';
          break;
        case 'glasses':
          targetDesc = 'Spatial Retinal Raycast @ (pitch: -4°, yaw: 12°)';
          resultDesc = 'AR HUD bounding box highlighted in field-of-view';
          break;
        case 'robotics':
          targetDesc = 'UR5e Manipulator JointTrajectory (MoveIt 2)';
          resultDesc = 'ROS2 Cyclone DDS /joint_states target reached with 0.01mm precision';
          break;
      }

      const randomProof = 'sha256:' + Math.random().toString(16).substring(2, 10);
      const latency = Math.floor(Math.random() * 40) + 18;

      setActionHistory(prev => [
        { verb, target: targetDesc, result: resultDesc, proof: randomProof, latency },
        ...prev.slice(0, 8)
      ]);
      setIsExecuting(false);
    }, 350);
  };

  return (
    <div className="space-y-6">
      {/* Driver Header & Universal Constant Banner */}
      <div className="rounded-2xl border border-slate-800 bg-gradient-to-b from-slate-900 to-slate-950 p-6 shadow-2xl">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-300 text-xs font-mono mb-2">
              <Bot className="w-3.5 h-3.5" />
              <span>SECTION 3: HANDS WITH UNIFIED CANONICAL VERBS</span>
            </div>
            <h2 className="text-2xl font-bold text-white font-display">
              Universal Hardware & Device Cockpit
            </h2>
            <p className="text-sm text-slate-400 max-w-2xl mt-1">
              Otto operates with <span className="text-cyan-400 font-semibold">one action layer across 7 drivers</span>: desktop, cloud browser, Android, iPhone, watches, AR glasses, and robotics. Every action sees the screen as image plus structure, acts, and checks the result before the next step.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-xs font-mono px-3 py-1.5 rounded-lg bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 flex items-center gap-1.5">
              <ShieldCheck className="w-3.5 h-3.5" />
              <span>STEP BOUND &lt;= 100s ENFORCED</span>
            </span>
          </div>
        </div>

        {/* 7 Driver Selector Buttons */}
        <div className="mt-6 grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-2">
          {[
            { id: 'desktop', name: 'Desktop', icon: Monitor, tag: 'macOS/Linux' },
            { id: 'browser', name: 'Browser', icon: Globe, tag: 'Cloud Playwright' },
            { id: 'android', name: 'Android', icon: Smartphone, tag: 'adb / Maestro' },
            { id: 'iphone', name: 'iPhone', icon: Apple, tag: 'XCUITest' },
            { id: 'watch', name: 'Smartwatch', icon: Watch, tag: 'Haptic Node' },
            { id: 'glasses', name: 'AR Glasses', icon: Glasses, tag: 'Retinal HUD' },
            { id: 'robotics', name: 'Robotics', icon: Cpu, tag: 'ROS2 / DDS' }
          ].map(driver => {
            const Icon = driver.icon;
            const isSelected = selectedDriver === driver.id;
            return (
              <button
                key={driver.id}
                onClick={() => setSelectedDriver(driver.id as DriverType)}
                className={`p-3 rounded-xl border flex flex-col items-center justify-center text-center transition-all ${
                  isSelected
                    ? 'border-indigo-400 bg-indigo-950/40 text-white shadow-lg shadow-indigo-500/10 ring-1 ring-indigo-400'
                    : 'border-slate-800 bg-slate-900/40 text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                }`}
              >
                <Icon className={`w-5 h-5 mb-1.5 ${isSelected ? 'text-indigo-400' : 'text-slate-400'}`} />
                <span className="text-xs font-semibold">{driver.name}</span>
                <span className="text-[10px] text-slate-500 font-mono mt-0.5">{driver.tag}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Canonical Verbs Toolbar */}
      <div className="p-4 rounded-xl border border-slate-800 bg-slate-950 flex flex-col md:flex-row items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          <Terminal className="w-4 h-4 text-cyan-400" />
          <span className="text-xs font-mono font-bold uppercase tracking-wider text-slate-300">
            Canonical Verbs:
          </span>
        </div>

        <div className="flex flex-wrap gap-1.5 justify-center">
          {VERBS.map(verb => (
            <button
              key={verb}
              onClick={() => executeVerb(verb)}
              disabled={isExecuting}
              className={`px-3 py-1.5 rounded-lg text-xs font-mono font-semibold transition-all ${
                activeVerb === verb
                  ? 'bg-cyan-500 text-slate-950 shadow-md shadow-cyan-500/20'
                  : 'bg-slate-900 text-slate-300 border border-slate-800 hover:bg-slate-800 hover:border-slate-700'
              }`}
            >
              .{verb}()
            </button>
          ))}
        </div>

        <div className="text-[11px] font-mono text-slate-400 flex items-center gap-1.5">
          <Video className="w-3.5 h-3.5 text-indigo-400" />
          <span>Trail Recorded</span>
        </div>
      </div>

      {/* Driver Viewport & Action Audit Log */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Device Viewport Simulation */}
        <div className="lg:col-span-7">
          <div className="rounded-xl border border-slate-800 bg-slate-950 p-4 shadow-xl">
            <div className="flex items-center justify-between mb-3 text-xs border-b border-slate-800 pb-2">
              <div className="flex items-center gap-2">
                <div className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse" />
                <span className="font-mono text-slate-200 uppercase font-semibold">
                  Driver Viewport: {selectedDriver.toUpperCase()}
                </span>
              </div>
              <span className="text-[10px] font-mono text-cyan-400 bg-cyan-950/40 px-2 py-0.5 rounded border border-cyan-800">
                RESOLUTION & DIFF CHECK: ACTIVE
              </span>
            </div>

            {/* Viewport Render depending on Driver */}
            <div className="relative min-h-[360px] bg-slate-900 rounded-xl border border-slate-800/80 overflow-hidden flex flex-col items-center justify-center p-4">
              
              {/* DESKTOP VIEW */}
              {selectedDriver === 'desktop' && (
                <div className="w-full max-w-md bg-slate-950 rounded-lg border border-slate-700 p-4 shadow-2xl space-y-3 font-mono text-xs">
                  <div className="flex items-center justify-between border-b border-slate-800 pb-2 text-[10px] text-slate-400">
                    <div className="flex gap-1.5">
                      <div className="w-2.5 h-2.5 rounded-full bg-rose-500" />
                      <div className="w-2.5 h-2.5 rounded-full bg-amber-500" />
                      <div className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
                    </div>
                    <span>founder@mac-m4: ~/estate/argon</span>
                  </div>
                  <div className="text-emerald-400">$ bin/genesis-drop-ingest.py --branch propose/otto-v1</div>
                  <div className="text-slate-400 text-[11px]">
                    [AIRLOCK] Verifying 42 test suite signatures...<br />
                    [DIFF] Comparing AST to main: +1,410 lines, -28 lines<br />
                    [GATE] Gatekeeper consensus: PASS (2/2 independent verifiers)
                  </div>
                  <div className="p-2 rounded bg-cyan-950/30 border border-cyan-800 text-[11px] text-cyan-300 flex items-center justify-between">
                    <span>Accessibility Tree: Focused AXWindow [Term2]</span>
                    <span className="text-emerald-400 font-bold">Diff: 0.00%</span>
                  </div>
                </div>
              )}

              {/* BROWSER VIEW */}
              {selectedDriver === 'browser' && (
                <div className="w-full max-w-lg bg-slate-950 rounded-lg border border-slate-700 p-3 shadow-2xl space-y-2 text-xs font-mono">
                  <div className="flex items-center gap-2 bg-slate-900 p-2 rounded text-[11px] text-slate-300">
                    <Globe className="w-3.5 h-3.5 text-cyan-400" />
                    <span>https://cloud.internal/cluster-dashboard/nodes</span>
                  </div>
                  <div className="p-3 bg-slate-900/60 rounded border border-slate-800 text-slate-300 text-[11px] space-y-2">
                    <div className="font-bold text-white">Cloud Node Cluster (Playwright Headless)</div>
                    <div className="grid grid-cols-2 gap-2 text-[10px]">
                      <div className="p-2 rounded bg-slate-950 border border-slate-800">
                        <div className="text-slate-400">Node Status</div>
                        <div className="text-emerald-400 font-bold">HEALTHY (100%)</div>
                      </div>
                      <div className="p-2 rounded bg-slate-950 border border-slate-800">
                        <div className="text-slate-400">DOM Tree Readback</div>
                        <div className="text-cyan-400 font-bold">186 text nodes</div>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* ANDROID VIEW */}
              {selectedDriver === 'android' && (
                <div className="w-64 bg-slate-950 rounded-2xl border-2 border-slate-700 p-3 shadow-2xl space-y-3 font-mono text-xs">
                  <div className="flex justify-between items-center text-[10px] text-slate-400 px-1">
                    <span>17:09</span>
                    <span className="text-emerald-400">5G · 88%</span>
                  </div>
                  <div className="p-3 rounded-xl bg-slate-900 border border-slate-800 space-y-2">
                    <div className="text-[10px] text-cyan-400 font-bold">ADB + UI AUTOMATOR 2.0</div>
                    <div className="text-[11px] text-white font-medium">Estate Mobile Companion</div>
                    <div className="text-[10px] text-slate-400">Package: com.estate.argon</div>
                    <button className="w-full py-1.5 rounded bg-indigo-600 text-white font-semibold text-[10px]">
                      Approve Sync Token
                    </button>
                  </div>
                  <div className="text-[9px] text-slate-500 text-center">
                    Maestro Driver attached via Unix Socket
                  </div>
                </div>
              )}

              {/* IPHONE VIEW */}
              {selectedDriver === 'iphone' && (
                <div className="w-64 bg-slate-950 rounded-3xl border-2 border-slate-700 p-3 shadow-2xl space-y-3 font-mono text-xs">
                  <div className="w-20 h-4 bg-slate-800 rounded-full mx-auto" />
                  <div className="p-3 rounded-2xl bg-slate-900 border border-slate-800 space-y-2">
                    <div className="text-[10px] text-indigo-300 font-bold">XCUITEST + DEVICECTL</div>
                    <div className="text-[11px] text-white">Apple Health & Identity Hub</div>
                    <div className="p-2 rounded bg-slate-950 border border-slate-800 text-[10px] text-emerald-400">
                      Accessibility Element ID: #auth-token-gate
                    </div>
                  </div>
                  <div className="text-[9px] text-slate-500 text-center">
                    Physical iPhone 16 Pro linked via Mac witness
                  </div>
                </div>
              )}

              {/* WATCH VIEW */}
              {selectedDriver === 'watch' && (
                <div className="w-56 h-64 bg-slate-950 rounded-[40px] border-4 border-amber-500/40 p-4 shadow-2xl flex flex-col justify-between font-mono text-xs text-center">
                  <div className="text-[10px] text-amber-400 font-bold flex items-center justify-center gap-1">
                    <Watch className="w-3.5 h-3.5" />
                    <span>APPLE WATCH ULTRA</span>
                  </div>
                  <div className="space-y-1">
                    <div className="text-xl font-bold text-white">OTTO HUD</div>
                    <div className="text-[10px] text-slate-300">Airlock PR-1084 Ready</div>
                    <button className="mt-2 px-3 py-1.5 rounded-full bg-emerald-500 text-slate-950 font-bold text-[10px]">
                      1-Tap Haptic Approve
                    </button>
                  </div>
                  <div className="text-[9px] text-slate-500">CoreHaptics Taptic Engine armed</div>
                </div>
              )}

              {/* GLASSES VIEW */}
              {selectedDriver === 'glasses' && (
                <div className="w-full max-w-md h-64 border border-cyan-500/50 bg-cyan-950/20 rounded-xl p-4 relative overflow-hidden font-mono text-xs scanline-effect">
                  <div className="absolute top-2 left-2 text-[10px] text-cyan-400 flex items-center gap-1">
                    <Glasses className="w-3.5 h-3.5" />
                    <span>ORION NEURAL HUD [RETINAL RAYCAST]</span>
                  </div>
                  <div className="absolute top-2 right-2 text-[10px] text-emerald-400">
                    GAZE: (0.42, 0.71) LOCKED
                  </div>
                  
                  {/* Visual Bounding Box in HUD */}
                  <div className="absolute top-16 left-12 w-48 h-28 border-2 border-dashed border-cyan-400 rounded p-2 bg-cyan-500/10">
                    <span className="text-[9px] bg-cyan-400 text-slate-950 px-1 font-bold">
                      OBJECT: WORKSTATION TERMINAL
                    </span>
                    <div className="text-[10px] text-cyan-200 mt-1">
                      Distance: 0.65m<br />
                      Action: Optical text scan complete
                    </div>
                  </div>
                </div>
              )}

              {/* ROBOTICS VIEW */}
              {selectedDriver === 'robotics' && (
                <div className="w-full max-w-md bg-slate-950 rounded-xl border border-purple-500/40 p-4 space-y-3 font-mono text-xs">
                  <div className="flex items-center justify-between text-purple-400 font-bold text-xs">
                    <span className="flex items-center gap-1.5">
                      <Cpu className="w-4 h-4" />
                      <span>ROS2 CYCLONE DDS TELEMETRY</span>
                    </span>
                    <span className="text-[10px] text-slate-400">UR5e + Unitree B2</span>
                  </div>

                  <div className="grid grid-cols-3 gap-2 text-[10px]">
                    {Object.entries(robotJoints).map(([joint, val]) => (
                      <div key={joint} className="p-2 rounded bg-slate-900 border border-slate-800">
                        <div className="text-slate-400 uppercase">{joint}</div>
                        <div className="text-purple-300 font-bold text-xs">{val}°</div>
                      </div>
                    ))}
                  </div>

                  <div className="flex gap-2 pt-2">
                    <button
                      onClick={() => setRobotJoints(prev => ({ ...prev, gripper: prev.gripper === 80 ? 20 : 80 }))}
                      className="w-full py-2 rounded-lg bg-purple-600 hover:bg-purple-500 text-white font-semibold text-[11px] transition-colors"
                    >
                      Toggle End-Effector Gripper ({robotJoints.gripper}%)
                    </button>
                  </div>
                </div>
              )}

            </div>
          </div>
        </div>

        {/* Action Audit Trail & Cryptographic Proof */}
        <div className="lg:col-span-5 space-y-4">
          <div className="rounded-xl border border-slate-800 bg-slate-950 p-4 shadow-xl">
            <div className="flex items-center justify-between mb-3 text-xs border-b border-slate-800 pb-2">
              <span className="font-display font-bold text-white uppercase tracking-wider flex items-center gap-1.5">
                <Activity className="w-4 h-4 text-emerald-400" />
                Action Audit Log & Proof Trail
              </span>
              <span className="text-[10px] font-mono text-slate-400">Bounded &lt; 100s</span>
            </div>

            <div className="space-y-2.5 max-h-[380px] overflow-y-auto pr-1">
              {actionHistory.map((action, i) => (
                <div key={i} className="p-2.5 rounded-lg bg-slate-900/60 border border-slate-800 text-xs font-mono space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="text-cyan-400 font-bold">.{action.verb}()</span>
                    <span className="text-[10px] text-slate-400">{action.latency}ms</span>
                  </div>
                  <div className="text-slate-300 text-[11px] truncate">{action.target}</div>
                  <div className="text-[10px] text-slate-400 flex items-center justify-between pt-1 border-t border-slate-800/60">
                    <span className="text-emerald-400 flex items-center gap-1">
                      <CheckCircle2 className="w-3 h-3" /> {action.result}
                    </span>
                    <span className="text-slate-500">{action.proof}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Visual Framebuffer Diff Slider & Bounding Box Delta */}
      <ScreenshotDiffViewer />
    </div>
  );
};
