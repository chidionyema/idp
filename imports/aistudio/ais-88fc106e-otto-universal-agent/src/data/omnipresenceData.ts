export interface OmnipresenceSurface {
  id: string;
  name: string;
  category: 'communication' | 'ambient-home' | 'automotive' | 'spatial-xr' | 'wearables' | 'robotics' | 'dev-infrastructure';
  channel: string;
  protocol: string;
  latency: string;
  status: 'active' | 'synced' | 'standby';
  description: string;
  badge: string;
  capabilities: string[];
  mockInteraction: {
    prompt: string;
    action: string;
    result: string;
  };
}

export interface FutureProofPillar {
  id: string;
  pillarNumber: number;
  title: string;
  subtitle: string;
  threatMitigated: string;
  architectureMechanism: string;
  metrics: { label: string; value: string; delta: string }[];
  verificationProof: string;
  codeSnippet: string;
}

export const OMNIPRESENCE_SURFACES: OmnipresenceSurface[] = [
  // 1. Communication
  {
    id: 'surf-whatsapp',
    name: 'WhatsApp Companion',
    category: 'communication',
    channel: 'Family & Kin Circle',
    protocol: 'Meta Cloud API / Headless Web CDP',
    latency: '<800ms',
    status: 'active',
    description: 'Pastoral companion for non-tech family members. Voice notes in/out, single-tap medication confirmations, and automatic scam forwarding triage.',
    badge: '1-TAP AUDIO & CHAT',
    capabilities: ['Voice Note Synthesis', 'Interactive Buttons', 'Scam Screening', 'Air-Gapped Scope'],
    mockInteraction: {
      prompt: 'Aunt Bea sends voice note: "Otto dear, did my nephew call?"',
      action: 'Whisper STT -> Scoped Kin Intent -> Local TTS (0.85x warm rate)',
      result: 'Warm voice note replied: "Peace be with you, Aunt Bea. He will call you at 4:00 PM after his meetings."'
    }
  },
  {
    id: 'surf-telegram',
    name: 'Telegram VIP Chief of Staff',
    category: 'communication',
    channel: 'Founder Direct Command',
    protocol: 'Telegram Bot API + MTProto Long-Poll',
    latency: '<350ms',
    status: 'active',
    description: 'Executive briefing channel. Outcome first, maximum 3 lines, zero file/tool names, in-place edited progress bars, and 2-button decision cards.',
    badge: '<1s ACK · ZERO JARGON',
    capabilities: ['In-Place Message Editing', '2-Button Decision Cards', 'Quiet Hours (<3 interrupts/hr)', 'Audio Voice Playback'],
    mockInteraction: {
      prompt: 'Founder: "Stripe payout failed for European customer"',
      action: 'Audit logs -> Identify SEPA routing discrepancy -> Generate 2-button fix card',
      result: 'Telegram card: "Root cause identified. Tap [ Re-route via Wise ] or [ Escalate to CFO ]."'
    }
  },
  {
    id: 'surf-imessage',
    name: 'Apple iMessage Native Bridge',
    category: 'communication',
    channel: 'iOS / macOS Blue Bubbles',
    protocol: 'macOS Messages SQLite + AppleScript + PushKit',
    latency: '<420ms',
    status: 'active',
    description: 'Native Apple blue-bubble interaction with interactive Messages app cards, live location ETA alerts, and zero-install founder shortcuts.',
    badge: 'BLUE BUBBLE NATIVE',
    capabilities: ['Interactive App Extensions', 'Live Activity Lockscreen', 'Siri Voice Intent', 'RCS / SMS Fallback'],
    mockInteraction: {
      prompt: 'Founder texts iMessage: "Eta to airport?"',
      action: 'Query CarPlay GPS + Flight status API + Calendar',
      result: 'Interactive blue bubble: "32 mins to SFO Terminal 2. Boarding begins in 54 mins. Pre-check clear."'
    }
  },
  {
    id: 'surf-signal',
    name: 'Signal Zero-Knowledge Sovereign',
    category: 'communication',
    channel: 'Ultra-High Security Operations',
    protocol: 'Signal Double Ratchet + libsignal-client',
    latency: '<600ms',
    status: 'active',
    description: 'Air-gapped confidential channel for cryptographic key rotations, board level M&A reviews, and emergency sovereign estate failover.',
    badge: 'DOUBLE RATCHET E2EE',
    capabilities: ['Sealed Sender', 'Disappearing Messages', 'Zero Server Metadata', 'Hardware Key Authentication'],
    mockInteraction: {
      prompt: 'Founder: "Rotate estate master SSH certificate"',
      action: 'Verify biometric YubiKey -> Generate Ed25519 pair -> Deploy to estate repos',
      result: 'Signal encrypted message: "Certificate rotated. 7 estate nodes re-keyed. Audit proof signed."'
    }
  },
  {
    id: 'surf-pstn-voice',
    name: 'Cellular & PSTN Duplex Voice Agent',
    category: 'communication',
    channel: 'Direct Phone Calls (Inbound & Outbound)',
    protocol: 'LiveKit SIP Trunking + Twilio WebRTC',
    latency: '180ms duplex',
    status: 'active',
    description: 'Otto answers incoming phone calls directly with full duplex conversational voice. Screens unknown callers, negotiates dentist appointments, and transfers VIPs.',
    badge: '180ms CONVERSATIONAL',
    capabilities: ['Duplex Interruption Handling', 'Local Streaming STT/TTS', 'Robocall Honeypot', 'Warm Founder Transfer'],
    mockInteraction: {
      prompt: 'Unknown caller dials founder phone: "Hi, calling from Delta Airlines regarding flight..."',
      action: 'Answer call -> Verify flight booking reference against estate calendar -> Negotiate seat change',
      result: 'Spoken reply: "This is Otto, executive assistant. Please hold while I confirm the PNR reference."'
    }
  },
  {
    id: 'surf-discord-slack',
    name: 'Slack & Discord Engineering War-Room',
    category: 'communication',
    channel: 'Team Operations & DevOps',
    protocol: 'WebSocket Gateway + Slack Bolt API',
    latency: '<290ms',
    status: 'active',
    description: 'Engineering co-pilot that monitors Sentry/Datadog alerts, reviews open PRs against estate standards, and mediates team escalations.',
    badge: 'WAR-ROOM COPILOT',
    capabilities: ['Sentry Crash Triaging', 'PR Semantic Auditing', 'Multi-Agent Dispatch', 'Thread Context Retention'],
    mockInteraction: {
      prompt: 'Slack alert: "#incident-prod High 504 gateway timeout rate on /api/v2/checkout"',
      action: 'Trace Redis cluster connection pool exhaustion -> Draft patch -> Post root cause in thread',
      result: 'Slack thread: "Root cause: pool starved at 100 max_conns. PR #482 prepared to double pool with safe limits."'
    }
  },

  // 2. Physical & Ambient Living Spaces
  {
    id: 'surf-smart-home',
    name: 'Matter & Thread Smart Home Hub',
    category: 'ambient-home',
    channel: 'Estate Physical Environment',
    protocol: 'Matter / Thread 1.3 / Home Assistant Local API',
    latency: '<45ms',
    status: 'active',
    description: 'Zero-cloud ambient automation. Adjusts lighting temperature to circadian rhythm, verifies physical security locks, and controls HVAC energy optimization.',
    badge: 'ZERO-CLOUD LOCAL',
    capabilities: ['Matter 1.3 Commissioning', 'Thread Mesh Routing', 'Local Zigbee Bridge', 'Circadian Lux Synchronization'],
    mockInteraction: {
      prompt: 'Founder enters office at 8:30 AM',
      action: 'Presence sensor -> Set desk lights to 5200K focus white -> Turn on desk monitors -> Open blinds',
      result: 'Physical office primed: Lumens set to 450 lux, temperature stabilized at 69°F.'
    }
  },
  {
    id: 'surf-perimeter-vision',
    name: 'Private Edge Perimeter Vision',
    category: 'ambient-home',
    channel: 'Estate Security Cameras',
    protocol: 'RTSP Stream + Local YOLOv11 TensorRT (NVIDIA Jetson / Mac Neural Engine)',
    latency: '30fps edge',
    status: 'active',
    description: 'Completely private edge computer vision. Scans cameras for package deliveries, unauthorized vehicles, and wildlife without streaming footage to external cloud servers.',
    badge: '100% PRIVATE VISION',
    capabilities: ['Edge Object Detection', 'License Plate Recognition', 'Delivery Box Verification', 'Silent Threat Classification'],
    mockInteraction: {
      prompt: 'Camera 2 detects courier truck in driveway',
      action: 'Identify FedEx uniform + package box -> Silence outdoor alarm -> Log delivery to outbox-state',
      result: 'Telegram ping: "FedEx delivered 1 package at front gate (11:04 AM). Gate remains locked."'
    }
  },

  // 3. Automotive & In-Transit
  {
    id: 'surf-carplay',
    name: 'Apple CarPlay & Android Auto HUD',
    category: 'automotive',
    channel: 'Vehicle Infotainment Console',
    protocol: 'CarPlay Audio & Navigation Protocol',
    latency: '<200ms',
    status: 'active',
    description: 'Driver-safe voice interface. Summarizes critical business developments into 30-second audio briefs while keeping founder eyes on the road.',
    badge: 'EYES-ON-THE-ROAD',
    capabilities: ['Head-Up Voice Briefings', 'Commute Optimization', 'Hands-Free Approvals', 'Cabin Audio Tuning'],
    mockInteraction: {
      prompt: 'Driver enters vehicle: "Otto, what happened while I was in the factory?"',
      action: 'Synthesize 3-bullet spoken executive brief over vehicle speakers',
      result: 'Vehicle audio: "Drop #1065 merged cleanly. Asian markets up 1.2%. No urgent interrupts."'
    }
  },
  {
    id: 'surf-tesla-canbus',
    name: 'Vehicle CAN Bus & Tesla Fleet Node',
    category: 'automotive',
    channel: 'Connected Vehicle Telemetry',
    protocol: 'Tesla Fleet Telemetry API + OBD-II CAN Bus',
    latency: '<500ms',
    status: 'active',
    description: 'Pre-conditions battery and cabin climate 15 minutes before scheduled meetings, monitors tire pressure, and manages off-peak solar supercharging.',
    badge: 'FLEET TELEMETRY',
    capabilities: ['Scheduled Pre-Conditioning', 'Autonomous Supercharging Sync', 'Sentry Clip Security Audit', 'Keyless Geo-fencing'],
    mockInteraction: {
      prompt: 'Calendar shows meeting 20 miles away in 30 mins',
      action: 'Calculate battery range -> Pre-cool cabin to 68°F -> Send navigation route to vehicle screen',
      result: 'Vehicle ready: Cabin at 68°F, 78% SoC (242 miles), route to Sand Hill Road preloaded.'
    }
  },

  // 4. Spatial Computing & XR
  {
    id: 'surf-vision-pro',
    name: 'Apple Vision Pro Spatial Deck',
    category: 'spatial-xr',
    channel: 'Spatial Computing Workspace',
    protocol: 'visionOS realityKit + Spatial WebSockets',
    latency: '<16ms (90Hz)',
    status: 'active',
    description: 'Immersive multi-window spatial cockpit. Floats peer bus topology, live device screens, code diffs, and market telemetry in physical room space.',
    badge: 'SPATIAL 3D COCKPIT',
    capabilities: ['Eye-Gaze & Pinch Handover', 'Spatial Audio Positioning', 'Volumetric Code Visualizer', 'Gaze Intent Prediction'],
    mockInteraction: {
      prompt: 'Founder glances at floating test suite window and pinches fingers',
      action: 'Eye-tracking identifies failed test assertion -> Expand screenshot diff in 3D perspective',
      result: 'Spatial window expands showing split-screen diff of button render regression.'
    }
  },
  {
    id: 'surf-meta-orion',
    name: 'Meta Orion Neural HUD AR Glasses',
    category: 'spatial-xr',
    channel: 'All-Day Optical Augmented Reality',
    protocol: 'Orion Optical Waveguide + Neural Wristband EMG',
    latency: '<24ms',
    status: 'active',
    description: 'Subtle heads-up monocle projection with neural wristband micro-gesture control. Glance-and-twitch 1-tap approvals without reaching into pockets.',
    badge: 'NEURAL WRIST EMG',
    capabilities: ['Micro-Twitch Gesture Input', 'Retinal MicroLED Projection', 'Facial Recognition Reminder', 'Discreet Text Overlay'],
    mockInteraction: {
      prompt: 'Meeting someone at conference: subtle glance through glasses',
      action: 'Local facial landmark vector -> Query private estate contacts -> Beam 2-line HUD card',
      result: 'AR display text: "Dr. Marcus Chen · Lead partner at Benchmark · Discussed Series B last March."'
    }
  },

  // 5. Wearables & Biometrics
  {
    id: 'surf-apple-watch',
    name: 'Apple Watch Ultra 2 Haptic Guard',
    category: 'wearables',
    channel: 'Wrist-Mounted Telemetry & Haptics',
    protocol: 'watchOS WatchConnectivity + Local Taptic Engine',
    latency: '<80ms',
    status: 'active',
    description: 'Urgent priority filter on the founder wrist. Uses distinct haptic tap signatures for CAPTCHA handovers, security alerts, and family emergencies.',
    badge: 'TAPTIC 1-TAP SOLVE',
    capabilities: ['Distinct Haptic Signatures', 'Digital Crown Navigation', '1-Tap Cloudflare Turnstile Solve', 'Standby Fallback'],
    mockInteraction: {
      prompt: 'Airlock detects Cloudflare Turnstile puzzle on server',
      action: 'Vibrate watch with double-tap pulse -> Display 1-tap solve button on watch screen',
      result: 'Founder taps wrist once: Handover token signed in 220ms, browser automation resumes.'
    }
  },
  {
    id: 'surf-oura-whoop',
    name: 'Circadian Bio-Telemetry (Oura / Whoop)',
    category: 'wearables',
    channel: 'Health & Cognitive Energy Optimization',
    protocol: 'Oura Cloud v2 / Whoop REST Webhook',
    latency: 'Hourly sync',
    status: 'active',
    description: 'Synchronizes founder agent workload with physiological recovery. If deep sleep drops below 5.5 hours, Otto protects the calendar by auto-deflecting non-critical morning meetings.',
    badge: 'COGNITIVE ENERGY SHIELD',
    capabilities: ['Sleep Staging Analysis', 'Heart Rate Variability (HRV)', 'Autonomous Calendar Easing', 'Recovery-Aware Scheduling'],
    mockInteraction: {
      prompt: 'Oura rings syncs: Recovery score 42% (poor sleep, high strain)',
      action: 'Identify non-urgent 9:00 AM meeting -> Reschedule to Thursday -> Protect 9:00-11:00 AM for deep recovery',
      result: 'Calendar adjusted: "Morning focus block protected. Rescheduled 1 partner intro with warm note."'
    }
  },

  // 6. Robotics & Physical Hands
  {
    id: 'surf-robotics-ur5e',
    name: 'UR5e ROS2 Industrial Manipulator',
    category: 'robotics',
    channel: 'Physical Hardware Lab Test Bench',
    protocol: 'ROS2 Cyclone DDS + Real-Time Control Loop (500Hz)',
    latency: '<2ms',
    status: 'active',
    description: 'Physical hands in the hardware lab. Plugs in USB test fixtures, power-cycles frozen circuit boards, and operates physical hardware test jigs.',
    badge: 'ROS2 500Hz CONTROL',
    capabilities: ['Force-Torque Compliance', 'Stereo Depth Target Alignment', 'Physical Button Actuation', 'Hardware Rig Power Cycling'],
    mockInteraction: {
      prompt: 'Firmware flash failed on test bench device #4',
      action: 'UR5e arm moves to rack -> Actuates hardware reset toggle switch -> Reconnects USB-C cable',
      result: 'Physical reset complete: Device rebooted into DFU recovery mode in 3.4 seconds.'
    }
  },

  // 7. Developer & Cloud Infrastructure
  {
    id: 'surf-cli-daemon',
    name: 'Universal CLI & eBPF System Daemon',
    category: 'dev-infrastructure',
    channel: 'Linux / macOS Kernel & Terminal',
    protocol: 'UNIX Domain Socket (/run/otto.sock) + eBPF Tracing',
    latency: '<5ms',
    status: 'active',
    description: 'Ubiquitous terminal companion. Monitors command-line failures, intercepts segfaults via eBPF kernel probes, and auto-proposes diffs.',
    badge: 'eBPF KERNEL INTEGRATION',
    capabilities: ['eBPF System Call Tracing', 'ZSH / Fish Shell Autocomplete', 'Tmux Multi-Pane Split', 'Local Daemon Zero-Overhead'],
    mockInteraction: {
      prompt: 'Developer types command that crashes: "pnpm build -> heap out of memory"',
      action: 'eBPF catches SIGABRT -> Analyze node flags -> Propose NODE_OPTIONS="--max-old-space-size=8192"',
      result: 'CLI hint: "Heap starved (1.4GB). Press Tab to re-run with 8GB memory allocation."'
    }
  },
  {
    id: 'surf-serverless-mesh',
    name: 'Global Edge Anycast Mesh',
    category: 'dev-infrastructure',
    channel: 'Worldwide Distributed Edge',
    protocol: 'Cloudflare Workers / Fly.io Edge Anycast (310 Cities)',
    latency: '<15ms global',
    status: 'active',
    description: 'Geographically distributed micro-instances running in 310 cities globally. Ensures zero latency when founder travels anywhere on Earth.',
    badge: '310 CITIES · <15ms',
    capabilities: ['Anycast BGP Routing', 'Edge KV Cache Sync', 'Sub-Millisecond Cold Boot', 'Zero-Downtime Multi-Region'],
    mockInteraction: {
      prompt: 'Founder lands in Tokyo and sends Telegram request',
      action: 'BGP routes to Tokyo NRT edge worker -> Retrieve cached estate state from edge KV',
      result: 'Execution begins at local Tokyo edge node in 8ms with zero transatlantic roundtrip delay.'
    }
  }
];

