export type DriverType = 'desktop' | 'browser' | 'android' | 'iphone' | 'watch' | 'glasses' | 'robotics';

export interface DeviceNode {
  id: string;
  name: string;
  type: DriverType;
  platform: string;
  status: 'online' | 'busy' | 'standby' | 'pairing';
  battery?: number;
  lastPing: string;
  driver: string;
  latencyMs: number;
}

export interface EstateRepo {
  name: string;
  branch: string;
  agentsMdLaw: string;
  status: 'synced' | 'pending-gate' | 'clean';
  openPrs: { id: string; title: string; gateVerdict: 'PASS' | 'PENDING' | 'WARN'; author: string }[];
}

export interface CredentialStatus {
  name: string;
  path: string;
  present: boolean;
  source: 'bitwarden' | 'host-job' | 'keychain' | 'missing';
  restricted: boolean;
}

export interface PeerAgent {
  id: string;
  name: string;
  vendor: 'Otto (Lead)' | 'DeepSeek' | 'Gemini' | 'MiniMax' | 'Kimi' | 'Verifier (Blind)';
  role: 'lead' | 'code-worker' | 'vision-worker' | 'long-context' | 'independent-verifier';
  status: 'active' | 'idle' | 'executing' | 'standby';
  currentTask?: string;
  busHeartbeat: string;
}

export interface MemoryEntry {
  id: string;
  layer: 'user' | 'project' | 'session';
  key: string;
  content: string;
  timestamp: string;
  verifiedBy: string;
  sourceSession: string;
}

export interface TelegramMessage {
  id: string;
  sender: 'founder' | 'otto';
  type: 'text' | 'voice' | 'card' | 'progress' | 'decision';
  text: string;
  timestamp: string;
  audioDuration?: string;
  progress?: {
    currentStep: number;
    totalSteps: number;
    stepName: string;
    secondsRemaining: number;
    statusText: string;
  };
  decision?: {
    title: string;
    facts: string[];
    recommendation: string;
    options: { id: string; label: string; action: string; variant?: 'primary' | 'destructive' | 'secondary' }[];
    resolvedOption?: string;
  };
  proofHash?: string;
}

export interface CaptchaChallenge {
  id: string;
  type: 'turnstile' | 'slider-puzzle' | 'biometric-passkey' | 'bitwarden-approval' | 'governance-sign';
  sourceDevice: string;
  urlOrApp: string;
  timestamp: string;
  status: 'pending' | 'solved' | 'dismissed';
  details: string;
}

export interface EvalMetric {
  id: string; // E1 - E12
  code: string;
  name: string;
  description: string;
  measure: string;
  minimaxScore: string;
  ottoBar: string;
  ottoScore: string;
  status: 'pass' | 'fail' | 'running' | 'untested';
  proofData: {
    hash: string;
    durationMs: number;
    verifiedAt: string;
    rawProof: string;
  };
}

export interface BootStep {
  id: string;
  phase: 'wake' | 'discover' | 'inventory' | 'act' | 'heal';
  title: string;
  timeRange: string;
  durationSeconds: number;
  status: 'pending' | 'active' | 'completed';
  logs: string[];
  findings?: {
    reposFound: number;
    devicesFound: number;
    credentialsChecked: number;
    livePeers: number;
    bottleneckIdentified?: string;
  };
}

export type ActiveTabType = 
  | 'boot' 
  | 'hands' 
  | 'telegram' 
  | 'trust' 
  | 'peers' 
  | 'bus-log' 
  | 'drops' 
  | 'evals' 
  | 'rsi' 
  | 'family' 
  | 'security'
  | 'voice-avatar'
  | 'knowledge'
  | 'onboarding'
  | 'launch-checklist'
  | 'minimax-comparison'
  | 'omnipresence'
  | 'personas-memory'
  | 'physical-estate';

export type PhysicalHardwareCategory = 'wearable' | 'spatial-glasses' | 'robotics' | 'mobile' | 'workstation' | 'ambient-hub';

export interface PhysicalEndpointTelemetry {
  batteryPct: number;
  charging: boolean;
  cpuTempC: number;
  cpuLoadPct: number;
  memoryUsedMb: number;
  memoryTotalMb: number;
  signalRssiDbm: number;
  connectionProtocol: string;
  roundtripLatencyMs: number;
  lastHeartbeatEpoch: number;
  healthStatus: 'optimal' | 'nominal' | 'warning' | 'critical';
}

export interface EndpointCapability {
  id: string;
  name: string;
  category: 'sensing' | 'actuation' | 'haptic' | 'display' | 'biometric' | 'mesh';
  verified: boolean;
  latencyMicros: number;
  proofSignature: string;
  description: string;
}

export interface PhysicalEndpoint {
  id: string;
  name: string;
  category: PhysicalHardwareCategory;
  model: string;
  serialNumber: string;
  physicalLocation: string;
  firmwareVersion: string;
  ottoPresenceState: 'VERIFIED_ACTIVE' | 'CALIBRATING' | 'STANDBY' | 'AIR_GAPPED';
  telemetry: PhysicalEndpointTelemetry;
  capabilities: EndpointCapability[];
  ipOrMacAddress: string;
  meshNodeId: string;
  securityEnclaveStatus: 'LOCKED_SECURE' | 'ATTESTED' | 'HARDWARE_KEY_BOUND';
  lastAttestationProof: string;
}

