import { Legion, SpokenBrief, TelegramVoiceNote, EstateTelemetry } from '../types';

export const INITIAL_TELEMETRY: EstateTelemetry = {
  armVm: {
    coresTotal: 4,
    coresAllocatedToPiper: 4,
    cpuUtilizationPct: 28,
    ramAllocatedGb: 8,
    ramUsedGb: 2.1,
    hourlyCostUsd: 0.0,
  },
  dofGate: {
    status: 'LOCKED_AWAITING_CREDENTIAL',
    queueCount: 3,
    nextInQueue: 'PR #412 (Piper ARM VM Neural TTS Lane)',
  },
  piperLane: {
    activeVoice: 'en_US-ryan-medium',
    latencyPerBriefMs: 380,
    cachedAudioCount: 24,
  },
  spooler: {
    queueLength: 2,
    telegramDispatchLatencyMs: 140,
    persistedVoiceCount: 36,
  },
};

export const INITIAL_LEGIONS: Legion[] = [
  {
    id: 'legion-alpha',
    name: 'Legion Alpha',
    code: 'ALPHA-KERNEL',
    symbol: 'α',
    role: 'Infrastructure & ARM64 Kernel',
    status: 'gated',
    statusLabel: 'Queued at DOF-Gate',
    activeAgents: 4,
    lastSessionId: 'sess_alp_8921a',
    lastSyncTime: '4m ago',
    totalTokensProcessed: 1420000,
    estateCostUsd: 0.0,
    currentBriefId: 'brief-alpha',
    colorTheme: {
      primary: '#38bdf8', // sky
      border: 'border-sky-500/30',
      bg: 'bg-sky-500/10',
      text: 'text-sky-400',
      badgeBg: 'bg-sky-950/60',
    },
  },
  {
    id: 'legion-beta',
    name: 'Legion Beta',
    code: 'BETA-EVAL',
    symbol: 'β',
    role: 'Frontier Models & Dream-Cycle Bench',
    status: 'active',
    statusLabel: 'Autonomous Run',
    activeAgents: 3,
    lastSessionId: 'sess_bet_7712c',
    lastSyncTime: '12m ago',
    totalTokensProcessed: 2890000,
    estateCostUsd: 0.0,
    currentBriefId: 'brief-beta',
    colorTheme: {
      primary: '#a855f7', // purple
      border: 'border-purple-500/30',
      bg: 'bg-purple-500/10',
      text: 'text-purple-400',
      badgeBg: 'bg-purple-950/60',
    },
  },
  {
    id: 'legion-gamma',
    name: 'Legion Gamma',
    code: 'GAMMA-SURFACE',
    symbol: 'γ',
    role: 'Genesis Surface & Voice Bar UI',
    status: 'merge_ready',
    statusLabel: 'PR Merge-Ready',
    activeAgents: 2,
    lastSessionId: 'sess_gam_4401e',
    lastSyncTime: '2m ago',
    totalTokensProcessed: 840000,
    estateCostUsd: 0.0,
    currentBriefId: 'brief-gamma',
    colorTheme: {
      primary: '#10b981', // emerald
      border: 'border-emerald-500/30',
      bg: 'bg-emerald-500/10',
      text: 'text-emerald-400',
      badgeBg: 'bg-emerald-950/60',
    },
  },
  {
    id: 'legion-delta',
    name: 'Legion Delta',
    code: 'DELTA-DATA',
    symbol: 'δ',
    role: 'Memory Spooler & JSONL Ring Buffer',
    status: 'active',
    statusLabel: 'Spooling Stream',
    activeAgents: 3,
    lastSessionId: 'sess_del_9981f',
    lastSyncTime: '18m ago',
    totalTokensProcessed: 3210000,
    estateCostUsd: 0.0,
    currentBriefId: 'brief-delta',
    colorTheme: {
      primary: '#f59e0b', // amber
      border: 'border-amber-500/30',
      bg: 'bg-amber-500/10',
      text: 'text-amber-400',
      badgeBg: 'bg-amber-950/60',
    },
  },
  {
    id: 'legion-epsilon',
    name: 'Legion Epsilon',
    code: 'EPSILON-SEC',
    symbol: 'ε',
    role: 'Security Enclave & DOF-Gate Triage',
    status: 'blocked',
    statusLabel: 'Credential Rotation Needed',
    activeAgents: 2,
    lastSessionId: 'sess_eps_1029d',
    lastSyncTime: '8m ago',
    totalTokensProcessed: 610000,
    estateCostUsd: 0.0,
    currentBriefId: 'brief-epsilon',
    colorTheme: {
      primary: '#f43f5e', // rose
      border: 'border-rose-500/30',
      bg: 'bg-rose-500/10',
      text: 'text-rose-400',
      badgeBg: 'bg-rose-950/60',
    },
  },
];

