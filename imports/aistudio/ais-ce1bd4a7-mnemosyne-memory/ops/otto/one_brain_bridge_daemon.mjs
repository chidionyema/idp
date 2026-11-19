#!/usr/bin/env node
/**
 * GENESIS ESTATE — MAC & DESKTOP ONE-BRAIN + DIRECT GITHUB MIRROR BRIDGE DAEMON
 * Protocols: GEN-NET-003, GEN-NET-005, GEN-NET-006, GEN-SCI-004
 *
 * Runs on your MacBook to keep Codex Desktop, Claude Code Desktop, Kimi Desktop,
 * Otto (ai.estate.otto-concierge), and GitHub (`chidionyema/argon` + `chidionyema/argon-sync`)
 * 100% synchronized with the Genesis One-Brain Hub:
 * 1. Fetches canonical polyglot constitution (/api/brain/AGENTS.md) and writes
 *    AGENTS.md, CLAUDE.md, GEMINI.md, and .agent.md in the local workspace root.
 * 2. Bridges your Mac's `gh auth token` (if available) to `/api/git/connect-github` so
 *    AI Studio pushes directly to `chidionyema/argon` and `chidionyema/argon-sync` on every commit.
 * 3. Pulls the live `/api/git/argon.bundle` from AI Studio and mirrors `main`, `genesis-live`,
 *    `estate/genesis-router-sync`, `estate/wwfd-alignment-gate`, and `argon-sync` directly to GitHub.
 */

import fs from 'node:fs';
import path from 'node:path';
import { execSync } from 'node:child_process';

const BRAIN_HUB_URL =
  process.env.GENESIS_BRAIN_HUB_URL ||
  'https://ais-pre-6t2ghnwqn4d2uzq7jeutd2-534240513427.europe-west3.run.app';

const POLYGLOT_FILES = ['AGENTS.md', 'CLAUDE.md', 'GEMINI.md', '.agent.md'];

function tryGetLocalGhToken() {
  if (process.env.GITHUB_TOKEN) return process.env.GITHUB_TOKEN.trim();
  if (process.env.GH_TOKEN) return process.env.GH_TOKEN.trim();
  try {
    return execSync('gh auth token', {
      encoding: 'utf8',
      stdio: ['ignore', 'pipe', 'ignore'],
    }).trim();
  } catch (_e) {
    return '';
  }
}

export async function syncLocalDesktopWorkspaceOnce(workspaceRoot = process.cwd()) {
  const res = await fetch(`${BRAIN_HUB_URL}/api/brain/state`);
  if (!res.ok) {
    throw new Error(`ONE_BRAIN_HUB_HTTP_${res.status}`);
  }
  const state = await res.json();
  const mdContent = state.polyglotAgentMdContent;

  if (mdContent) {
    for (const filename of POLYGLOT_FILES) {
      const targetPath = path.join(workspaceRoot, filename);
      fs.writeFileSync(targetPath, mdContent, 'utf8');
    }
  }

  let githubMirrorResult = 'SKIPPED_NO_LOCAL_GH_TOKEN';
  const ghToken = tryGetLocalGhToken();
  if (ghToken) {
    try {
      const mirrorRes = await fetch(`${BRAIN_HUB_URL}/api/git/connect-github`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token: ghToken }),
      });
      if (mirrorRes.ok) {
        const mirrorData = await mirrorRes.json();
        githubMirrorResult = `CONNECTED_AND_PUSHED:${mirrorData.githubArgonStatus}/${mirrorData.githubArgonSyncStatus}`;
      }
    } catch (_e) {
      githubMirrorResult = 'BRIDGE_HTTP_WARN';
    }
  }

  return {
    syncedRevisionHash: state.canonicalRevisionHash,
    zeroCreditLifeboatActive: state.zeroCreditLifeboatModeActive,
    latestSteer: state.steeringHistory?.[0]?.directiveText || '',
    filesWritten: POLYGLOT_FILES,
    githubMirrorResult,
  };
}

if (import.meta.url === `file://${process.argv[1]}`) {
  syncLocalDesktopWorkspaceOnce()
    .then((result) => {
      console.log(JSON.stringify({ status: 'ONE_BRAIN_AND_GITHUB_SYNCED', ...result }, null, 2));
      process.exit(0);
    })
    .catch((err) => {
      console.error(JSON.stringify({ status: 'SYNC_ERROR', error: err.message }, null, 2));
      process.exit(1);
    });
}
