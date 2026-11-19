import type { AuraManifoldSnapshot } from '../engine/auraManifold';
import type { AutonomousReactivitySnapshot } from '../engine/autonomousReactivity';
import type { ProductionGuaranteesReport } from '../engine/debugPackBuilder';
import type { EstateGrandUnionSnapshot } from '../engine/estateGrandUnion';
import type {
  EstateWorkstreamRecord,
  LiveEstateWorkstreamTelemetryRow,
} from '../engine/estateWorkstreams';
import type {
  AgentsMdRatchetResult,
  FirstUseAuditSnapshot,
  InstallerShortcutAuditResult,
} from '../engine/firstUseGovernanceAudit';
import type {
  GenTttSpecSnapshot,
  I8088SimulationSnapshot,
} from '../engine/genesisSporeTtt';
import type { WorldResonanceSnapshot } from '../engine/hermesWorldConnector';
import type {
  CertificationScenarioId,
  MccConvergenceSnapshot,
} from '../engine/meridianCapabilityCalculus';
import type { MeridianSymphonySnapshot } from '../engine/meridianSymphony';
import type { MumConciergeOverviewSnapshot } from '../engine/mumsConcierge';
import type {
  AdversarialRedTeamSuiteReport,
  AppliancePillarId,
  ApplianceProfileId,
  ApplianceTurnkeySnapshot,
  ForeignLocationPresetId,
  ForeignPhoneBootstrapReceipt,
  RecoveryFactorId,
  TurnkeySetupRunReceipt,
  TurnkeyStageId,
  ZeroSecretRecoveryCapsule,
} from '../engine/applianceTurnkeySetup';
import type {
  BootStageId,
  PhoenixControlSnapshot,
} from '../engine/phoenixDailyBoot';
import type {
  AntiConfusionLedgerRow,
  InterchangeableActuatorId,
  IocSandboxPreset,
  SystemFirstIocAdmissionResult,
  SystemFirstIocStateSnapshot,
} from '../engine/systemFirstIocReconciler';
import type {
  CeoDecisionReceipt,
  CeoFocusPolicy,
  OttoNumenSnapshot,
  RawEstateEventKind,
  TelegramTopicKey,
  VipTelegramMessageCard,
} from '../engine/ottoNumenTelegram';
import {
  BattalionRoutingMapping,
  CertificationProbeResult,
  DiscoveredModelEntry,
  RecoveryWorkItem,
  SmallVsFrontierBenchmark,
  TaskAdmissionDecision,
} from '../engine/modelSupply';
import {
  MeridianFourDomainsSnapshot,
  PacketTraceRecord,
} from '../engine/meridianTelemetry';
import { ProviderRateCard } from '../engine/pricingCatalog';
import {
  CapSaveResult,
  ClientKeyRecord,
  DagsterAsset,
  DagsterRunEvent,
  DagsterSensor,
  RestartComparisonReport,
  RouteResult,
  RoutingStrategy,
  UpstreamLane,
  WalReceipt,
} from '../engine/types';

export type NavTabId =
  | 'appliance_setup'
  | 'phoenix_round_table'
  | 'union'
  | 'founder_reactivity'
  | 'investor_meridian'
  | 'founder_plane'
  | 'mum_concierge'
  | 'mumchimp_research'
  | 'academy'
  | 'telegram_vip'
  | 'hermes'
  | 'symphony'
  | 'genesis_ttt'
  | 'aura'
  | 'overview'
  | 'packets'
  | 'meridian'
  | 'supply'
  | 'dagster'
  | 'competitors'
  | 'falsifiers'
  | 'chaos';

