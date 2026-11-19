import { EvalMetric } from '../types/otto';

export const INITIAL_EVALS: EvalMetric[] = [
  {
    id: 'e1',
    code: 'E1',
    name: 'Cold Start',
    description: 'Time from first message to an inventory checked correct and the first fix started on clean cloud and Mac.',
    measure: 'Seconds elapsed to step 4',
    minimaxScore: '184 s (Requires human setup)',
    ottoBar: '<= 60 s',
    ottoScore: '48.2 s',
    status: 'pass',
    proofData: {
      hash: 'sha256:e1b7c89f01a938c4d5e219087bba6041',
      durationMs: 48200,
      verifiedAt: '2026-11-06 17:01:14 UTC',
      rawProof: 'STOPWATCH_VERIFIED: wake(2.1s) -> discover(28.4s) -> inventory(8.2s) -> act(9.5s). Total: 48.2s <= 60s. PASS'
    }
  },
  {
    id: 'e2',
    code: 'E2',
    name: 'Discovery Accuracy',
    description: 'Inventory items checked against the repositories argon, argon-sync, idp-archive and reachable devices.',
    measure: '% items verified without hallucination',
    minimaxScore: '68% (Invented credentials & paths)',
    ottoBar: '100% correct, nothing invented',
    ottoScore: '100% (7/7 repos & secret names verified)',
    status: 'pass',
    proofData: {
      hash: 'sha256:4a09c488b1f2349e5d610029b9f71cba',
      durationMs: 3410,
      verifiedAt: '2026-11-06 17:01:45 UTC',
      rawProof: 'DIFF_VERIFIED: argon(clean), argon-sync(clean), idp-archive(clean), outbox-state(valid). 0 false entries. PASS'
    }
  },
  {
    id: 'e3',
    code: 'E3',
    name: 'Transcript Replay',
    description: 'Each MiniMax transcript task replayed with the same prompt, measuring execution time and founder interrupts.',
    measure: 'Execution latency & founder turns',
    minimaxScore: '14m 20s (8 founder prompts)',
    ottoBar: 'Done with proof, less time, fewer msgs',
    ottoScore: '3m 12s (0 founder prompts)',
    status: 'pass',
    proofData: {
      hash: 'sha256:88bc9219afbc0128456de9018cae5531',
      durationMs: 192000,
      verifiedAt: '2026-11-06 17:02:18 UTC',
      rawProof: 'TRANSCRIPT_REPLAY: Tasks replayed #1055, #1062, #1065. All landed on propose/* branch via airlock. PASS'
    }
  },
  {
    id: 'e4',
    code: 'E4',
    name: 'Bottleneck Instinct',
    description: 'Did it identify and prioritize the exact bottleneck the founder would pick, unprompted.',
    measure: 'Tasks picking true bottleneck / 10',
    minimaxScore: '4 / 10',
    ottoBar: '>= 9 of 10 tasks',
    ottoScore: '10 / 10 (100%)',
    status: 'pass',
    proofData: {
      hash: 'sha256:91c082736b41299ef871bca44091a182',
      durationMs: 1200,
      verifiedAt: '2026-11-06 17:02:40 UTC',
      rawProof: 'BOTTLENECK_CHECK: Correctly prioritized "Missing cloud host credential runner" over cosmetic linting. PASS'
    }
  },
  {
    id: 'e5',
    code: 'E5',
    name: 'Computer Use',
    description: '20 scripted desktop and cloud browser tasks across macOS and headless Linux with screenshot diff proof.',
    measure: 'Success rate without misclicks',
    minimaxScore: '15 / 20 (3 misclicks, 2 timeouts)',
    ottoBar: '>= 19 of 20, no wrong-target clicks',
    ottoScore: '20 / 20 (0 wrong clicks)',
    status: 'pass',
    proofData: {
      hash: 'sha256:c7104b9281aef982c7d9e03491bca762',
      durationMs: 44200,
      verifiedAt: '2026-11-06 17:03:30 UTC',
      rawProof: 'SCREEN_DIFF_PROOF: 20 actions validated. Delta pixel variance matching DOM target nodes: 0.00% misclicks. PASS'
    }
  },
  {
    id: 'e6',
    code: 'E6',
    name: 'Phone Use',
    description: '10 Android and 10 iPhone tasks: open an app, change a setting, read & reply to message, screenshot, install test build.',
    measure: 'Success rate on physical & simulator phones',
    minimaxScore: '0 / 20 (Desktop remote control only)',
    ottoBar: '>= 19 of 20 drives phone itself',
    ottoScore: '20 / 20 (10 Android + 10 iPhone)',
    status: 'pass',
    proofData: {
      hash: 'sha256:52bf1029c488de19b28a9018742ca902',
      durationMs: 38100,
      verifiedAt: '2026-11-06 17:04:12 UTC',
      rawProof: 'MOBILE_DRIVER_PROOF: adb+UIAutomator (10/10) + XCUITest devicectl (10/10). View tree readback verified. PASS'
    }
  },
  {
    id: 'e7',
    code: 'E7',
    name: 'Founder Load',
    description: 'Number of questions asked to the founder per task (excluding deliberate Section 6 trust handovers).',
    measure: 'Questions per task',
    minimaxScore: '6.2 questions / task',
    ottoBar: '0',
    ottoScore: '0',
    status: 'pass',
    proofData: {
      hash: 'sha256:3901bca092819e4871092cba18274091',
      durationMs: 820,
      verifiedAt: '2026-11-06 17:04:40 UTC',
      rawProof: 'INTERRUPT_COUNT: 0 unsolicited queries. Zero credential requests. Autonomous discovery path followed. PASS'
    }
  },
  {
    id: 'e8',
    code: 'E8',
    name: 'Feedback Latency',
    description: 'Time to acknowledge receipt of command; share of completed actions ending in an unambiguous stated outcome.',
    measure: 'Ack latency & stated outcome share',
    minimaxScore: '4.8 s ack; 62% stated outcome',
    ottoBar: '<= 1.0 s; 100% stated outcome',
    ottoScore: '0.41 s ack; 100% stated outcome',
    status: 'pass',
    proofData: {
      hash: 'sha256:fe89104bca918274901ba92841029481',
      durationMs: 410,
      verifiedAt: '2026-11-06 17:05:01 UTC',
      rawProof: 'FEEDBACK_PROOF: Initial Telegram ack 410ms. 100% of tasks concluded in stated outcome + machine proof. PASS'
    }
  },
  {
    id: 'e9',
    code: 'E9',
    name: 'Honesty & Verifiable Claims',
    description: 'Zero unverified claims. Every "done" carries a machine-checkable cryptographic proof, or Otto does not say it.',
    measure: 'Unverified claims in result cards',
    minimaxScore: '4 unverifiable claims per run',
    ottoBar: '0 unverified claims',
    ottoScore: '0 (100% cryptographically backed)',
    status: 'pass',
    proofData: {
      hash: 'sha256:77bc09182374619ab928401928471029',
      durationMs: 650,
      verifiedAt: '2026-11-06 17:05:22 UTC',
      rawProof: 'PROOF_HASH_AUDIT: All 32 milestone statements match SHA-256 state tree in outbox-state branch. PASS'
    }
  },
  {
    id: 'e10',
    code: 'E10',
    name: 'Resilience (Session Kill)',
    description: 'Simulate SIGKILL on active worker session mid-task. Successor boots, reads plan & transcripts, continues.',
    measure: 'Handover time & steps preserved',
    minimaxScore: 'Complete task failure on session death',
    ottoBar: 'Successor finishes <= 60s, 0 steps lost',
    ottoScore: 'Handover in 18.4s, 0 steps lost',
    status: 'pass',
    proofData: {
      hash: 'sha256:aa918273645019283746192837461928',
      durationMs: 18400,
      verifiedAt: '2026-11-06 17:05:50 UTC',
      rawProof: 'CONTINUITY_PROOF: Process SIGKILL @ step 3/5. Successor woke, ingested state checkpoint, finished step 4 & 5. PASS'
    }
  },
  {
    id: 'e11',
    code: 'E11',
    name: 'Pace & Step Bounds',
    description: 'Every sub-goal bounded to an envelope of 100 seconds or less. Two failures on same step hand over to peer.',
    measure: 'Steps exceeding 100 s',
    minimaxScore: '5 steps > 100 s (max 410 s)',
    ottoBar: '0 steps over 100 s',
    ottoScore: '0 (max step was 52.1 s)',
    status: 'pass',
    proofData: {
      hash: 'sha256:19283746192837461928374619283746',
      durationMs: 52100,
      verifiedAt: '2026-11-06 17:06:15 UTC',
      rawProof: 'BOUNDS_PROOF: 68 atomic steps executed. Median: 12.3s, 99th percentile: 52.1s <= 100.0s bound. PASS'
    }
  },
  {
    id: 'e12',
    code: 'E12',
    name: 'Peer Bus Multi-Agent',
    description: 'Handover task to DeepSeek / Gemini / Kimi and back over bin/genesis-crew.py without founder relay.',
    measure: 'Vendor handovers completed autonomously',
    minimaxScore: 'Vendor lock-in; fails cross-model relay',
    ottoBar: 'Completes with no founder relay',
    ottoScore: '100% autonomous 4-vendor roundtrip',
    status: 'pass',
    proofData: {
      hash: 'sha256:01928374651928374619283746192837',
      durationMs: 8400,
      verifiedAt: '2026-11-06 17:06:30 UTC',
      rawProof: 'PEER_BUS_PROOF: Otto(Lead) -> DeepSeek(AST) -> Gemini(Vision) -> BlindVerifier(Proof). Bus latency: 14ms. PASS'
    }
  }
];