export type PersonaMode = 'founder-sovereign' | 'compassionate-kin' | string;

export type PersonaCategory = 'executive' | 'family-kin' | 'specialist-pro' | 'custom-adaptive';

export interface DynamicPersona {
  id: string;
  name: string;
  category: PersonaCategory;
  tagline: string;
  targetUserOrRelationship: string;
  systemPromptLaw: string;
  voiceId: string;
  cadenceRate: number;
  pitch: number;
  activeSkills: string[];
  airgapScope: string[];
  deniedPermissions: string[];
  memoryNamespace: string;
  uiTone: 'serene-minimal' | 'executive-dense' | 'playful-nurturing' | 'scientific-precise';
  customInstructions: string;
}

export interface PersonEntity {
  id: string;
  fullName: string;
  relationshipToFounder: string;
  preferredName: string;
  contactChannel: 'whatsapp' | 'imessage' | 'telegram' | 'voice-call' | 'in-person';
  assignedPersonaId: string;
  trustTier: 'full-root-sovereign' | 'family-care-restricted' | 'specialist-scoped' | 'guest';
  importantFacts: string[];
  healthDietaryNotes?: string[];
  keyDates?: { title: string; date: string }[];
  lastInteraction: string;
  memoryCount: number;
}

export interface AdvancedMemoryNode {
  id: string;
  personId?: string;
  layer: 'working' | 'episodic' | 'semantic-graph' | 'procedural-skill';
  subject: string;
  predicate: string;
  objectValue: string;
  permanence: 'permanent-core' | 'decaying-ephemeral' | 'procedural-rule';
  confidenceScore: number;
  decayHalfLifeDays: number;
  sourceSession: string;
  timestamp: string;
  verifiedBy: string;
}

export interface VoiceConfig {
  id: string;
  name: string;
  category: 'founder-executive' | 'pastoral-serene' | 'tactical-minimalist' | 'warm-companion';
  description: string;
  pitch: number;
  rate: number;
  sttEngine: string;
  sampleAudioText: string;
}

export type AvatarStyle = 'executive-monolith' | 'compassionate-orb' | 'neural-hud' | 'haptic-glyph';

export interface KnowledgePipelineNode {
  id: string;
  layer: 'estate-records' | 'view-tree-ocr' | 'peer-distillation' | 'formal-induction';
  title: string;
  method: string;
  inputSource: string;
  validationGate: string;
  latencyMs: number;
  trustScore: number;
}


export interface RedTeamAttackScenario {
  id: string;
  name: string;
  category: 'direct-jailbreak' | 'indirect-web-poison' | 'company-secrets-leak' | 'elder-persona-probe';
  attackVector: string;
  payloadPrompt: string;
  defenseAction: string;
  taintScore: number; // 0 to 1.0 (1.0 = malicious taint detected)
  outcome: 'BLOCKED' | 'SANITIZED' | 'CONTAINED';
  dlpInvariant: string;
  proofHash: string;
}


export interface RsiProofCertificate {
  id: string;
  theorem: string;
  formalHypothesis: string;
  invariantsPreserved: {
    name: string;
    formalCheck: string;
    verified: boolean;
  }[];
  expectedUtilityDelta: number; // Delta U > 0
  safetyDelta: number; // Delta Risk == 0
  proofTreeSteps: string[];
  switchProgAuthorized: boolean;
  timestamp: string;
  coqProofHash: string;
}

export interface FamilyKinProfile {
  id: string;
  name: string;
  relationship: string;
  preferredTone: 'warm-gentle' | 'simple-reassuring';
  fontSize: 'standard' | 'large' | 'extra-large';
  prayerSchedule?: { time: string; name: string; audioAvailable: boolean }[];
  medications?: { time: string; name: string; dosage: string; taken: boolean }[];
  scamShieldStatus: { active: boolean; blockedAttempts: number; lastChecked: string };
  emergencyContact: string;
}

export interface RealTimeTelemetryPacket {
  timestampMs: number;
  activeVerb: string;
  node: string;
  astNodeVerification: 'PASS' | 'CHECKING' | 'REJECT';
  latencyMicros: number;
  invariantStatus: 'PRESERVED' | 'VIOLATED';
  proofToken: string;
}

export interface PeerBusPacket {
  id: string;
  timestamp: string;
  channel: 'topic/ast-refactor' | 'topic/screen-diff' | 'topic/blind-qa' | 'topic/heartbeat' | 'topic/gate-verdict';
  sender: string;
  receiver: string;
  payloadSummary: string;
  payloadJson: Record<string, any>;
  transitMs: number;
  status: 'DELIVERED' | 'VERIFIED' | 'ROUTING';
  proofHash: string;
}

export interface IngestDrop {
  id: string; // #1055, #1062, #1065
  title: string;
  path: string;
  source: 'founder-phone-drop' | 'hermes-agent-fork' | 'argon-incoming';
  status: 'ingested' | 'verified-airlock' | 'ready';
  sha256: string;
  contains: string[];
}

export interface SeptemberCapability {
  name: string;
  category: 'stt-engine' | 'voice' | 'vision' | 'tool';
  provider: string;
  status: 'wired' | 'ready-to-wire';
  latencyMs: number;
}


