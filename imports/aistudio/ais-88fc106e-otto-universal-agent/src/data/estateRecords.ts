import { EstateRepo, CredentialStatus, DeviceNode, PeerAgent, MemoryEntry } from '../types/otto';

export const ESTATE_REPOS: EstateRepo[] = [
  {
    name: 'argon',
    branch: 'outbox-state',
    agentsMdLaw: 'Rule 1: Zero unverified claims. Every commit requires signed gate verdict. No secrets in state.',
    status: 'synced',
    openPrs: [
      { id: 'PR-1084', title: 'feat(airlock): genesis-drop-ingest with cryptographic verification', gateVerdict: 'PASS', author: 'otto-lead' },
      { id: 'PR-1082', title: 'fix(maestro): sync android adb accessibility tree snapshotter', gateVerdict: 'PASS', author: 'deepseek-worker' }
    ]
  },
  {
    name: 'argon-sync',
    branch: 'main',
    agentsMdLaw: 'Rule 2: Outbox state sync must maintain atomic handovers without founder relay.',
    status: 'synced',
    openPrs: [
      { id: 'PR-419', title: 'chore(peer-bus): bin/genesis-crew.py roundtrip latency monitor', gateVerdict: 'PASS', author: 'otto-lead' }
    ]
  },
  {
    name: 'idp-archive',
    branch: 'main',
    agentsMdLaw: 'Rule 3: Historical specs & capability inventories remain read-only immutable references.',
    status: 'clean',
    openPrs: []
  }
];

export const CREDENTIALS_INVENTORY: CredentialStatus[] = [
  { name: 'BITWARDEN_SESSION_VAULT', path: '~/.bitwarden/vault.sock', present: true, source: 'host-job', restricted: true },
  { name: 'TELEGRAM_BOT_VIP_TOKEN', path: '/etc/estate/secrets/telegram.env', present: true, source: 'keychain', restricted: true },
  { name: 'ADB_SECURE_PAIRING_FINGERPRINT', path: '~/.android/adbkey', present: true, source: 'keychain', restricted: false },
  { name: 'XCRUN_DEVICECTL_MAC_CERT', path: '~/Library/Developer/Xcode/UserData/Profiles', present: true, source: 'keychain', restricted: false },
  { name: 'CLOUD_HOST_RUNNER_CREDENTIAL', path: '/opt/runner/auth.json', present: true, source: 'host-job', restricted: true },
  { name: 'GEMINI_AIRLOCK_API_KEY', path: 'ENV:GEMINI_API_KEY', present: true, source: 'bitwarden', restricted: true },
  { name: 'ROS2_DDS_ROBOTIC_MESH_TOKEN', path: '/etc/robotics/cyclonedds.xml', present: true, source: 'host-job', restricted: false }
];

export const ESTATE_DEVICES: DeviceNode[] = [
  {
    id: 'dev-mac-01',
    name: "Founder's MacBook Pro (M4 Max)",
    type: 'desktop',
    platform: 'macOS 15.1 Sequoia',
    status: 'online',
    battery: 92,
    lastPing: '2s ago',
    driver: 'Accessibility API + CGEvent + diff-verifier',
    latencyMs: 14
  },
  {
    id: 'dev-cloud-01',
    name: 'Cloud Headless Edge Cluster',
    type: 'browser',
    platform: 'Ubuntu 24.04 LTS (Playwright Chrome)',
    status: 'online',
    lastPing: '400ms ago',
    driver: 'Playwright CDP + DOM Text Readback',
    latencyMs: 8
  },
  {
    id: 'dev-android-01',
    name: 'Pixel 9 Pro (adb/Maestro)',
    type: 'android',
    platform: 'Android 15 (Vanilla Ice Cream)',
    status: 'online',
    battery: 88,
    lastPing: '1s ago',
    driver: 'adb + UI Automator 2.0 + Maestro flow engine',
    latencyMs: 22
  },
  {
    id: 'dev-iphone-01',
    name: 'iPhone 16 Pro (XCUITest)',
    type: 'iphone',
    platform: 'iOS 18.2 (xcrun devicectl)',
    status: 'online',
    battery: 85,
    lastPing: '1.2s ago',
    driver: 'XCUITest runner over Unix Domain Socket',
    latencyMs: 28
  },
  {
    id: 'dev-watch-01',
    name: 'Apple Watch Ultra 2 (Wrist Node)',
    type: 'watch',
    platform: 'watchOS 11.2 (Haptic Bus)',
    status: 'online',
    battery: 79,
    lastPing: '800ms ago',
    driver: 'WatchConnectivity + CoreHaptics Fast-Triage',
    latencyMs: 31
  },
  {
    id: 'dev-glasses-01',
    name: 'Orion Neural AR Glasses (HUD Node)',
    type: 'glasses',
    platform: 'Neural AR OS (Retinal Projection)',
    status: 'online',
    battery: 64,
    lastPing: '350ms ago',
    driver: 'Spatial Optical Raycasting + Retinal HUD Stream',
    latencyMs: 11
  },
  {
    id: 'dev-robotics-01',
    name: 'Universal Robotics UR5e + Unitree B2',
    type: 'robotics',
    platform: 'ROS2 Jazzy Jalisco / Cyclone DDS',
    status: 'online',
    battery: 95,
    lastPing: '120ms ago',
    driver: 'ros2_control JointTrajectoryController + MoveIt 2',
    latencyMs: 4
  }
];