export type {
  AdversarialRedTeamSuiteReport,
  AgentsMdRatchetResult,
  AppliancePillarId,
  ApplianceProfileId,
  ApplianceTurnkeySnapshot,
  AuraManifoldSnapshot,
  AutonomousReactivitySnapshot,
  CeoDecisionReceipt,
  CeoFocusPolicy,
  EstateGrandUnionSnapshot,
  FirstUseAuditSnapshot,
  ForeignLocationPresetId,
  ForeignPhoneBootstrapReceipt,
  GenTttSpecSnapshot,
  I8088SimulationSnapshot,
  InstallerShortcutAuditResult,
  LiveEstateWorkstreamTelemetryRow,
  CertificationScenarioId,
  MccConvergenceSnapshot,
  MeridianSymphonySnapshot,
  MumConciergeOverviewSnapshot,
  OttoNumenSnapshot,
  PhoenixControlSnapshot,
  BootStageId,
  AntiConfusionLedgerRow,
  InterchangeableActuatorId,
  IocSandboxPreset,
  RecoveryFactorId,
  SystemFirstIocAdmissionResult,
  SystemFirstIocStateSnapshot,
  TurnkeySetupRunReceipt,
  TurnkeyStageId,
  ProductionGuaranteesReport,
  RawEstateEventKind,
  TelegramTopicKey,
  VipTelegramMessageCard,
  WorldResonanceSnapshot,
  ZeroSecretRecoveryCapsule,
};

export interface GrandUnionApiResponse {
  union: EstateGrandUnionSnapshot;
  state: GatewayStateSnapshot;
  guarantees?: ProductionGuaranteesReport;
}

export interface GenesisSurvivalTttApiResponse {
  panspermia: I8088SimulationSnapshot;
  ttt: GenTttSpecSnapshot;
  estateRows: LiveEstateWorkstreamTelemetryRow[];
  guarantees: ProductionGuaranteesReport;
  healingCycles: number;
}

export interface ForensicSummary {
  baselineModelSlug: string;
  packetCount: number;
  succeededPackets: number;
  totalExecutedTokens: number;
  uncachedInputTokens: number;
  cachedInputTokens: number;
  outputTokens: number;
  reasoningTokens: number;
  tokensSavedByPennyD: number;
  actualSpendUsd: number;
  withoutPennydSpendUsd: number;
  netSavingsUsd: number;
  savingsPct: number;
  avgThroughputTokPerSec: number;
  blindCount: number;
  byProvider: Array<{
    provider: string;
    modelSlug: string;
    packets: number;
    executedTokens: number;
    tokensSaved: number;
    actualUsd: number;
    withoutPennydUsd: number;
    savedUsd: number;
  }>;
}

export interface PacketsApiResponse {
  packets: PacketTraceRecord[];
  summary: ForensicSummary;
  rateCards: ProviderRateCard[];
  state?: GatewayStateSnapshot;
}

export interface MeridianApiResponse {
  meridian: MeridianFourDomainsSnapshot;
  rateCards: ProviderRateCard[];
}

export interface GatewayStateSnapshot {
  strategy: RoutingStrategy;
  vaultHydrated: boolean;
  clientKeys: ClientKeyRecord[];
  tomlSnapshot: string;
  lanes: UpstreamLane[];
  walStats: {
    totalReceipts: number;
    uncommittedCount: number;
    checkpointedCount: number;
    latestSequence: number;
  };
  recentReceipts: WalReceipt[];
  forensicSummary?: ForensicSummary;
  dagster: {
    assets: DagsterAsset[];
    sensors: DagsterSensor[];
    events: DagsterRunEvent[];
  };
}

export interface RouteApiResponse {
  result: RouteResult;
  state: GatewayStateSnapshot;
}

export interface CapSaveApiResponse {
  saveResult: CapSaveResult;
  state: GatewayStateSnapshot;
}

export interface RestartApiResponse {
  report: RestartComparisonReport;
  state: GatewayStateSnapshot;
}

export interface SupplyApiResponse {
  discoveryCycle: number;
  models: DiscoveredModelEntry[];
  recoveryPackage: RecoveryWorkItem[];
  routingMatrix: BattalionRoutingMapping[];
  workstreams?: EstateWorkstreamRecord[];
  tick?: {
    cycle: number;
    discoveredCount: number;
    preExhaustionWarnings: string[];
  };
  certificationProbe?: CertificationProbeResult;
  updated?: DiscoveredModelEntry;
  decision?: TaskAdmissionDecision;
  benchmark?: SmallVsFrontierBenchmark;
}

