/**
 * packages/io-engine/cli.ts — Canonical IO Engine TypeScript CLI Implementation (PACK-15)
 * Invoked natively via `./bin/io <command>` across macOS & Linux.
 */

import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import {
  createInitialIoCanonicalState,
  evaluateOmniscientMegaOracleAndCausalAdjudicator,
  evaluateSynapseEstateWideSyncAndZeroTouchOperationalization,
  startEstateSession,
  triageAllUnownedWorkGraphClusters,
  evaluateAndTrainRealtimeActivity,
  type IoCanonicalWorkGraphState,
} from './index.ts';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const ROOT_DIR = path.resolve(__dirname, '../..');
const STATE_PATH = path.join(ROOT_DIR, '.ops', 'io-work-graph.json');
const DATASET_PATH = path.join(ROOT_DIR, '.ops', 'realtime-training-dataset.jsonl');
const SPORE_PATH = path.join(ROOT_DIR, '.genesis', 'GENESIS_SPORE.dna');

async function loadState(): Promise<IoCanonicalWorkGraphState> {
  try {
    const raw = await fs.readFile(STATE_PATH, 'utf8');
    return JSON.parse(raw) as IoCanonicalWorkGraphState;
  } catch {
    const seeded = createInitialIoCanonicalState(new Date().toISOString());
    await saveState(seeded);
    return seeded;
  }
}

async function saveState(state: IoCanonicalWorkGraphState): Promise<void> {
  await fs.mkdir(path.dirname(STATE_PATH), { recursive: true });
  await fs.writeFile(STATE_PATH, JSON.stringify(state, null, 2), 'utf8');
  const lines = state.trainingTuples
    .slice()
    .reverse()
    .map((t) => JSON.stringify(t))
    .join('\n');
  await fs.writeFile(DATASET_PATH, lines ? `${lines}\n` : '', 'utf8');
}

function getArg(args: string[], flag: string, fallback: string): string {
  const idx = args.indexOf(flag);
  if (idx >= 0 && idx + 1 < args.length) return args[idx + 1];
  return fallback;
}

async function main() {
  const [, , subcmd = 'status', ...rest] = process.argv;
  const state = await loadState();
  const sporeStat = await fs.stat(SPORE_PATH).catch(() => null);
  const canonicalSporeBytes = sporeStat ? sporeStat.size : 1461;

  if (subcmd === 'status') {
    const unowned = state.workGraphNodes.filter((n) => n.disposition === 'UNOWNED_DRIFT');
    console.log(
      JSON.stringify(
        {
          package: '@meridian-estate/io-engine',
          packId: 'PACK-15',
          version: '1.0.0',
          accountableFounder: state.accountableFounder,
          totalCanonicalPacks: state.packs.length,
          ownedDomains: state.domains.length,
          activeSessions: state.activeSessions.length,
          unownedClusters: unowned.length,
          unownedArtifacts: unowned.reduce((s, n) => s + n.artifactCount, 0),
          evalReceiptsCount: state.evalReceipts.length,
          trainingTuplesCount: state.trainingTuples.length,
          canonicalSporeBytes,
          busRoutes: state.busEndpoints.map((b) => b.route),
        },
        null,
        2
      )
    );
    return;
  }

  if (subcmd === 'packs') {
    console.log(JSON.stringify({ totalPacks: state.packs.length, packs: state.packs }, null, 2));
    return;
  }

  if (subcmd === 'session-start') {
    const actorDid = getArg(rest, '--actor-did', 'did:estate:principal:aurelius-marcus');
    const domainId = getArg(rest, '--domain', 'DOM-IO-ENGINE');
    const packId = getArg(rest, '--pack', 'PACK-15');
    const res = startEstateSession(state, {
      actorDid,
      domainId,
      packId,
      surfaceOrigin: 'MAC_HOST_CLI',
    });
    await saveState(state);
    if (!res.ok) {
      console.error(JSON.stringify(res, null, 2));
      process.exit(1);
    }
    console.log(JSON.stringify(res, null, 2));
    return;
  }

  if (subcmd === 'oracle') {
    const sessionId = getArg(rest, '--session', state.activeSessions[0]?.sessionId ?? 'ses-aurelius-io-01');
    const actorDid = getArg(rest, '--actor-did', 'did:estate:principal:aurelius-marcus');
    const targetLayer = getArg(rest, '--layer', 'packages/io-engine/index.ts');
    const proposed = getArg(rest, '--proposed', '');
    const verdict = evaluateOmniscientMegaOracleAndCausalAdjudicator(state, {
      sessionId,
      actorDid,
      targetLayer,
      proposedSymbolOrFile: proposed || undefined,
      sporeBytesObserved: canonicalSporeBytes,
    });
    evaluateAndTrainRealtimeActivity(state, {
      sessionId,
      actorDid,
      domainId: 'DOM-IO-ENGINE',
      packId: 'PACK-15',
      actionType: 'CLI_IO_ORACLE_ADJUDICATE',
      summary: `bin/io oracle on ${targetLayer} -> ${verdict.verdict}`,
      evidenceVerified: verdict.ring0InvariantsPassed,
      writeBackArtifactRef: `oracle:${verdict.causalChainHash.slice(0, 14)}`,
      isDuplicateRebuildAttempt: verdict.verdict === 'HALT_DUPLICATE_REBUILD_PREVENTED',
    });
    await saveState(state);
    console.log(JSON.stringify(verdict, null, 2));
    return;
  }

  if (subcmd === 'synapse') {
    const sessionId = getArg(rest, '--session', state.activeSessions[0]?.sessionId ?? 'ses-aurelius-io-01');
    const actorDid = getArg(rest, '--actor-did', 'did:estate:principal:aurelius-marcus');
    const hostSporeBytes = Number(getArg(rest, '--host-spore-bytes', String(canonicalSporeBytes)));
    const result = evaluateSynapseEstateWideSyncAndZeroTouchOperationalization(state, {
      sessionId,
      actorDid,
      localHostSporeBytes: hostSporeBytes,
      canonicalSporeBytes,
      argonBackupSha: 'b31e032',
      idpBackupSha: 'd4b1349ce',
      cloudPreviewAppletId: 'fe43cf69-d529-4d49-ad17-e2d3a79ce7eb',
    });
    evaluateAndTrainRealtimeActivity(state, {
      sessionId,
      actorDid,
      domainId: 'DOM-ESTATE-BUS',
      packId: 'PACK-15',
      actionType: 'CLI_IO_SYNAPSE_SYNC',
      summary: `bin/io synapse -> ${result.syncVerdict} (spore ${canonicalSporeBytes}B)`,
      evidenceVerified: true,
      writeBackArtifactRef: `synapse:${result.syncDigestSha256.slice(0, 14)}`,
    });
    await saveState(state);
    console.log(JSON.stringify(result, null, 2));
    return;
  }

  if (subcmd === 'triage-all') {
    const sessionId = getArg(rest, '--session', state.activeSessions[0]?.sessionId ?? 'ses-aurelius-io-01');
    const res = triageAllUnownedWorkGraphClusters(state, sessionId);
    await saveState(state);
    console.log(JSON.stringify(res, null, 2));
    return;
  }

  console.error(
    `Unknown bin/io command "${subcmd}". Supported: status | packs | session-start | oracle | synapse | triage-all`
  );
  process.exit(1);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