export const PEER_BUS_AGENTS: PeerAgent[] = [
  {
    id: 'peer-otto-lead',
    name: 'Otto Core (Lead)',
    vendor: 'Otto (Lead)',
    role: 'lead',
    status: 'executing',
    currentTask: 'Supervising Evals E1-E12 & Estate Orchestration',
    busHeartbeat: '150ms ago'
  },
  {
    id: 'peer-deepseek-worker',
    name: 'DeepSeek-V3 Code Worker',
    vendor: 'DeepSeek',
    role: 'code-worker',
    status: 'active',
    currentTask: 'Parallel AST analysis & refactoring driver logic',
    busHeartbeat: '320ms ago'
  },
  {
    id: 'peer-gemini-vision',
    name: 'Gemini 2.5 Flash Vision Worker',
    vendor: 'Gemini',
    role: 'vision-worker',
    status: 'active',
    currentTask: 'Screen diff bounding box validation & OCR',
    busHeartbeat: '180ms ago'
  },
  {
    id: 'peer-kimi-context',
    name: 'Kimi Moonshot Context Worker',
    vendor: 'Kimi',
    role: 'long-context',
    status: 'idle',
    currentTask: 'Ingesting 1.2M token historical audit trail',
    busHeartbeat: '450ms ago'
  },
  {
    id: 'peer-blind-verifier',
    name: 'Independent Verifier (Blind QA)',
    vendor: 'Verifier (Blind)',
    role: 'independent-verifier',
    status: 'active',
    currentTask: 'Zero-knowledge verification of execution proofs',
    busHeartbeat: '110ms ago'
  }
];

export const INITIAL_MEMORIES: MemoryEntry[] = [
  {
    id: 'mem-user-01',
    layer: 'user',
    key: 'founder_communication_standard',
    content: 'VIP standard: outcome first, max 3 lines, zero file paths or tool names in telegram, never ask for secrets, quiet mode after 22:00 unless production is broken.',
    timestamp: '2026-11-06 14:22:00',
    verifiedBy: 'otto-lead',
    sourceSession: 'session-argon-vip-09'
  },
  {
    id: 'mem-project-01',
    layer: 'project',
    key: 'estate_airlock_rules',
    content: 'Deliveries must land as one bundle through bin/genesis-drop-ingest.py on a propose/* branch. Main branch is protected by cryptographic gate verdicts.',
    timestamp: '2026-11-06 16:04:12',
    verifiedBy: 'blind-verifier',
    sourceSession: 'session-argon-airlock-02'
  },
  {
    id: 'mem-session-01',
    layer: 'session',
    key: 'successor_continuation_checkpoint',
    content: 'Checkpoint #41: E1-E4 passed, E5 (computer use) screenshot diff delta=0.000%, state saved to shared outbox-state branch.',
    timestamp: '2026-11-06 17:05:40',
    verifiedBy: 'otto-lead',
    sourceSession: 'session-current'
  }
];
