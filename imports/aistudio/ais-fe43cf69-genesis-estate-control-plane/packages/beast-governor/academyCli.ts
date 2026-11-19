import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import {
  createInitialGenesisAcademyState,
  simulateAsymmetricAcademyEconomics,
  generateVerifiableAcademyCredentialMarkdown,
  verifyAcademyCredentialDigest,
  type GenesisAcademyState,
} from './genesisAcademy.ts';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const ROOT_DIR = path.resolve(__dirname, '../..');
const STATE_PATH = path.join(ROOT_DIR, '.ops/genesis-academy-state.json');

function loadOrCreateState(): GenesisAcademyState {
  try {
    const raw = fs.readFileSync(STATE_PATH, 'utf8');
    const parsed = JSON.parse(raw) as GenesisAcademyState;
    if (parsed && parsed.schemaVersion === 'genesis-asymmetric-academy.v1') {
      return parsed;
    }
  } catch {
    // Seed initial Academy state
  }
  const seeded = createInitialGenesisAcademyState();
  fs.mkdirSync(path.dirname(STATE_PATH), { recursive: true });
  fs.writeFileSync(STATE_PATH, JSON.stringify(seeded, null, 2), 'utf8');
  return seeded;
}

const args = process.argv.slice(2);
const cmd = args[0] || 'status';
const state = loadOrCreateState();

if (cmd === 'status') {
  console.log(
    JSON.stringify(
      {
        schemaVersion: state.schemaVersion,
        learner: state.learner.learnerName,
        activeLens: state.learner.activeLens,
        totalXp: state.learner.totalXp,
        streakDays: state.learner.streakDays,
        completedSparks: `${state.learner.completedSparkIds.length}/${state.sparks.length}`,
        completedLabs: `${state.learner.completedLabIds.length}/${state.labs.length}`,
        unlockedCerts: state.certifications.filter((c) => c.unlocked).map((c) => c.tierId),
        defaultArrUsd: state.defaultRevenueModel.annualizedArrUsd,
        grossMarginPct: state.defaultRevenueModel.grossMarginPct,
      },
      null,
      2
    )
  );
} else if (cmd === 'credential') {
  console.log(generateVerifiableAcademyCredentialMarkdown(state, state.academyMerkleSha256));
} else if (cmd === 'verify') {
  const shaIdx = args.indexOf('--sha');
  const candidate = shaIdx >= 0 && shaIdx + 1 < args.length ? args[shaIdx + 1] : '';
  const verdict = verifyAcademyCredentialDigest(state, candidate);
  console.log(JSON.stringify(verdict, null, 2));
  if (!verdict.valid) process.exit(1);
} else if (cmd === 'economics') {
  console.log(JSON.stringify(simulateAsymmetricAcademyEconomics(), null, 2));
} else {
  console.error(
    `Unknown bin/academy command "${cmd}". Supported: status | credential | verify --sha <hex> | economics`
  );
  process.exit(1);
}