export const INITIAL_BRIEFS: Record<string, SpokenBrief> = {
  'brief-alpha': {
    id: 'brief-alpha',
    legionId: 'legion-alpha',
    legionName: 'Legion Alpha',
    title: 'Kernel & Piper ARM VM Lane Delivery',
    recordedDurationSec: 68,
    sha256Receipt: '8f21b7904e54cd882ae614995d319e7cf00b21a389146dfbca520111ea37cd19',
    rawLogSessionId: 'sess_alp_8921a',
    rawLogLineCount: 1420,
    rawLogDurationMinutes: 44,
    timestamp: '2026-11-09T14:24:00Z',
    pipeline: {
      sourceFormat: 'jsonl',
      condenser: 'dream-cycle-extractive-v2',
      ttsEngine: 'piper-neural-arm64',
      piperVoice: 'en_US-ryan-medium',
      estateCostUsd: 0.0,
    },
    spokenScript:
      'Genesis Brief for Legion Alpha. Here is the state of the world. What shipped: Merged PR 412 implementing the Piper neural voice synthesizer on the ARM VM. All neural models run across 4 local cores at zero dollar compute cost with sub-400 millisecond latency. What is blocked: Automated landing is queued behind the DOF-Gate credential unblock. Action required from founder: One-tap credential approval required to unlock gate lanes and promote PR 412 to main. Machine receipt verified and recorded.',
    karaokeLines: [
      { id: 'al-1', startTime: 0, endTime: 6, text: 'Genesis Brief for Legion Alpha. Here is the state of the world.' },
      { id: 'al-2', startTime: 6, endTime: 18, text: 'What shipped: Merged PR 412 implementing the Piper neural voice synthesizer on the ARM VM.' },
      { id: 'al-3', startTime: 18, endTime: 32, text: 'All neural models run across 4 local cores at zero dollar compute cost with sub-400 millisecond latency.' },
      { id: 'al-4', startTime: 32, endTime: 46, text: 'What is blocked: Automated landing is queued behind the DOF-Gate credential unblock.' },
      { id: 'al-5', startTime: 46, endTime: 60, text: 'Action required from founder: One-tap credential approval required to unlock gate lanes and promote PR 412 to main.' },
      { id: 'al-6', startTime: 60, endTime: 68, text: 'Machine receipt verified and recorded. Standing by for dispatch.' },
    ],
    sections: {
      whatShipped: [
        {
          id: 'shp-1',
          text: 'PR #412: Piper neural TTS lane on ARM VM (4 cores, $0 estate cost)',
          commitHash: 'e71ab49',
          prNumber: 412,
          impact: 'Core TTS Engine',
        },
        {
          id: 'shp-2',
          text: 'SHA-256 audio naming daemon with zero-leak disk buffer',
          commitHash: '98d2ef1',
          impact: 'Receipt Verifiability',
        },
      ],
      whatIsBlocked: [
        {
          id: 'blk-1',
          text: 'Promotion to main branch blocked',
          blockerType: 'dof-gate',
          detail: 'Queued behind DOF-Gate credential rotation. Lanes blocked until founder approves.',
        },
      ],
      needsFounder: [
        {
          id: 'fnd-1',
          title: 'Approve DOF-Gate Credential Rotation',
          urgency: 'critical',
          description: 'Reopen gate to unblock automated PR landing across Alpha and Gamma.',
          actionType: 'approve_credential',
          status: 'pending',
        },
        {
          id: 'fnd-2',
          title: 'Promote Piper ARM VM Lane to Primary Spooler',
          urgency: 'high',
          description: 'Switches default audio synthesis from browser fallback to local ARM VM.',
          actionType: 'merge_pr',
          status: 'pending',
        },
      ],
    },
  },
  'brief-beta': {
    id: 'brief-beta',
    legionId: 'legion-beta',
    legionName: 'Legion Beta',
    title: 'Frontier Models & Dream-Cycle Bench',
    recordedDurationSec: 72,
    sha256Receipt: 'd3e419b841a0e14cb751f8990263cbb21985ef41a238012da74e12e847c1a82e',
    rawLogSessionId: 'sess_bet_7712c',
    rawLogLineCount: 2890,
    rawLogDurationMinutes: 52,
    timestamp: '2026-11-09T14:18:00Z',
    pipeline: {
      sourceFormat: 'jsonl',
      condenser: 'dream-cycle-extractive-v2',
      ttsEngine: 'piper-neural-arm64',
      piperVoice: 'en_US-lessac-medium',
      estateCostUsd: 0.0,
    },
    spokenScript:
      'Genesis Brief for Legion Beta. What shipped: Verified the dream-cycle extractive core across 24 concurrent sessions. Achieved 99.6 percent log condensation with zero external model spend. What is blocked: External sandbox eval suite hit hourly rate ceilings. Action required from founder: Decide whether to toggle Gemini 2.5 Flash enrichment for high-cadence executive briefing polish at 1/100th of a cent per brief. Receipt confirmed.',
    karaokeLines: [
      { id: 'be-1', startTime: 0, endTime: 7, text: 'Genesis Brief for Legion Beta. Here is the state of the world.' },
      { id: 'be-2', startTime: 7, endTime: 22, text: 'What shipped: Verified the dream-cycle extractive core across 24 concurrent agent sessions.' },
      { id: 'be-3', startTime: 22, endTime: 36, text: 'Achieved 99.6 percent log condensation with zero external model spend.' },
      { id: 'be-4', startTime: 36, endTime: 48, text: 'What is blocked: External sandbox eval suite hit hourly rate ceilings.' },
      { id: 'be-5', startTime: 48, endTime: 64, text: 'Action required from founder: Decide whether to toggle Gemini 2.5 Flash enrichment for high-cadence spoken polish.' },
      { id: 'be-6', startTime: 64, endTime: 72, text: 'Machine receipt confirmed. Standing by for dispatch.' },
    ],
    sections: {
      whatShipped: [
        {
          id: 'shp-b1',
          text: 'Dream-Cycle extractive core benchmark: 99.6% reduction in transcript noise',
          commitHash: 'bc141aa',
          impact: 'Model Spend Protection',
        },
      ],
      whatIsBlocked: [
        {
          id: 'blk-b1',
          text: 'External eval benchmark sandbox throttled',
          blockerType: 'quota',
          detail: 'Sandbox hit 60 RPM burst limit; local heuristic evaluator continuing unaffected.',
        },
      ],
      needsFounder: [
        {
          id: 'fnd-b1',
          title: 'Review Gemini Enrichment Toggle Policy',
          urgency: 'normal',
          description: 'Confirm baseline remains $0 heuristic with opt-in Gemini 2.5 Flash enrichment.',
          actionType: 'dispatch_directive',
          status: 'pending',
        },
      ],
    },
  },
  'brief-gamma': {
    id: 'brief-gamma',
    legionId: 'legion-gamma',
    legionName: 'Legion Gamma',
    title: 'Genesis Surface Voice Bar & Cockpit UI',
    recordedDurationSec: 64,
    sha256Receipt: '4b91ce0a58ef30219ca71a682de90fbc410283aa90021ceba814d3a2e4b01149',
    rawLogSessionId: 'sess_gam_4401e',
    rawLogLineCount: 840,
    rawLogDurationMinutes: 28,
    timestamp: '2026-11-09T14:26:00Z',
    pipeline: {
      sourceFormat: 'jsonl',
      condenser: 'dream-cycle-extractive-v2',
      ttsEngine: 'piper-neural-arm64',
      piperVoice: 'en_GB-alan-low',
      estateCostUsd: 0.0,
    },
    spokenScript:
      'Genesis Brief for Legion Gamma. What shipped: Deployed the bottom Voice Bar on the ops-cockpit surface. Press any legion to hear its 60-second session. Browser SpeechSynthesis runs as zero-infra fallback before the Piper lane lands. What is blocked: PR 415 merge queued behind Alpha kernel gate. Action required from founder: Review and sign off on Genesis surface plan.',
    karaokeLines: [
      { id: 'ga-1', startTime: 0, endTime: 6, text: 'Genesis Brief for Legion Gamma. State of the surface.' },
      { id: 'ga-2', startTime: 6, endTime: 20, text: 'What shipped: Deployed the bottom Voice Bar on the ops-cockpit surface.' },
      { id: 'ga-3', startTime: 20, endTime: 34, text: 'Press any legion to hear its session. Browser SpeechSynthesis runs as zero-infra fallback.' },
      { id: 'ga-4', startTime: 34, endTime: 48, text: 'What is blocked: PR 415 merge is queued behind Alpha kernel gate.' },
      { id: 'ga-5', startTime: 48, endTime: 58, text: 'Action required from founder: Review and sign off on Genesis surface plan.' },
      { id: 'ga-6', startTime: 58, endTime: 64, text: 'Machine receipt verified. Standing by.' },
    ],
    sections: {
      whatShipped: [
        {
          id: 'shp-g1',
          text: 'Interactive Voice Bar with scrubbable waveform and karaoke sync',
          commitHash: '38a9bc0',
          prNumber: 415,
          impact: 'Founder Audio UX',
        },
      ],
      whatIsBlocked: [
        {
          id: 'blk-g1',
          text: 'Queued behind Alpha kernel PR #412',
          blockerType: 'dependency',
          detail: 'Requires Piper TTS lane unblock before merging surface audio bindings.',
        },
      ],
      needsFounder: [
        {
          id: 'fnd-g1',
          title: 'Sign Off on Genesis Surface Plan',
          urgency: 'high',
          description: 'Authorize merge-readiness for PR #415 into Genesis master.',
          actionType: 'merge_pr',
          status: 'pending',
        },
      ],
    },
  },
  'brief-delta': {
    id: 'brief-delta',
    legionId: 'legion-delta',
    legionName: 'Legion Delta',
    title: 'Data Memory Spooler & Telegram Pipeline',
    recordedDurationSec: 76,
    sha256Receipt: '9a7c3125e830bfd1ae4128f73100ba219aef4190c41031bba920412ef901b089',
    rawLogSessionId: 'sess_del_9981f',
    rawLogLineCount: 3210,
    rawLogDurationMinutes: 60,
    timestamp: '2026-11-09T14:10:00Z',
    pipeline: {
      sourceFormat: 'jsonl',
      condenser: 'dream-cycle-extractive-v2',
      ttsEngine: 'piper-neural-arm64',
      piperVoice: 'en_US-ryan-medium',
      estateCostUsd: 0.0,
    },
    spokenScript:
      'Genesis Brief for Legion Delta. What shipped: Established the persistent Telegram voice spooler via genesis-host-spooler. Voice notes survive dead sessions because audio files are persisted by SHA-256 hash. What is blocked: Zero blockers in data lane. Action required from founder: Approve 7-day voice note retention policy on local ARM VM storage.',
    karaokeLines: [
      { id: 'de-1', startTime: 0, endTime: 7, text: 'Genesis Brief for Legion Delta. State of memory spooling.' },
      { id: 'de-2', startTime: 7, endTime: 25, text: 'What shipped: Established the persistent Telegram voice spooler via genesis-host-spooler.' },
      { id: 'de-3', startTime: 25, endTime: 44, text: 'Voice notes survive dead sessions because audio files are persisted by SHA-256 hash.' },
      { id: 'de-4', startTime: 44, endTime: 54, text: 'What is blocked: Zero blockers in data lane. All streams operating smoothly.' },
      { id: 'de-5', startTime: 54, endTime: 68, text: 'Action required from founder: Approve 7-day voice note retention policy on ARM VM storage.' },
      { id: 'de-6', startTime: 68, endTime: 76, text: 'Machine receipt confirmed. Standing by.' },
    ],
    sections: {
      whatShipped: [
        {
          id: 'shp-d1',
          text: 'Persistent Telegram voice spooler with SHA-256 audio disk ledger',
          commitHash: '21ab89d',
          impact: 'Dead Session Survival',
        },
      ],
      whatIsBlocked: [
        {
          id: 'blk-d1',
          text: 'None',
          blockerType: 'dependency',
          detail: 'All spooler buffers healthy.',
        },
      ],
      needsFounder: [
        {
          id: 'fnd-d1',
          title: 'Approve 7-Day Voice Note Retention Policy',
          urgency: 'normal',
          description: 'Automatic rollover prevents ARM VM disk pressure.',
          actionType: 'dispatch_directive',
          status: 'pending',
        },
      ],
    },
  },
  'brief-epsilon': {
    id: 'brief-epsilon',
    legionId: 'legion-epsilon',
    legionName: 'Legion Epsilon',
    title: 'Security Enclave & DOF-Gate Triage',
    recordedDurationSec: 56,
    sha256Receipt: '1c890f5431ae87bc0192e4129b01ac21a084128ebca102941fa9021481a9ec31',
    rawLogSessionId: 'sess_eps_1029d',
    rawLogLineCount: 610,
    rawLogDurationMinutes: 19,
    timestamp: '2026-11-09T14:21:00Z',
    pipeline: {
      sourceFormat: 'jsonl',
      condenser: 'dream-cycle-extractive-v2',
      ttsEngine: 'piper-neural-arm64',
      piperVoice: 'en_US-amy-medium',
      estateCostUsd: 0.0,
    },
    spokenScript:
      'Genesis Brief for Legion Epsilon. What shipped: Verified cryptographic receipts across all five legions. Zero token leakage detected. What is blocked: Gate rotation locked in secure enclave. Action required from founder: Authorize credential rollover to open DOF-Gate.',
    karaokeLines: [
      { id: 'ep-1', startTime: 0, endTime: 6, text: 'Genesis Brief for Legion Epsilon. Security posture.' },
      { id: 'ep-2', startTime: 6, endTime: 22, text: 'What shipped: Verified cryptographic receipts across all five legions. Zero token leakage detected.' },
      { id: 'ep-3', startTime: 22, endTime: 34, text: 'What is blocked: Gate rotation is locked in secure enclave awaiting verification.' },
      { id: 'ep-4', startTime: 34, endTime: 48, text: 'Action required from founder: Authorize credential rollover to reopen the DOF-Gate.' },
      { id: 'ep-5', startTime: 48, endTime: 56, text: 'Cryptographic receipt confirmed. Standing by.' },
    ],
    sections: {
      whatShipped: [
        {
          id: 'shp-e1',
          text: 'Cryptographic audit ledger: 100% SHA-256 match on all session digests',
          commitHash: '8910cdf',
          impact: 'Receipt Provenance',
        },
      ],
      whatIsBlocked: [
        {
          id: 'blk-e1',
          text: 'DOF-Gate key rotation paused',
          blockerType: 'dof-gate',
          detail: 'Key rotation halted to prevent unauthenticated pipeline merging.',
        },
      ],
      needsFounder: [
        {
          id: 'fnd-e1',
          title: 'Authorize DOF-Gate Key Rollover',
          urgency: 'critical',
          description: 'Unlocks Legion Alpha and Gamma lanes immediately.',
          actionType: 'approve_credential',
          status: 'pending',
        },
      ],
    },
  },
};

