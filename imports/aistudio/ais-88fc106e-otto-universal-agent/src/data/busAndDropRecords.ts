import { PeerBusPacket, IngestDrop, SeptemberCapability } from '../types/otto';

export const INITIAL_BUS_PACKETS: PeerBusPacket[] = [
  {
    id: 'pkt-bus-1092',
    timestamp: '18:01:42.124',
    channel: 'topic/ast-refactor',
    sender: 'otto-lead',
    receiver: 'deepseek-worker',
    payloadSummary: 'Dispatch AST mutation: optimize Maestro driver retry envelope to <=30s',
    payloadJson: { target: 'drivers/android_maestro.ts', maxRetryMs: 30000, boundsCheck: 'Invariant 3' },
    transitMs: 12,
    status: 'DELIVERED',
    proofHash: 'sha256:d81029cba1'
  },
  {
    id: 'pkt-bus-1093',
    timestamp: '18:01:42.348',
    channel: 'topic/ast-refactor',
    sender: 'deepseek-worker',
    receiver: 'otto-lead',
    payloadSummary: 'AST refactor complete: 0 syntax errors, verified in sandbox AST parser',
    payloadJson: { linesMutated: 42, compileStatus: 'OK', astHash: '0x94fa10' },
    transitMs: 14,
    status: 'VERIFIED',
    proofHash: 'sha256:99bc41029a'
  },
  {
    id: 'pkt-bus-1094',
    timestamp: '18:01:42.512',
    channel: 'topic/screen-diff',
    sender: 'otto-lead',
    receiver: 'gemini-vision',
    payloadSummary: 'Screen diff evaluation: 2560x1440 framebuffer vs DOM accessibility tree',
    payloadJson: { source: 'macOS_M4_Display0', diffTolerance: 0.001, expectedTarget: 'Button[Merge Airlock]' },
    transitMs: 9,
    status: 'DELIVERED',
    proofHash: 'sha256:4a019284cb'
  },
  {
    id: 'pkt-bus-1095',
    timestamp: '18:01:42.790',
    channel: 'topic/blind-qa',
    sender: 'gemini-vision',
    receiver: 'blind-verifier',
    payloadSummary: 'Vision audit passed: Target clicked with 0.000% delta misclick variance',
    payloadJson: { matchScore: 1.0, misclicks: 0, pixelDeltaPercent: 0.0 },
    transitMs: 11,
    status: 'VERIFIED',
    proofHash: 'sha256:ee19028471'
  },
  {
    id: 'pkt-bus-1096',
    timestamp: '18:01:43.012',
    channel: 'topic/gate-verdict',
    sender: 'blind-verifier',
    receiver: 'otto-lead',
    payloadSummary: 'Zero-Knowledge Gate Verdict: PASS (All 42 test assertions signed)',
    payloadJson: { verdict: 'PASS', zkProofVerified: true, airlockBranch: 'propose/otto-universal-v1' },
    transitMs: 8,
    status: 'VERIFIED',
    proofHash: 'sha256:77bc091823'
  },
  {
    id: 'pkt-bus-1097',
    timestamp: '18:01:43.340',
    channel: 'topic/heartbeat',
    sender: 'kimi-context',
    receiver: 'otto-lead',
    payloadSummary: 'Ingested 1.2M token founder transcript audit trail from 2026-11-07',
    payloadJson: { tokensProcessed: 1248000, contextWindow: '2M', memoryLayer: 'project' },
    transitMs: 15,
    status: 'DELIVERED',
    proofHash: 'sha256:aa09128374'
  }
];

export const INGEST_DROPS: IngestDrop[] = [
  {
    id: 'Drop #1055',
    title: "Founder's Android Phone Work (2026-11-07)",
    path: 'inbox/incoming/drop-1055-android-maestro.tar.gz',
    source: 'founder-phone-drop',
    status: 'verified-airlock',
    sha256: 'sha256:5a91028374619bca019283746102938471',
    contains: [
      '~/.maestro/flows/settings_triage.yaml',
      '~/.appium/drivers/uiautomator2_bindings.json',
      'Android 15 accessibility view-tree snapshotter'
    ]
  },
  {
    id: 'Drop #1062',
    title: "Founder's iPhone xcrun devicectl Profiles (2026-11-07)",
    path: 'inbox/incoming/drop-1062-iphone-devicectl.tar.gz',
    source: 'founder-phone-drop',
    status: 'verified-airlock',
    sha256: 'sha256:88bc019284719283746192837461928374',
    contains: [
      'xcrun devicectl identity certs for physical iPhone 16 Pro',
      'XCUITest runner over Unix Domain Socket daemon',
      'iOS 18.2 UI element hierarchy inspector'
    ]
  },
  {
    id: 'Drop #1065',
    title: 'September Otto Capabilities & Tool Registry',
    path: 'inbox/incoming/drop-1065-september-otto-inventory.tar.gz',
    source: 'hermes-agent-fork',
    status: 'verified-airlock',
    sha256: 'sha256:1928374619283746192837461928374619',
    contains: [
      'hermes_tool_registry.py (8 STT engines, 11 voices, vision/video pipeline)',
      'idp-archive/docs/specs/otto-capability-inventory.md',
      'bin/otto-concierge.py (1,228 lines baseline)'
    ]
  }
];

export const SEPTEMBER_CAPABILITIES: SeptemberCapability[] = [
  { name: 'Deepgram Nova-2', category: 'stt-engine', provider: 'Deepgram API', status: 'wired', latencyMs: 140 },
  { name: 'Whisper Large v3 Turbo', category: 'stt-engine', provider: 'Local / Cloud GPU', status: 'wired', latencyMs: 210 },
  { name: 'Google Cloud Chirp 2', category: 'stt-engine', provider: 'Google Speech API', status: 'wired', latencyMs: 165 },
  { name: 'ElevenLabs Scribe', category: 'stt-engine', provider: 'ElevenLabs', status: 'wired', latencyMs: 240 },
  { name: 'Groq Distil-Whisper', category: 'stt-engine', provider: 'Groq LPU', status: 'wired', latencyMs: 85 },
  { name: 'AssemblyAI Conformer', category: 'stt-engine', provider: 'AssemblyAI', status: 'wired', latencyMs: 220 },
  { name: 'RevAI Express', category: 'stt-engine', provider: 'Rev.ai', status: 'wired', latencyMs: 290 },
  { name: 'Azure Cognitive Speech', category: 'stt-engine', provider: 'Azure AI', status: 'wired', latencyMs: 180 },

  { name: 'Chief of Staff (Terse British Executive)', category: 'voice', provider: 'Otto Neural Voice #1', status: 'wired', latencyMs: 65 },
  { name: 'Serene Pastoral (Gentle Nun Companion)', category: 'voice', provider: 'Otto Neural Voice #4', status: 'wired', latencyMs: 70 },
  { name: 'Minimalist Tactical (Crisp Outcome)', category: 'voice', provider: 'Otto Neural Voice #7', status: 'wired', latencyMs: 50 },

  { name: 'Framebuffer Screenshot Diff Engine', category: 'vision', provider: 'CoreGraphics + OpenCV', status: 'wired', latencyMs: 18 },
  { name: 'Retinal Optical Raycasting HUD', category: 'vision', provider: 'Orion AR Neural SDK', status: 'wired', latencyMs: 11 },

  { name: 'ROS2 Cyclone DDS Teleoperation', category: 'tool', provider: 'ros2_control MoveIt 2', status: 'wired', latencyMs: 4 },
  { name: 'Bitwarden Session Vault Autofill', category: 'tool', provider: 'Unix Domain Socket', status: 'wired', latencyMs: 16 }
];
