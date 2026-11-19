#!/usr/bin/env npx tsx
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import {
  createInitialBeastGovernorState,
  runFractalContinuousSweep,
  evaluateBeastRegoPolicy,
  updateBeastDynamicDials,
  triggerBeastDisruptiveIncident,
  resolveBeastIncident,
  runBeastDreamsCycle,
  type BeastGovernorState,
  type BeastFaultKind,
  type BeastPosturePreset,
} from './index.ts';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const STATE_PATH = path.resolve(__dirname, '../../.ops/beast-governor-state.json');

async function loadState(): Promise<BeastGovernorState> {
  try {
    const raw = await fs.readFile(STATE_PATH, 'utf8');
    return JSON.parse(raw) as BeastGovernorState;
  } catch {
    const seeded = createInitialBeastGovernorState();
    await persistState(seeded);
    return seeded;
  }
}

async function persistState(state: BeastGovernorState): Promise<void> {
  await fs.mkdir(path.dirname(STATE_PATH), { recursive: true });
  await fs.writeFile(STATE_PATH, JSON.stringify(state, null, 2), 'utf8');
}

function getFlag(args: string[], flag: string): string | undefined {
  const idx = args.indexOf(flag);
  if (idx >= 0 && idx + 1 < args.length) return args[idx + 1];
  return undefined;
}

async function main() {
  const args = process.argv.slice(2);
  const cmd = args[0] || 'status';
  const state = await loadState();

  if (cmd === 'status' || cmd === 'sweep') {
    runFractalContinuousSweep(state);
    await persistState(state);
    console.log(
      JSON.stringify(
        {
          ok: state.allLayersConsistent,
          sweepSequence: state.sweepSequence,
          preset: state.dials.preset,
          fractalConsistencyRootSha256: state.fractalConsistencyRootSha256,
          allLayersConsistent: state.allLayersConsistent,
          uiSurfacesGreen: `${state.uiSurfaceProbes.filter((u) => u.contractStatus === 'PROVEN_GREEN').length}/${state.uiSurfaceProbes.length}`,
          sessionsWithLiveEval: `${state.monitoredSessions.filter((s) => s.realtimeEvalAttached).length}/${state.monitoredSessions.length}`,
          regoConvertiblePct: `${state.regoConsolidationStats.convertiblePercentage}%`,
          activeIncident: state.activeIncident?.incidentId ?? null,
        },
        null,
        2
      )
    );
    return;
  }

  if (cmd === 'eval-rego') {
    const evalAttached = getFlag(args, '--eval-attached') !== 'false';
    const tests = Number(getFlag(args, '--tests') ?? '39');
    const tokens = Number(getFlag(args, '--tokens') ?? '18400');
    const sessionId = getFlag(args, '--session') ?? 'ses-aurelius-io-01';
    const verdict = evaluateBeastRegoPolicy(state.dials, {
      sessionId,
      actorDid: 'did:estate:principal:aurelius-marcus',
      realtimeEvalAttached: evalAttached,
      actionKind: 'CI_OR_PREPUSH_GATE',
      collectedTests: tests,
      epistemicConfidencePct: 98,
      requiresVaultSecret: true,
      bitwardenLeaseValid: true,
      targetBranch: 'lane/cli-rego-check',
      sessionUsedTokens: tokens,
    });
    console.log(JSON.stringify(verdict, null, 2));
    process.exitCode = verdict.allow ? 0 : 2;
    return;
  }

  if (cmd === 'dials') {
    const preset = getFlag(args, '--preset') as BeastPosturePreset | undefined;
    if (preset) {
      updateBeastDynamicDials(state, { applyPreset: preset });
      await persistState(state);
    }
    console.log(JSON.stringify({ dials: state.dials, activeRegoSource: state.activeRegoSource }, null, 2));
    return;
  }

  if (cmd === 'inject-fault') {
    const kind = (getFlag(args, '--kind') ?? 'UNEVALUATED_SESSION') as BeastFaultKind;
    const incident = triggerBeastDisruptiveIncident(state, kind);
    await persistState(state);
    console.log(JSON.stringify(incident, null, 2));
    return;
  }

  if (cmd === 'resolve-incident') {
    const out = resolveBeastIncident(state, 'AUTO_COORDINATE_FIX');
    await persistState(state);
    console.log(
      JSON.stringify(
        {
          resolvedIncidentId: out.resolvedIncidentId,
          synthesizedAntibodyId: out.synthesizedAntibodyId,
          resolutionSummary: out.resolutionSummary,
          allLayersConsistent: state.allLayersConsistent,
        },
        null,
        2
      )
    );
    return;
  }

  if (cmd === 'dreams') {
    const scenario = getFlag(args, '--scenario');
    const dream = runBeastDreamsCycle(state, scenario);
    await persistState(state);
    console.log(JSON.stringify(dream, null, 2));
    return;
  }

  if (cmd === 'brochure') {
    const {
      createInitialBeastSynchronyState,
      generateLivingBrochureMarkdown,
    } = await import('./synchronyCatalog.ts');
    const persona = (getFlag(args, '--persona') ?? 'INSTITUTIONAL_INVESTOR') as
      | 'FOUNDER_SOVEREIGN'
      | 'INSTITUTIONAL_INVESTOR'
      | 'ENTERPRISE_OPERATOR'
      | 'PUBLIC_VISITOR';
    const syncState = createInitialBeastSynchronyState(state);
    console.log(generateLivingBrochureMarkdown(syncState, state, persona));
    return;
  }

  if (cmd === 'heartbeat' || cmd === 'map-surfaces') {
    const { createInitialBeastSynchronyState } = await import('./synchronyCatalog.ts');
    const syncState = createInitialBeastSynchronyState(state);
    console.log(
      JSON.stringify(
        cmd === 'heartbeat'
          ? {
              heartbeatBpm: syncState.heartbeatBpm,
              posture: syncState.heartbeatPosture,
              phaseDriftMs: syncState.founderSystemPhaseDriftMs,
              mathematicallySynchronized: syncState.mathematicallySynchronized,
              horizons: syncState.horizons,
              topHeadlines: syncState.rankedHeadlines.slice(0, 3),
            }
          : syncState.omniSurfaceMap,
        null,
        2
      )
    );
    return;
  }

  console.log(
    'Usage: bin/beast [status | sweep | eval-rego | dials --preset <MAXIMUM_LOCKDOWN|PRODUCTION_AUTONOMOUS|RAPID_RND_SANDBOX> | inject-fault --kind <...> | resolve-incident | dreams | brochure --persona <FOUNDER_SOVEREIGN|INSTITUTIONAL_INVESTOR|ENTERPRISE_OPERATOR|PUBLIC_VISITOR> | heartbeat | map-surfaces]'
  );
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