export const INITIAL_TELEGRAM_NOTES: TelegramVoiceNote[] = [
  {
    id: 'tg-1',
    legionId: 'legion-alpha',
    legionName: 'Legion Alpha (Kernel)',
    voiceFileSha256: '8f21b7904e54cd882ae614995d319e7cf00b21a389146dfbca520111ea37cd19',
    durationSec: 68,
    timestamp: '14:24',
    isHeard: false,
    deliveredStatus: 'delivered',
    spoolerLatencyMs: 120,
    summarySnippet: 'PR #412 merged (Piper on ARM VM). Queued at DOF-Gate for credential rotation.',
    spokenScript: INITIAL_BRIEFS['brief-alpha'].spokenScript,
    survivesDeadSession: true,
  },
  {
    id: 'tg-2',
    legionId: 'legion-gamma',
    legionName: 'Legion Gamma (Surface)',
    voiceFileSha256: '4b91ce0a58ef30219ca71a682de90fbc410283aa90021ceba814d3a2e4b01149',
    durationSec: 64,
    timestamp: '14:26',
    isHeard: true,
    deliveredStatus: 'delivered',
    spoolerLatencyMs: 145,
    summarySnippet: 'Ops cockpit voice bar live. Browser SpeechSynthesis zero-infra fallback tested.',
    spokenScript: INITIAL_BRIEFS['brief-gamma'].spokenScript,
    survivesDeadSession: true,
  },
  {
    id: 'tg-3',
    legionId: 'legion-delta',
    legionName: 'Legion Delta (Spooler)',
    voiceFileSha256: '9a7c3125e830bfd1ae4128f73100ba219aef4190c41031bba920412ef901b089',
    durationSec: 76,
    timestamp: '14:10',
    isHeard: true,
    deliveredStatus: 'delivered',
    spoolerLatencyMs: 98,
    summarySnippet: 'genesis-host-spooler persistent voice buffer running. 7-day retention ready.',
    spokenScript: INITIAL_BRIEFS['brief-delta'].spokenScript,
    survivesDeadSession: true,
  },
];

