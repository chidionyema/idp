/**
 * Operation Phoenix v2 Standalone Cold-Boot & Union Round Table CLI Runner
 * Runs identically on laptops, Linux servers, or daily 06:00 UTC GitHub Actions.
 */
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import {
  BootStageId,
  PhoenixDailyBootEngine,
} from '../src/engine/phoenixDailyBoot';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(__dirname, '..');

function parseArgs(argv: string[]) {
  const args = new Set(argv);
  const faultArg = argv.find((a) => a.startsWith('--simulate-fault='));
  const simulateP0FaultStage = faultArg
    ? (faultArg.split('=')[1] as BootStageId)
    : null;
  const rehearsal = args.has('--rehearsal');
  const jsonOutput = args.has('--json');
  const skipNetwork = args.has('--skip-network');
  return {
    probeMode: rehearsal ? ('CLEANROOM_REHEARSAL' as const) : ('LIVE_ESTATE' as const),
    simulateP0FaultStage,
    jsonOutput,
    skipNetwork,
  };
}

async function main() {
  const opts = parseArgs(process.argv.slice(2));
  const engine = new PhoenixDailyBootEngine({ repoRoot });

  const run = await engine.runColdBootDrill({
    triggerSource: opts.probeMode === 'CLEANROOM_REHEARSAL' ? 'SANDBOX_REHEARSAL' : 'DAILY_SCHEDULE',
    probeMode: opts.probeMode,
    simulateP0FaultStage: opts.simulateP0FaultStage,
    runCleanRoomTsc: true,
    skipLiveNetwork: opts.skipNetwork,
  });

  if (opts.jsonOutput) {
    console.log(JSON.stringify(engine.getSnapshot(), null, 2));
  } else {
    console.log('=== OPERATION PHOENIX DAILY COLD-BOOT & ROUND TABLE REPORT ===');
    console.log(`Drill ID       : ${run.drillId}`);
    console.log(`Probe Mode     : ${run.probeMode}`);
    console.log(`Source HEAD    : ${run.sourceHeadSha}`);
    console.log(`Bundle SHA-256 : ${run.bundleSha256} (${(run.bundleBytes / (1024 * 1024)).toFixed(2)} MiB)`);
    console.log(`Overall Verdict: ${run.overallVerdict}`);
    console.log('');
    for (const s of run.stages) {
      console.log(`  [${s.status.padEnd(16)}] Stage ${s.order}: ${s.title} (${s.durationMs}ms)`);
      console.log(`      ${s.summary}`);
    }
    console.log('');
    console.log(`Unblock Pack (${run.unblockPack.length} item(s)):`);
    for (const item of run.unblockPack) {
      console.log(`  - [${item.category}] ${item.title}: ${item.rootCause}`);
      for (const cmd of item.commands) {
        console.log(`      $ ${cmd}`);
      }
    }
  }

  if (
    run.overallVerdict !== 'QUORUM_READY_AWAITING_GO' &&
    run.overallVerdict !== 'OPERATIONAL_100_PCT_SEALED'
  ) {
    process.exitCode = 1;
  }
}

void main();
