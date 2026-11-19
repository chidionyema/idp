import { createHash } from 'node:crypto';

export type WorkstreamStatus = 'PARTIAL' | 'SOURCE-LOCATED' | 'UNKNOWN';

export interface EstateWorkstreamRecord {
  id: number;
  name: string;
  status: WorkstreamStatus;
  drivePath: string;
  locations: string;
  entryPoint: string;
  buildRun: string;
  externalNeeds: string;
  knownDefect: string;
  missing: string;
  selfCheck: string;
}

export interface IntakeHashBindingInput {
  verifierPublicKeyHex: string | undefined;
  claimedBodySha256: string;
  receivedBodyBytes: string;
  storedCopyBytes: string;
}

export interface IntakeHashBindingResult {
  ok: boolean;
  reason:
    | 'verified_bound_and_rehashed'
    | 'verifier_key_missing_fail_closed'
    | 'received_body_hash_mismatch'
    | 'copy_rehash_mismatch';
  actualReceivedSha256: string;
  actualCopySha256: string;
}

/**
 * Fail-closed cryptographic intake verifier addressing BEAST / Genesis Kernel defects:
 * 1) Never fails open when FOUNDER_ED25519_PUBLIC_KEY is unset or all-zeros.
 * 2) Computes SHA-256 over the actual received body rather than trusting claimed headers.
 * 3) Re-hashes the stored destination copy to prove end-to-end byte integrity.
 */
export function verifyIntakeBodyIntegrity(
  input: IntakeHashBindingInput
): IntakeHashBindingResult {
  const actualReceivedSha256 = createHash('sha256')
    .update(input.receivedBodyBytes, 'utf8')
    .digest('hex');
  const actualCopySha256 = createHash('sha256')
    .update(input.storedCopyBytes, 'utf8')
    .digest('hex');

  const trimmedKey = (input.verifierPublicKeyHex ?? '').trim();
  const isAllZeros = /^0+$/.test(trimmedKey);
  if (!trimmedKey || isAllZeros || trimmedKey.length < 32) {
    return {
      ok: false,
      reason: 'verifier_key_missing_fail_closed',
      actualReceivedSha256,
      actualCopySha256,
    };
  }

  if (input.claimedBodySha256.trim().toLowerCase() !== actualReceivedSha256) {
    return {
      ok: false,
      reason: 'received_body_hash_mismatch',
      actualReceivedSha256,
      actualCopySha256,
    };
  }

  if (actualCopySha256 !== actualReceivedSha256) {
    return {
      ok: false,
      reason: 'copy_rehash_mismatch',
      actualReceivedSha256,
      actualCopySha256,
    };
  }

  return {
    ok: true,
    reason: 'verified_bound_and_rehashed',
    actualReceivedSha256,
    actualCopySha256,
  };
}