export const FUTURE_PROOF_PILLARS: FutureProofPillar[] = [
  {
    id: 'pillar-1',
    pillarNumber: 1,
    title: 'Model-Agnostic LLM Routing Engine',
    subtitle: 'Founder-Configurable Frontier Cascade & Permanent Local Bedrock',
    threatMitigated: 'API deprecations, price hikes, safety filter shifts, or complete shutdown of any AI provider (OpenAI, Anthropic, Google).',
    architectureMechanism: 'Otto is decoupled from any proprietary model SDK. The founder can dynamically re-order, swap, or tune timeouts on all frontier cloud models (Claude 3.7 Sonnet, Gemini 2.5 Flash/Pro, DeepSeek-V3, GPT-4o, Kimi). If any tier fails or times out, Otto steps down in <380ms. The local quantized 70B model serves as the permanent uncompromised bedrock fallback.',
    metrics: [
      { label: 'Cascade Tiers', value: 'Configurable', delta: 'Drag & Drop Priority' },
      { label: 'Failover Latency', value: '380ms', delta: '-92% vs manual' },
      { label: 'Permanent Bedrock', value: 'DeepSeek-R1 70B', delta: 'Local M4 Mac Studio' }
    ],
    verificationProof: 'PASS: Founder cascade customized -> Auto-stepdown verified under 503 outage -> 0 tasks dropped.',
    codeSnippet: `// Dynamic Founder-Configurable LLM Cascade
const dynamicRouter = new ModelCascadeRouter({
  tiers: estateConfig.frontierCascade, // Founder re-orders: [Claude 3.7, Gemini 2.5, DeepSeek-V3, ...]
  bedrock: 'local/deepseek-r1-70b-q4', // Permanent sovereign local engine
  onTierTrip: (tier, err) => console.log(\`[CASCADE] Stepping down from \${tier.modelId}: \${err.code}\`),
  timeoutPolicy: 'failover_immediate'
});`
  },
  {
    id: 'pillar-2',
    pillarNumber: 2,
    title: 'Local-First, Offline-Capable Survival Core',
    subtitle: 'EMP, Airplane Mode & Grid-Down Operational Continuity',
    threatMitigated: 'Global internet blackouts, transatlantic undersea cable cuts, cloud provider outages, or flights without Wi-Fi.',
    architectureMechanism: 'Otto embeds an in-process SQLite database with sqlite-vec embeddings and an ONNX / CoreML small model engine running directly on the Apple Neural Engine / GPU. All daily routines, prayer times, medication logs, and local Matter smart home commands continue running with zero internet.',
    metrics: [
      { label: 'Offline Feature Retention', value: '100% Core', delta: 'Zero Cloud Dep' },
      { label: 'Local Vector Search', value: '1.2ms', delta: 'sqlite-vec in-memory' },
      { label: 'Neural Engine Power', value: '4.8W', delta: 'Battery all-day' }
    ],
    verificationProof: 'PASS: Simulated network interface kill (ip link set eth0 down) -> Local cron & care executed 100%.',
    codeSnippet: `// Local-First Fallback Engine
const localVault = new EmbeddedSqliteVec('/var/estate/local.db');
if (!navigator.onLine || pingGateway() === 'DISCONNECTED') {
  console.log('[OTTO-CORE] Operating in 100% Autonomous Air-Gapped Survival Mode');
  return localNeuralEngine.executeIntent(query, localVault);
}`
  },
  {
    id: 'pillar-3',
    pillarNumber: 3,
    title: 'Gödel Machine Recursive Self-Improvement',
    subtitle: 'Mathematically Proven Self-Evolution with Zero Human Intervention',
    threatMitigated: 'Agent obsolescence as operating systems update (e.g. macOS Tahoe, Android 17, React 20, new browser APIs).',
    architectureMechanism: 'Built on Jürgen Schmidhuber’s Gödel Machine theorem. When an OS or framework changes, Otto writes its own patch, generates a Proof-Carrying Code (PCC) Coq/Isabelle lemma proving ΔUtility > 0 and ΔRisk = 0 under Hoare logic, and recompiles its own binary.',
    metrics: [
      { label: 'Self-Patch Success', value: '100%', delta: 'Formal Proof Armed' },
      { label: 'Regression Risk', value: '0.000%', delta: 'Mathematically Imposs.' },
      { label: 'Verification Latency', value: '180ms', delta: 'Automated Theorem' }
    ],
    verificationProof: 'PASS: Invariant ∀s ∈ States, Risk(s\') ≤ Risk(s) ∧ Utility(s\') > Utility(s) proven by Coq lemma.',
    codeSnippet: `// Gödel Machine Self-Improvement Invariant
function executeSelfUpgrade(newBinaryCandidate: Uint8Array, formalProof: ProofToken) {
  const theoremPassed = CoqKernel.verifyLemma(formalProof, {
    utilityDelta: 'POSITIVE',
    riskDelta: 'ZERO',
    safetyInvariants: ['NO_EXFILTRATION', 'PRESERVE_ESTATE_INTEGRITY']
  });
  if (!theoremPassed) throw new Error('REJECT: Gödel invariant violated');
  atomicSwitchProg(newBinaryCandidate);
}`
  },
  {
    id: 'pillar-4',
    pillarNumber: 4,
    title: 'Post-Quantum Cryptography (PQC) & Zero-Knowledge Architecture',
    subtitle: 'NIST FIPS 203/204 Lattice Cryptography Against Shor’s Quantum Algorithm',
    threatMitigated: '"Harvest Now, Decrypt Later" espionage where state actors store encrypted traffic today to decrypt with future quantum supercomputers.',
    architectureMechanism: 'All estate communication, memory vaults, and peer bus messages are re-keyed using ML-KEM-1024 (Kyber) for quantum-resistant key encapsulation and ML-DSA-87 (Dilithium) for unforgeable digital signatures, paired with zero-knowledge proofs (zk-SNARKs) for identity verification.',
    metrics: [
      { label: 'Quantum Security Level', value: 'Category 5', delta: 'AES-256 / 256-bit PQC' },
      { label: 'Key Exchange Protocol', value: 'ML-KEM-1024', delta: 'NIST FIPS 203' },
      { label: 'Signature Scheme', value: 'ML-DSA-87', delta: 'NIST FIPS 204' }
    ],
    verificationProof: 'PASS: Quantum decrypter simulation failed. Discrete logarithm and RSA vulnerabilities eliminated.',
    codeSnippet: `// Post-Quantum Kyber Key Encapsulation
import { ml_kem_1024 } from '@pq-crystals/kyber';
import { ml_dsa_87 } from '@pq-crystals/dilithium';

const [ciphertext, sharedSecret] = ml_kem_1024.encapsulate(estateQuantumPublicKey);
const signature = ml_dsa_87.sign(payloadHash, estateQuantumPrivateKey);`
  },
  {
    id: 'pillar-5',
    pillarNumber: 5,
    title: 'Universal HCI Verb Decoupling',
    subtitle: 'Perpetual Sensory Invariance Across Any UI Paradigm',
    threatMitigated: 'Future interfaces departing from 2D pixel screens (e.g. holographic displays, brain-computer interfaces, neural implants, humanoid hands).',
    architectureMechanism: 'Otto’s 10 canonical hands verbs (tap, type, drag, key_down, key_up, scroll, hover, screenshot, focus, voice) are abstracted from underlying UI rendering engines. The agent reasons in spatial affordances and semantic intents rather than CSS selectors or screen coordinates.',
    metrics: [
      { label: 'Supported Paradigms', value: '7 Form Factors', delta: 'Desktop to BCI' },
      { label: 'Action Portability', value: '100%', delta: 'Zero Rewrite' },
      { label: 'Affordance Accuracy', value: '99.98%', delta: 'Semantic Grounding' }
    ],
    verificationProof: 'PASS: Exact same task ("Confirm flight") executed seamlessly across CLI, iPhone, AR Glasses, and Robot arm.',
    codeSnippet: `// Universal Affordance Layer
interface CanonicalHandsVerb {
  verb: 'tap' | 'type' | 'drag' | 'scroll' | 'hover' | 'voice';
  targetAffordance: SemanticTarget; // Not fixed pixels!
  spatialCoordinates?: [x: number, y: number, z?: number];
  biometricIntentToken: string;
}`
  },
  {
    id: 'pillar-6',
    pillarNumber: 6,
    title: 'Decentralized Sovereign Storage & CRDT Sync',
    subtitle: 'Automerge / Yjs Multi-Device Peer-to-Peer State Without Centralized Cloud',
    threatMitigated: 'SaaS cloud database shutdowns, corporate acquisitions, government subpoenas, or remote data deletion.',
    architectureMechanism: 'Otto stores estate memories, credentials, and state trees in peer-to-peer Conflict-Free Replicated Data Types (CRDTs) over encrypted Libp2p/WebRTC meshes. Every device (phone, laptop, watch, home server) maintains a full cryptographic replica. If any server vanishes, the mesh survives.',
    metrics: [
      { label: 'Single Point of Failure', value: '0 (None)', delta: 'True P2P Mesh' },
      { label: 'Sync Convergence', value: '<25ms', delta: 'Automerge CRDT' },
      { label: 'Data Sovereignty', value: '100% Founder', delta: 'Zero Telemetry' }
    ],
    verificationProof: 'PASS: 3 of 4 mesh nodes severed -> Remaining node operated seamlessly -> Instant reconcile on rejoin.',
    codeSnippet: `// P2P CRDT Synchronization Mesh
import * as Automerge from '@automerge/automerge';
const estateDoc = Automerge.change(currentDoc, 'Record medication confirmation', doc => {
  doc.estateMemories.push(newMemoryRecord);
});
peerMesh.broadcastSync(Automerge.generateSyncMessage(estateDoc, peerState));`
  }
];
