/**
 * FIR-07 provider pilots: compile three provider-specific heavy-work assignments
 * into ONE existing MERIDIAN-TASK-V1 wire contract. This does not call any model,
 * automate consumer login, obtain a worker lease, or grant publication authority.
 * Source provenance and exact-main readback remain github-evidence.mjs's job.
 */
import { writeFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { hydrateFromGitHub } from './github-evidence.mjs';

const ISSUE = 7794;
const ROOT = 'FIR-07';
const STANDARD = 'Output data-only MERIDIAN-PATCH-V1, limited to the exact source files; never assume current production health from a historical diagnosis. If no justified patch exists, report NO_CHANGE with evidence instead of inventing one. No secrets, provider API calls, browser automation, direct Git writes, QUAD lease, or self-certified yield.';

/** The providers are destinations, not authorising identities or cost entitlements. */
export const PROVIDER_PILOTS = Object.freeze({
  zai: Object.freeze({
    id: 'BR-ZAI-01',
    site: 'https://chat.z.ai/',
    owner: 'zai-web-unverified',
    focus: 'Heavy code-generation and adversarial verification of provider routing, including the Coding Plan versus pay-as-you-go failure class.',
    paths: Object.freeze([
      'platform/llm/pennyd/providers/zai.toml',
      'docs/diagnoses/2026-10-10-zai-lane-hits-pay-as-you-go.yaml',
    ]),
  }),
  deepseek: Object.freeze({
    id: 'BR-DSH-01',
    site: 'https://chat.deepseek.com/',
    owner: 'deepseek-web-unverified',
    focus: 'Heavy root-cause analysis and code/test proposal for the DeepSeek credential-mount and cost-control boundary; no paid inference.',
    paths: Object.freeze([
      'platform/llm/pennyd/providers/deepseek.toml',
      'docs/diagnoses/2026-10-10-deepseek-lane-has-no-key.yaml',
    ]),
  }),
  kimi: Object.freeze({
    id: 'BR-KIMI-01',
    site: 'https://www.kimi.com/',
    owner: 'kimi-web-unverified',
    focus: 'Long-context architectural review: identify stale assumptions in the historical Kimi router decision and audit the canonical V1 web-handoff CLI for gaps.',
    paths: Object.freeze([
      'docs/decisions/2026-09-04-the-kimi-lane-is-reached-by-a-router-alias.md',
      'scripts/web-fleet/task-packet.mjs',
    ]),
  }),
});

export function pilotRequest(provider) {
  if (typeof provider !== 'string' || !Object.hasOwn(PROVIDER_PILOTS, provider)) {
    throw new Error('UNKNOWN_PROVIDER_PILOT');
  }
  const p = PROVIDER_PILOTS[provider];
  return {
    issue: ISSUE,
    paths: [...p.paths],
    instructionId: ROOT,
    taskId: `${p.id}-SOURCE-PILOT`,
    owner: p.owner,
    acceptance: `${p.focus} ${STANDARD}`,
    checkpoint: { state: 'UNKNOWN', lease: 'UNOBSERVED' },
  };
}

/** Returns ONLY the canonical packet. No extra provider-specific wire schema. */
export async function prepareProviderPilot(provider, { hydrate = hydrateFromGitHub } = {}) {
  const request = pilotRequest(provider);
  const packet = await hydrate(request);
  const {payload_sha256: signature, ...unsigned} = packet || {};
  const realDigest = createHash('sha256').update(JSON.stringify(unsigned)).digest('hex');
  if (signature !== realDigest ||
      packet?.root_instruction_id !== ROOT ||
      packet?.issue !== ISSUE ||
      packet?.owner !== request.owner ||
      !Array.isArray(packet?.source_files) ||
      packet.source_files.length !== request.paths.length ||
      packet.source_files.some((f, i) => f?.path !== request.paths[i]) ||
      packet?.schema !== 'MERIDIAN-TASK-V1' ||
      packet?.requested_result?.schema !== 'MERIDIAN-PATCH-V1' ||
      packet?.requested_result?.authority !== 'DATA_ONLY_UNTRUSTED' ||
      packet?.checkpoint?.state !== 'UNKNOWN' ||
      !/^[a-f0-9]{64}$/.test(packet?.payload_sha256 || '') ||
      packet?.task_id !== `${PROVIDER_PILOTS[provider].id}-SOURCE-PILOT` ||
      packet?.source_repo !== 'chidionyema/idp' ||
      !/^[a-f0-9]{40}$/.test(packet?.source_sha || '') ||
      Buffer.byteLength(JSON.stringify(packet), 'utf8') > 12_288) {
    throw new Error('NONCANONICAL_OR_UNVERIFIED_TASK');
  }
  return packet;
}

export function parsePilotCLI(argv) {
  if (argv.length === 1 && argv[0] === '--help') return { help: true };
  if (argv.length !== 2 && argv.length !== 4) throw new Error('INVALID_PILOT_CLI');
  if (argv[0] !== '--provider' || !Object.hasOwn(PROVIDER_PILOTS, argv[1])) {
    throw new Error('INVALID_PILOT_PROVIDER');
  }
  if (argv.length === 4 && (argv[2] !== '--out' || !argv[3] || argv[3].startsWith('--'))) {
    throw new Error('INVALID_PILOT_OUTPUT');
  }
  return { provider: argv[1], out: argv.length === 4 ? argv[3] : null };
}

async function main(argv) {
  try {
    const opts = parsePilotCLI(argv);
    if (opts.help) {
      process.stdout.write('provider-pilots.mjs --provider zai|deepseek|kimi [--out NEW_FILE]\n');
      return 0;
    }
    const packet = await prepareProviderPilot(opts.provider);
    const payload = JSON.stringify(packet) + '\n';
    if (opts.out) await writeFile(opts.out, payload, { flag: 'wx', mode: 0o600 });
    else process.stdout.write(payload);
    return 0;
  } catch (error) {
    // No potentially sensitive model response, remote content or auth material in stderr.
    const code = ['UNKNOWN_PROVIDER_PILOT', 'INVALID_PILOT_CLI', 'INVALID_PILOT_PROVIDER', 'INVALID_PILOT_OUTPUT'].includes(error?.message)
      ? error.message : 'SOURCE_EVIDENCE_BLIND';
    process.stderr.write(JSON.stringify({ state: 'BLIND', code }) + '\n');
    return code === 'SOURCE_EVIDENCE_BLIND' ? 3 : 2;
  }
}
if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  main(process.argv.slice(2)).then(status => { process.exitCode = status; });
}