export const SAMPLE_JSONL_SESSIONS: Record<string, string> = {
  'session-kernel-piper': `{"timestamp":"2026-11-09T14:02:11Z","level":"info","agent":"piper-worker-01","action":"Spawning ARM64 Piper neural runtime on core 0..3"}
{"timestamp":"2026-11-09T14:05:44Z","level":"milestone","agent":"piper-worker-01","action":"Merged PR #412: Piper fast neural TTS on ARM VM (4 cores, $0 cost)","commitHash":"e71ab49","prNumber":412}
{"timestamp":"2026-11-09T14:12:19Z","level":"info","agent":"piper-worker-01","action":"Benchmarked en_US-ryan-medium: 380ms latency per 70s brief audio"}
{"timestamp":"2026-11-09T14:18:02Z","level":"error","agent":"piper-worker-01","action":"DOF-Gate synchronization locked","details":"Queued behind credential unblock before automated PR landing","blocker":true,"needsFounder":true}
{"timestamp":"2026-11-09T14:22:15Z","level":"warn","agent":"piper-worker-01","action":"Approve DOF-Gate Credential Rotation","details":"Reopen gate to unblock automated PR landing across Alpha and Gamma","needsFounder":true}`,

  'session-model-benchmark': `{"timestamp":"2026-11-09T14:00:10Z","level":"info","agent":"eval-runner","action":"Evaluating extractive dream-cycle core across 45-min transcripts"}
{"timestamp":"2026-11-09T14:08:33Z","level":"milestone","agent":"eval-runner","action":"Achieved 99.6% log noise compression with zero external model spend","commitHash":"bc141aa"}
{"timestamp":"2026-11-09T14:14:01Z","level":"warn","agent":"eval-runner","action":"Sandbox rate limit reached on secondary testbed","details":"Secondary testbed 60 RPM limit hit, local heuristics unaffected","blocker":true}
{"timestamp":"2026-11-09T14:17:50Z","level":"info","agent":"eval-runner","action":"Review Gemini Enrichment Toggle Policy","details":"Founder can opt-in to Gemini 2.5 Flash at 1/100th cent per brief","needsFounder":true}`,

  'session-dof-gate-lock': `{"timestamp":"2026-11-09T14:10:05Z","level":"info","agent":"enclave-gatekeeper","action":"Routine cryptographic integrity check on Legion digests"}
{"timestamp":"2026-11-09T14:13:22Z","level":"milestone","agent":"enclave-gatekeeper","action":"100% SHA-256 match on all session digests","commitHash":"8910cdf"}
{"timestamp":"2026-11-09T14:19:40Z","level":"error","agent":"enclave-gatekeeper","action":"DOF-Gate credential rotation expired","details":"Credential locked in enclave to enforce founder gatekeeping","blocker":true,"needsFounder":true}
{"timestamp":"2026-11-09T14:21:00Z","level":"warn","agent":"enclave-gatekeeper","action":"Authorize DOF-Gate Key Rollover","details":"Founder manual sign-off required to resume automated merges","needsFounder":true}`,
};
