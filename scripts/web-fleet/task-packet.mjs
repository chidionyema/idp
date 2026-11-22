/**
 * Public read-only GitHub -> one canonical MERIDIAN-TASK-V1 packet.
 * The same exact-SHA Git evidence adapter feeds every browser/app source. This
 * tool does not lease a mission, call a model, validate a model claim or write Git.
 */
import { writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { hydrateFromGitHub, EvidenceBlind } from './github-evidence.mjs';

const HELP = `task-packet.mjs --issue N --file PATH [--file PATH] [--instruction ID]
                [--owner LABEL] [--acceptance TEXT] [--task ID] [--out FILE]
Source: live public idp GitHub, exact SHA/blob/mode, canonical MERIDIAN-TASK-V1.
Output: data-only untrusted packet; no credentials, model execution, merge or lease.
Missing or stale evidence is BLIND (exit 3); usage error exits 2.
`;
const MAX_WIRE = 12_288;
const MAX_VALUE = 1_200;

export function parseArgs(args) {
  if (args.length === 1 && (args[0] === '--help' || args[0] === '-h')) return { help: true };
  const out = { paths: [] };
  const pairs = new Map([
    ['--issue', 'issue'], ['--file', 'paths'], ['--instruction', 'instructionId'],
    ['--owner', 'owner'], ['--acceptance', 'acceptance'], ['--task', 'taskId'],
    ['--out', 'outFile'], ['--run', 'runId'],
  ]);
  for (let i = 0; i < args.length; i += 2) {
    const key = args[i], value = args[i + 1], field = pairs.get(key);
    if (!field || typeof value !== 'string' || !value || value.startsWith('--')) {
      throw new EvidenceBlind('INVALID_CLI_ARGUMENTS');
    }
    if (field === 'paths') out.paths.push(value);
    else {
      if (Object.hasOwn(out, field)) throw new EvidenceBlind('DUPLICATE_CLI_FLAG');
      out[field] = value;
    }
  }
  if (!/^[1-9][0-9]{0,12}$/.test(out.issue || '')) {
    throw new EvidenceBlind('MISSING_OR_INVALID_ISSUE');
  }
  out.issue = Number(out.issue);
  if (!Number.isSafeInteger(out.issue)) throw new EvidenceBlind('INVALID_ISSUE_ID');
  if (out.runId !== undefined) {
    if (!/^[1-9][0-9]{0,15}$/.test(out.runId)) throw new EvidenceBlind('INVALID_RUN_ID');
    out.runId = Number(out.runId);
    if (!Number.isSafeInteger(out.runId)) throw new EvidenceBlind('INVALID_RUN_ID');
  }
  if (!out.paths.length || out.paths.length > 2 ||
      out.paths.length !== new Set(out.paths).size) throw new EvidenceBlind('INVALID_SOURCE_PATH_COUNT');
  if (out.acceptance !== undefined && Buffer.byteLength(out.acceptance) > MAX_VALUE) {
    throw new EvidenceBlind('ACCEPTANCE_OVERSIZE');
  }
  out.instructionId ??= `idp-issue-${out.issue}`;
  out.taskId ??= `IDP-${out.issue}-SOURCE`;
  out.owner ??= 'web-fleet-unverified';
  out.acceptance ??= `Draft a data-only MERIDIAN-PATCH-V1 proposal against idp issue #${out.issue}. Never write Git, invent tests, infer a lease or certify your own outcome.`;
  return out;
}

export async function createPacket(opts, deps = {}) {
  if (opts.help) return null;
  const { outFile, ...request } = opts;
  const packet = await hydrateFromGitHub(request, deps);
  if (packet.schema !== 'MERIDIAN-TASK-V1' ||
      packet.requested_result?.authority !== 'DATA_ONLY_UNTRUSTED') {
    throw new EvidenceBlind('NON_CANONICAL_PACKET');
  }
  const encoded = JSON.stringify(packet) + '\n';
  if (Buffer.byteLength(encoded) > MAX_WIRE) throw new EvidenceBlind('WIRE_EXCEEDS_12K');
  if (outFile) await writeFile(outFile, encoded, { flag: 'wx', mode: 0o600 });
  else process.stdout.write(encoded);
  return packet;
}

async function main(argv) {
  try {
    const options = parseArgs(argv);
    if (options.help) { process.stdout.write(HELP); return 0; }
    await createPacket(options);
    return 0;
  } catch (e) {
    const code = /^[A-Z0-9_]+$/.test(e?.code || '') ? e.code : 'SOURCE_EVIDENCE_UNAVAILABLE';
    process.stderr.write(JSON.stringify({ state: 'BLIND', code }) + '\n');
    return code.includes('CLI') || code.includes('ISSUE_ID') || code === 'MISSING_OR_INVALID_ISSUE' ? 2 : 3;
  }
}
if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  main(process.argv.slice(2)).then((status) => { process.exitCode = status; });
}
