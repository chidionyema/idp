import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import {
  createInitialSovereignStandardsState,
  certifyAgentSessionOnboarding,
  compilePromptToFormalSpecAndBdd,
  interceptZombieBlockerQuery,
  queryWhiteBoxMemoryWithCausalProof,
  runDeterministicLegacyHygieneSweep,
  type SovereignStandardsGovernanceState,
} from './standardsMemoryBdd.ts';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const ROOT_DIR = path.resolve(__dirname, '../..');
const STATE_PATH = path.join(ROOT_DIR, '.ops/standards-memory-bdd-state.json');

function loadOrCreateState(): SovereignStandardsGovernanceState {
  try {
    const raw = fs.readFileSync(STATE_PATH, 'utf8');
    const parsed = JSON.parse(raw) as SovereignStandardsGovernanceState;
    if (parsed && parsed.schemaVersion === 'sovereign-standards-memory-bdd.v1') {
      return parsed;
    }
  } catch {
    // Seed initial state
  }
  const seeded = createInitialSovereignStandardsState();
  fs.mkdirSync(path.dirname(STATE_PATH), { recursive: true });
  fs.writeFileSync(STATE_PATH, JSON.stringify(seeded, null, 2), 'utf8');
  return seeded;
}

function saveState(state: SovereignStandardsGovernanceState): void {
  fs.mkdirSync(path.dirname(STATE_PATH), { recursive: true });
  fs.writeFileSync(STATE_PATH, JSON.stringify(state, null, 2), 'utf8');
}

function parseArgFlag(args: string[], flag: string, fallback: string): string {
  const idx = args.indexOf(flag);
  if (idx >= 0 && idx + 1 < args.length) return args[idx + 1];
  return fallback;
}

const args = process.argv.slice(2);
const cmd = args[0] || 'status';
const state = loadOrCreateState();

if (cmd === 'status') {
  console.log(
    JSON.stringify(
      {
        schemaVersion: state.schemaVersion,
        constitutionSha256: state.constitutionSha256,
        enforcedRulesCount: state.enforcedRules.length,
        ossToolsPinned: state.ossToolchain.length,
        tombstonesSealed: state.tombstones.length,
        whiteBoxMemoryCells: state.whiteBoxMemory.totalCells,
        agentSelfWriteAllowed: state.whiteBoxMemory.agentSelfWriteAllowed,
        activeFormalSpecs: state.formalSpecs.length,
        dataStoresMerkleSynced: state.dataGovernanceStores.length,
      },
      null,
      2
    )
  );
} else if (cmd === 'onboard') {
  const session = parseArgFlag(args, '--session', 'ses-aurelius-53');
  const actor = parseArgFlag(args, '--actor', 'did:estate:principal:aurelius-marcus');
  const pack = parseArgFlag(args, '--pack', 'PACK-15');
  const cert = certifyAgentSessionOnboarding(state, {
    agentSessionId: session,
    actorDid: actor,
    actorRealName: 'Aurelius Marcus (Chief Principal)',
    targetPackId: pack,
    busDoorsProbed: true,
    activeSpecId: state.formalSpecs[0]?.specId ?? null,
  });
  saveState(state);
  console.log(JSON.stringify(cert, null, 2));
  if (cert.verdict !== 'CERTIFIED_SESSION_READY') process.exit(1);
} else if (cmd === 'spec') {
  const promptText = args.slice(1).join(' ').trim() || 'Enforce deterministic SpecGate BDD across PACK-15';
  const spec = compilePromptToFormalSpecAndBdd(state, {
    rawFounderPrompt: promptText,
    lockAmbiguity: true,
  });
  saveState(state);
  console.log(JSON.stringify(spec, null, 2));
} else if (cmd === 'intercept') {
  const question = args.slice(1).join(' ').trim() || 'How do we fix Telegram 3327 and OKE #2468?';
  const out = interceptZombieBlockerQuery(state, question);
  saveState(state);
  console.log(JSON.stringify(out, null, 2));
} else if (cmd === 'memory') {
  const query = args.slice(1).join(' ').trim() || 'greenlane merge-base omega hal';
  const out = queryWhiteBoxMemoryWithCausalProof(state, { queryText: query });
  saveState(state);
  console.log(JSON.stringify(out, null, 2));
} else if (cmd === 'audit') {
  const report = runDeterministicLegacyHygieneSweep(state);
  saveState(state);
  console.log(
    JSON.stringify(
      {
        hygieneSweep: report,
        dataGovernanceStores: state.dataGovernanceStores,
      },
      null,
      2
    )
  );
} else {
  console.error(
    `Unknown bin/standards command "${cmd}". Supported: status | onboard | spec | intercept | memory | audit`
  );
  process.exit(1);
}