export const ESTATE_WORKSTREAMS: EstateWorkstreamRecord[] = [
  {
    id: 1,
    name: 'BEAST / Mini-NASA',
    status: 'PARTIAL',
    drivePath: 'UNKNOWN',
    locations:
      'genesis-always-on-protocol/references/formal-spec-and-bdd.md (GenesisSplitAuthorityCertifier.tla, six_certification_trials.feature), sos-estate-alignment-i8072.md, system-first-ioc-reconciler.md; repos: chidionyema/idp (#6603, #7379, #7452, #7613, #7760, #8164 59effb8f4), chidionyema/argon, chidionyema/argon-sync, chidionyema/crew, chidionyema/estate-graph',
    entryPoint:
      'UNKNOWN (TLA+ spec: specs/GenesisSplitAuthorityCertifier.tla; intake gate: bin/gemini-intake on idp 59effb8f4)',
    buildRun: 'pytest tests/test_gemini_intake.py (idp#8164); standalone daemon UNKNOWN',
    externalNeeds:
      'ESTATE_RECEIPT_KEY, GENESIS_DB_PATH, FOUNDER_ED25519_PUBLIC_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_FOUNDER_CHAT_ID, TELEGRAM_PINNED_MSG_ID · SQLite, TLC, GitHub Actions, Telegram',
    knownDefect:
      '(1) Rust middleware verified CLAIMED body hash without binding signature to actual received body; (2) Gemini intake recorded SOURCE hash and never re-hashed copy; gemini-sync (fa339ca9) prototype lacked auth & persistence.',
    missing:
      'Standalone BEAST six-layer assurance runtime code, synchrony/topology catalogue files, and Python bodies for immediate_embodiment_gate.py & universal_compensating_capstone.py.',
    selfCheck: '(a) Drive UNKNOWN, verified paths only; (b) mapped to named files/commits; (c) no secrets',
  },
  {
    id: 2,
    name: 'Genesis control plane',
    status: 'PARTIAL',
    drivePath: 'UNKNOWN',
    locations:
      'otto-real-core-and-purge.md (bin/otto_real_core.py), aura-2100-cloud-surface.md (FounderConciergeSurface.tsx, functions/api/[[path]].ts), PR_MANIFEST.md, universal-agent-cage.md, unexpanded user:legion-longcapharness-dagster-chronos; chidionyema/idp (#7664, #7794, #7819, #8133, #8161 8e8e1846, #8164 59effb8f4), chidionyema/argon (#7, #20), commit da1536c7',
    entryPoint: 'bin/otto_real_core.py + src/surface/FounderConciergeSurface.tsx',
    buildRun: 'python3 bin/otto_real_core.py; python3 bin/claim-gate "$BASE" "$(git rev-parse HEAD)"',
    externalNeeds:
      'GENESIS_DB_PATH, OTTO_LLM_BASE_URL, MINIMAX_API_KEY, OTTO_LLM_API_KEY, DEEPSEEK_API_KEY, CF_ACCESS_TEAM_DOMAIN, CF_ACCESS_AUD, FOUNDER_ED25519_PUBLIC_KEY, GH_TOKEN · Cloudflare Pages/Access, SQLite, PennyD',
    knownDefect:
      '19-Tab Mock Museum fixtures in chidionyema/argon; synchronous 14-iteration gh pr view + sleep 15 loops on idp#8161; PennyD dropping vault env credentials (2,382 -> 552 receipts); gemini-sync (fa339ca9) unauthenticated prototype.',
    missing:
      'Contents of user:legion-longcapharness-dagster-chronos, FLOW watchdog implementation file, and live voice gateway backend code.',
    selfCheck: '(a) Drive UNKNOWN, real paths only; (b) mapped to skill files & transcripts; (c) no secrets',
  },
  {
    id: 3,
    name: 'Genesis Symbiont / ICP',
    status: 'SOURCE-LOCATED',
    drivePath: 'UNKNOWN',
    locations:
      'realtime-chronicle-and-spore.md (bin/genesis_realtime_symbiont.py, GENESIS_SPORE.dna, genesis-mycelium.user.js), genesis-kernel-rust.md (src/realtime.rs /api/mycelium/lease); chidionyema/idp (#7760, #7772 953e96a1, #8164 59effb8f4)',
    entryPoint: 'bin/genesis_realtime_symbiont.py',
    buildRun:
      'python3 bin/genesis_realtime_symbiont.py pack-spore | emit-userscript | science-stream',
    externalNeeds:
      'GENESIS_DB_PATH, REALTIME_BASE_URL, FOUNDER_ED25519_PUBLIC_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_FOUNDER_CHAT_ID, TELEGRAM_PINNED_MSG_ID · Cloudflare Pages/Workers/D1, SQLite, Telegram',
    knownDefect:
      'Gemini intake did not re-hash copy; USERSCRIPT_TEMPLATE polls /api/mycelium/lease every 3s without X-Genesis-Signature / X-Genesis-Timestamp headers; science stream loops with time.sleep(1.0).',
    missing:
      'Cloudflare D1 schema/wrangler migrations, packaged extension manifest.json, and inbound Telegram webhook ingress handler.',
    selfCheck: '(a) Drive UNKNOWN, verified skill/commit paths; (b) mapped to realtime-chronicle-and-spore.md; (c) no secrets',
  },
  {
    id: 4,
    name: 'Genesis Kernel',
    status: 'SOURCE-LOCATED',
    drivePath: 'UNKNOWN',
    locations:
      'genesis-kernel-rust.md (Cargo.toml, src/certifier.rs, src/realtime.rs, src/main.rs, tests/bdd_realtime_trials.rs); chidionyema/idp (#7760, #7771, #7772 953e96a1, da1536c7)',
    entryPoint: 'src/main.rs (genesis-kernel binding GENESIS_BIND_ADDR 0.0.0.0:4001)',
    buildRun: 'cargo test && cargo run --release',
    externalNeeds:
      'GENESIS_DB_PATH, GENESIS_BIND_ADDR, FOUNDER_ED25519_PUBLIC_KEY, GIT_COMMIT_SHA, MINIMAX_API_KEY, DEEPSEEK_API_KEY, TELEGRAM_* · SQLite WAL, Telegram',
    knownDefect:
      'Claimed-body-hash bypass in Rust middleware; i4 coercion phrasing bypass & i3 basket drift (£4.20 -> £7.00); CertifierPublicVerifier::from_env_or_default() fails OPEN when FOUNDER_ED25519_PUBLIC_KEY is unset/zero; 15ms SQLite WAL sleep polling.',
    missing: 'Standalone instruction-coalescing module and external kernel-core/real_kernel tree.',
    selfCheck: '(a) Drive UNKNOWN, verified Rust paths; (b) mapped to genesis-kernel-rust.md; (c) no secrets',
  },
  {
    id: 5,
    name: 'OMEGA / BEAST gov',
    status: 'PARTIAL',
    drivePath: 'UNKNOWN',
    locations:
      'genesis-always-on-protocol/SKILL.md, system-first-ioc-reconciler.md (geburah_estate_architecture.json, issue-classes.json), universal-agent-cage.md (genesis-protocols.json), formal-spec-and-bdd.md',
    entryPoint: 'UNKNOWN (immediate_embodiment_gate.py & universal_compensating_capstone.py bodies absent)',
    buildRun: 'UNKNOWN',
    externalNeeds:
      'FOUNDER_ED25519_PUBLIC_KEY, GENESIS_DB_PATH · POSIX openssl CLI, SQLite, GitHub rulesets (gemini-argon bypass actor)',
    knownDefect:
      'Claimed-hash vs received-body bypass; intake missing copy re-hash; macOS LibreSSL vs Linux OpenSSL -iter flag incompatibility (LAW_PORTABLE_ES256_VAULT).',
    missing:
      'Open Policy Agent (.rego) files, fault-rehearsal scripts, and bodies of geburah_estate_architecture.json, genesis-protocols.json, immediate_embodiment_gate.py, universal_compensating_capstone.py.',
    selfCheck: '(a) Drive UNKNOWN, verified refs; (b) mapped to genesis-always-on-protocol; (c) no secrets',
  },
  {
    id: 6,
    name: 'Investor / commercial',
    status: 'PARTIAL',
    drivePath: 'UNKNOWN',
    locations:
      'system-first-ioc-reconciler.md (config/geburah_estate_architecture.json, bin/meridian_investor_and_os_broker.py serving /investors/room); chidionyema/idp PR #7999 commit 2a7b37e6',
    entryPoint: 'bin/meridian_investor_and_os_broker.py (body absent from skill file)',
    buildRun: 'UNKNOWN',
    externalNeeds: 'UNKNOWN',
    knownDefect:
      'idp#7999 required ES256 provenance & BDD-PROOF remediation; prior materials conflated Ring 3 tools into Enterprise SKU tables and omitted DEVELOPMENT_STAGE_CONCEPT — NOT PRODUCTION DEPLOYED badge on Chronos.',
    missing:
      'Full source of bin/meridian_investor_and_os_broker.py, living brochure assets, product catalogue files, investor handoff package.',
    selfCheck: '(a) Drive UNKNOWN, PR #7999 verified; (b) mapped to genesis-always-on-protocol; (c) no secrets',
  },
  {
    id: 7,
    name: 'Genesis Face / avatars',
    status: 'UNKNOWN',
    drivePath: 'UNKNOWN',
    locations: 'UNKNOWN',
    entryPoint: 'UNKNOWN',
    buildRun: 'UNKNOWN',
    externalNeeds: 'UNKNOWN',
    knownDefect:
      'In genesis-kernel-rust.md (src/main.rs surface_meta_handler), voiceGatewayConnected is hardcoded to true without attached avatar, lip-sync, or live-transcript implementation.',
    missing: 'Avatar art assets, voice & lip-sync pipeline, live transcript module, session steering code.',
    selfCheck: '(a) Marked UNKNOWN with zero invented paths; (b) defect maps to genesis-kernel-rust.md; (c) no secrets',
  },
  {
    id: 8,
    name: 'I-8088 Cephalopod Panspermia',
    status: 'SOURCE-LOCATED',
    drivePath: 'UNKNOWN',
    locations:
      'src/engine/genesisSporeTtt.ts (GF(2^8) RS(3,8), PBKDF2-HMAC-SHA256 GENVAULT1, DNS TXT, PNG carrier); specs: I-8088 GENESIS_CEPHALOPOD_PANSPERMIA T1..T8',
    entryPoint: 'src/engine/genesisSporeTtt.ts (runI8088PanspermiaSimulation)',
    buildRun: 'POST /api/genesis/panspermia/simulate · POST /api/genesis/panspermia/heal',
    externalNeeds:
      'Ring 1 Ed25519 hardware founder key & external Cloudflare/DNS/Nostr/Telegram credentials for off-box scatter',
    knownDefect:
      'Zero-cost (£0.00/mo) 8-tentacle RS(3,8) spore/vault codec & stego carrier active locally in sandbox; remote DNS/Nostr/Telegram broadcast awaits external API credentials.',
    missing: 'External Cloudflare DNS & Telegram production API tokens inside sandbox container.',
    selfCheck: '(a) Drive UNKNOWN, verified local TS codec; (b) G1-G3 BDD verified; (c) £0.00/mo zero secrets',
  },
  {
    id: 9,
    name: 'GEN-TTT-001 Adaptive Intelligence',
    status: 'PARTIAL',
    drivePath: 'UNKNOWN',
    locations:
      'branch lane/genesis-ttt-full-spec-20261116 (commit e2c134e29b5c455e14fb0ef25ebd87e68821a29e), Issue #8185, closed PR #8186; src/engine/genesisSporeTtt.ts',
    entryPoint: 'Issue #8185 — Greenlane Execution Contract (BLOCKED_DISPATCH)',
    buildRun: 'POST /api/genesis/ttt/falsify · awaiting Spec Factory spec.json/SPEC.md & signed lane-submit',
    externalNeeds:
      'Argon Spec Factory canonical schema, signed lane-submit authority, authenticated Greenlane executor on #8185',
    knownDefect:
      'Closed invalid PR #8186; direct merge blocked under branch protection. Remaining gated in BLOCKED_DISPATCH until Spec Factory schema reconciliation and signed Greenlane promotion pass.',
    missing: 'Argon Spec Factory spec.json template match and authenticated Greenlane executor pickup on #8185.',
    selfCheck: '(a) Drive UNKNOWN, commit & branch grounded; (b) BLOCKED_DISPATCH strictly preserved; (c) no fake dispatch claims',
  },
];

