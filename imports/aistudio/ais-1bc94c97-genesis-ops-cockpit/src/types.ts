export type LegionStatus = 'active' | 'blocked' | 'merge_ready' | 'gated' | 'sleeping';

export interface Legion {
  id: string;
  name: string;
  code: string;
  symbol: string;
  role: string;
  status: LegionStatus;
  statusLabel: string;
  activeAgents: number;
  lastSessionId: string;
  lastSyncTime: string;
  totalTokensProcessed: number;
  estateCostUsd: number;
  currentBriefId: string;
  colorTheme: {
    primary: string;
    border: string;
    bg: string;
    text: string;
    badgeBg: string;
  };
}

export interface BriefSectionShipped {
  id: string;
  text: string;
  commitHash?: string;
  prNumber?: number;
  impact: string;
}

export interface BriefSectionBlocked {
  id: string;
  text: string;
  blockerType: 'dof-gate' | 'dependency' | 'quota';
  detail: string;
}

export interface BriefSectionNeedsFounder {
  id: string;
  title: string;
  urgency: 'critical' | 'high' | 'normal';
  description: string;
  actionType: 'approve_credential' | 'merge_pr' | 'grant_budget' | 'dispatch_directive';
  status: 'pending' | 'approved' | 'rejected';
  resolvedAt?: string;
}

export interface KaraokeLine {
  id: string;
  startTime: number;
  endTime: number;
  text: string;
}

export interface SpokenBrief {
  id: string;
  legionId: string;
  legionName: string;
  title: string;
  recordedDurationSec: number;
  sha256Receipt: string;
  rawLogSessionId: string;
  rawLogLineCount: number;
  rawLogDurationMinutes: number;
  timestamp: string;
  pipeline: {
    sourceFormat: 'jsonl';
    condenser: 'dream-cycle-extractive-v2';
    ttsEngine: 'piper-neural-arm64' | 'speech-synthesis-fallback';
    piperVoice: string;
    estateCostUsd: number;
  };
  spokenScript: string;
  karaokeLines: KaraokeLine[];
  sections: {
    whatShipped: BriefSectionShipped[];
    whatIsBlocked: BriefSectionBlocked[];
    needsFounder: BriefSectionNeedsFounder[];
  };
}

export interface TelegramVoiceNote {
  id: string;
  legionId: string;
  legionName: string;
  voiceFileSha256: string;
  durationSec: number;
  timestamp: string;
  isHeard: boolean;
  deliveredStatus: 'delivered' | 'spooled' | 'listening';
  spoolerLatencyMs: number;
  summarySnippet: string;
  spokenScript: string;
  survivesDeadSession: boolean;
}

export interface EstateTelemetry {
  armVm: {
    coresTotal: number;
    coresAllocatedToPiper: number;
    cpuUtilizationPct: number;
    ramAllocatedGb: number;
    ramUsedGb: number;
    hourlyCostUsd: number;
  };
  dofGate: {
    status: 'LOCKED_AWAITING_CREDENTIAL' | 'UNBLOCKED_MERGING' | 'CLEAR';
    queueCount: number;
    nextInQueue: string;
  };
  piperLane: {
    activeVoice: string;
    latencyPerBriefMs: number;
    cachedAudioCount: number;
  };
  spooler: {
    queueLength: number;
    telegramDispatchLatencyMs: number;
    persistedVoiceCount: number;
  };
}
