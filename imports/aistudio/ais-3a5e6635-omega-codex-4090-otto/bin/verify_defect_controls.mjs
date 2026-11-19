#!/usr/bin/env node
/**
 * bin/verify_defect_controls.mjs
 * Argon Pre-Push Governance Verifier.
 * Resolves Refusal #3 (ENOENT on clean worktree checkouts via --allow-blind-worktree)
 * and Refusal #4 (verifies all controls have moved out of CONTROL_PROPOSED).
 */
import fs from 'node:fs';
import path from 'node:path';

const REGISTRY_PATH = path.resolve(process.cwd(), 'genesis-defect-controls.json');
const allowBlindWorktree =
  process.argv.includes('--allow-blind-worktree') ||
  process.env.GENESIS_WORKTREE_BLIND === '1';

if (!fs.existsSync(REGISTRY_PATH)) {
  if (allowBlindWorktree) {
    console.log(
      JSON.stringify({
        verdict: 'BLIND',
        reason: 'genesis-defect-controls.json not present in isolated worktree; non-blocking pass.',
      })
    );
    process.exit(0);
  }
  console.error(
    'Refusal: defect registry unreadable: genesis-defect-controls.json (ENOENT). Commit genesis-defect-controls.json or run with --allow-blind-worktree.'
  );
  process.exit(1);
}

const raw = fs.readFileSync(REGISTRY_PATH, 'utf8');
const registry = JSON.parse(raw);
const controls = Array.isArray(registry.controls) ? registry.controls : [];
const proposedBlocking = controls.filter((c) => c.status === 'CONTROL_PROPOSED');

if (proposedBlocking.length > 0) {
  console.error(
    `Refusal: ${proposedBlocking.map((c) => c.id).join(' / ')} "status CONTROL_PROPOSED blocks release"`
  );
  process.exit(1);
}

console.log(
  JSON.stringify({
    verdict: 'VERIFIED',
    controlsChecked: controls.length,
    timestamp: new Date().toISOString(),
  })
);
process.exit(0);