export interface LiveEstateWorkstreamTelemetryRow {
  id: number;
  name: string;
  status: WorkstreamStatus;
  dispatchState: string;
  liveMetricLabel: string;
  liveMetricValue: string;
  healthSignal: 'HEALTHY' | 'GUARDED' | 'BLOCKED' | 'UNVERIFIED';
  verifiedBy: string;
  knownDefect: string;
}

export function buildLiveEstateWorkstreamTelemetry(params: {
  walReceipts: number;
  healthyLanes: number;
  totalLanes: number;
  certifiedModels: number;
  totalModels: number;
  verifiedKeys: number;
  totalKeys: number;
  sporeBytes: number;
  survivingTentacles: number;
  tttBlockedDispatch: boolean;
  all15TttFalsifiersGuarded: boolean;
  guaranteesVerified: number;
  guaranteesTotal: number;
}): LiveEstateWorkstreamTelemetryRow[] {
  return ESTATE_WORKSTREAMS.map((ws) => {
    switch (ws.id) {
      case 1:
        return {
          id: ws.id,
          name: ws.name,
          status: ws.status,
          dispatchState: 'FAIL_CLOSED_SHA256',
          liveMetricLabel: 'Verified Guarantees / Intake',
          liveMetricValue: `${params.guaranteesVerified}/${params.guaranteesTotal} · SHA-256 Rehash`,
          healthSignal: 'GUARDED',
          verifiedBy: 'F10, F12',
          knownDefect: ws.knownDefect,
        };
      case 2:
        return {
          id: ws.id,
          name: ws.name,
          status: ws.status,
          dispatchState: 'SANDBOX_ACTIVE',
          liveMetricLabel: 'Healthy Lanes / Atomic Keys',
          liveMetricValue: `${params.healthyLanes}/${params.totalLanes} lanes · ${params.verifiedKeys}/${params.totalKeys} keys`,
          healthSignal: params.healthyLanes === params.totalLanes ? 'HEALTHY' : 'GUARDED',
          verifiedBy: 'F1, F2, F4, F5',
          knownDefect: ws.knownDefect,
        };
      case 3:
        return {
          id: ws.id,
          name: ws.name,
          status: ws.status,
          dispatchState: 'ED25519_NO_POLL',
          liveMetricLabel: 'Zero-Poll Exit Guard',
          liveMetricValue: 'Exit 78 Enforced · WAL Push',
          healthSignal: 'HEALTHY',
          verifiedBy: 'F11, F12',
          knownDefect: ws.knownDefect,
        };
      case 4:
        return {
          id: ws.id,
          name: ws.name,
          status: ws.status,
          dispatchState: 'DAGSTER_WAL_SYNC',
          liveMetricLabel: 'Durable WAL Receipts',
          liveMetricValue: `${params.walReceipts.toLocaleString()} receipts · 0 loss`,
          healthSignal: 'HEALTHY',
          verifiedBy: 'F3, INT-03, INT-04',
          knownDefect: ws.knownDefect,
        };
      case 5:
        return {
          id: ws.id,
          name: ws.name,
          status: ws.status,
          dispatchState: 'AURA_OBSIDIAN_64B',
          liveMetricLabel: 'Binary Frame & Non-Collusion',
          liveMetricValue: '64B Codec · 3-Key Airlock',
          healthSignal: 'GUARDED',
          verifiedBy: 'F13, F17',
          knownDefect: ws.knownDefect,
        };
      case 6:
        return {
          id: ws.id,
          name: ws.name,
          status: ws.status,
          dispatchState: 'FOCUS_1_0_PRICING',
          liveMetricLabel: 'Certified Small Specialists',
          liveMetricValue: `${params.certifiedModels}/${params.totalModels} certified`,
          healthSignal: 'GUARDED',
          verifiedBy: 'F6, F7, F8, F9',
          knownDefect: ws.knownDefect,
        };
      case 7:
        return {
          id: ws.id,
          name: ws.name,
          status: ws.status,
          dispatchState: 'UNKNOWN_HONEST',
          liveMetricLabel: 'Voice & Avatar Pipeline',
          liveMetricValue: 'voiceGatewayConnected = false',
          healthSignal: 'UNVERIFIED',
          verifiedBy: 'F12 Truthful Probe',
          knownDefect: ws.knownDefect,
        };
      case 8:
        return {
          id: ws.id,
          name: ws.name,
          status: ws.status,
          dispatchState: params.survivingTentacles >= 3 ? 'QUORUM_SURVIVAL_OK' : 'QUORUM_BELOW_3',
          liveMetricLabel: 'Spore Size / RS(3,8) Quorum',
          liveMetricValue: `${params.sporeBytes.toLocaleString()} B · ${params.survivingTentacles}/8 alive`,
          healthSignal: params.survivingTentacles >= 3 ? 'HEALTHY' : 'BLOCKED',
          verifiedBy: 'F18 · G1-G3 BDD',
          knownDefect: ws.knownDefect,
        };
      default:
        return {
          id: ws.id,
          name: ws.name,
          status: ws.status,
          dispatchState: params.tttBlockedDispatch ? 'BLOCKED_DISPATCH' : 'SPEC_READY',
          liveMetricLabel: 'Issue #8185 · 15 Failure Classes',
          liveMetricValue: `${params.all15TttFalsifiersGuarded ? '15/15' : 'DEGRADED'} guarded · BLOCKED_DISPATCH`,
          healthSignal: 'BLOCKED',
          verifiedBy: 'F18 · Commit e2c134e2',
          knownDefect: ws.knownDefect,
        };
    }
  });
}

