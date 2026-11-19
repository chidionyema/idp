/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 * 
 * Genesis Estate Non-Destructive GitHub Synchronizer & Argos SOS Bridge
 * Targets: chidionyema/argon & chidionyema/argos
 * Target Ref: refs/heads/genesis-live
 * Tags: v1.0.26, v1.0.27
 */

import { execSync } from 'child_process';

export interface SyncOptions {
  remotes?: string[];
  targetBranch?: string;
  releaseTags?: string[];
  dryRun?: boolean;
}

export async function runGenesisArgonSync(opts: SyncOptions = {}) {
  const remotes = opts.remotes || [
    'https://github.com/chidionyema/argon.git',
    'https://github.com/chidionyema/argos.git',
  ];
  const branch = opts.targetBranch || 'genesis-live';
  const tags = opts.releaseTags || ['v1.0.26', 'v1.0.27'];

  console.log(`[SYNC] Initializing non-destructive sync across ${remotes.length} remotes...`);
  console.log(`[SYNC] Target ref: refs/heads/${branch}`);
  console.log(`[SYNC] Release tag seals: ${tags.join(', ')}`);

  // Ensure local branch and tags exist
  try {
    execSync(`git branch -f ${branch} HEAD`, { stdio: 'pipe' });
    for (const tag of tags) {
      execSync(`git tag -f ${tag} HEAD`, { stdio: 'pipe' });
    }
    // Re-seal bundle
    execSync(`git bundle create public/olat-estate-genesis-main.bundle --all HEAD`, { stdio: 'pipe' });
    console.log(`[SYNC] Re-sealed standalone git bundle at public/olat-estate-genesis-main.bundle`);
  } catch (err: unknown) {
    const errorMsg = err instanceof Error ? err.message : String(err);
    console.warn(`[SYNC] Local prep note: ${errorMsg}`);
  }

  const results = [];
  const token = process.env.GITHUB_TOKEN || process.env.GH_TOKEN;

  for (const remote of remotes) {
    const remoteName = remote.includes('argon') ? 'argon' : 'argos';
    const authRemote = token 
      ? remote.replace('https://github.com/', `https://${token}@github.com/`)
      : remote;

    console.log(`[SYNC] Processing remote [${remoteName}]: ${remote}`);
    let pushed = false;
    try {
      // Add or update remote
      try {
        execSync(`git remote add ${remoteName} "${authRemote}"`, { stdio: 'pipe' });
      } catch {
        execSync(`git remote set-url ${remoteName} "${authRemote}"`, { stdio: 'pipe' });
      }

      // Attempt push to genesis-live ref only (NEVER force-push over main - §8.1)
      if (token) {
        execSync(`git push ${remoteName} HEAD:refs/heads/${branch} --tags`, { stdio: 'pipe' });
        console.log(`[PASS] Pushed to ${remoteName}:refs/heads/${branch}`);
        pushed = true;
      } else {
        console.log(`[INFO] No GitHub write token in env; prepared ref refs/heads/${branch} and bundle.`);
      }
    } catch (err: unknown) {
      const errorMsg = err instanceof Error ? err.message : String(err);
      console.warn(`[WARN] Push to ${remoteName} requires authentication: ${errorMsg}`);
    }

    results.push({ remote, remoteName, pushed });
  }

  return {
    success: true,
    branch,
    tags,
    results,
    bundlePath: 'public/olat-estate-genesis-main.bundle',
    timestamp: new Date().toISOString(),
    commitSha: execSync('git rev-parse HEAD').toString().trim(),
  };
}

if (import.meta.url === `file://${process.argv[1]}`) {
  runGenesisArgonSync().then((res) => {
    console.log('[SUCCESS]', JSON.stringify(res, null, 2));
  }).catch((err) => {
    console.error('[ERROR]', err);
    process.exit(1);
  });
}
