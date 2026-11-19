import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';

export interface B1ArtifactEntry {
  filename: string;
  relativePath: string;
  sha256: string;
  byteSize: number;
}

export interface B1SourceManifest {
  schemaVersion: string;
  aiStudioAppletId: string;
  exportTimestampIso: string;
  gitHeadCommitSha: string;
  gitTag: string;
  targetMirrorBranch: string;
  canonicalProtectedBranch: string;
  preserveLegacyOct31SnapshotHistory: boolean;
  containerPreflightFacts: Record<string, unknown>;
  measuredVerificationGates: Record<string, unknown>;
  headlessGithubMirrorSync: Record<string, unknown>;
  artifacts: B1ArtifactEntry[];
  merkleRootOverAllArtifacts: string;
  signerIdentity: string;
  keyId: string;
  ed25519PublicKeyPem: string;
  ed25519SignatureHex: string;
  signatureVerifiedOutOfProcess: boolean;
}

function sha256Buffer(buf: Buffer | string): string {
  return crypto.createHash('sha256').update(buf).digest('hex');
}

export function verifyRelease(rootDir: string = process.cwd()): {
  verified: boolean;
  errors: string[];
  manifestCommit: string;
  manifestTag: string;
  artifactsVerifiedCount: number;
} {
  const errors: string[] = [];
  const manifestPath = path.join(rootDir, 'SOURCE_MANIFEST.json');

  if (!fs.existsSync(manifestPath)) {
    return {
      verified: false,
      errors: ['SOURCE_MANIFEST.json not found on disk'],
      manifestCommit: '',
      manifestTag: '',
      artifactsVerifiedCount: 0,
    };
  }

  const manifestRaw = fs.readFileSync(manifestPath, 'utf8');
  let manifest: B1SourceManifest;
  try {
    manifest = JSON.parse(manifestRaw) as B1SourceManifest;
  } catch (err) {
    return {
      verified: false,
      errors: [`SOURCE_MANIFEST.json is not valid JSON: ${String(err)}`],
      manifestCommit: '',
      manifestTag: '',
      artifactsVerifiedCount: 0,
    };
  }

  // 1. Verify AGENTS.md constitutional constraint (<= 120 lines)
  const agentsMdPath = path.join(rootDir, 'AGENTS.md');
  if (fs.existsSync(agentsMdPath)) {
    const agentsMdContent = fs.readFileSync(agentsMdPath, 'utf8');
    const lines = agentsMdContent.split('\n').length;
    if (lines > 120) {
      errors.push(`AGENTS.md line count (${lines}) exceeds 120-line constitutional limit`);
    }
  } else {
    errors.push('AGENTS.md not found on disk');
  }

  // 2. Read-only verification of artifacts
  let verifiedCount = 0;
  const artifactHashes: string[] = [];

  for (const artifact of manifest.artifacts) {
    const fullPath = path.join(rootDir, artifact.relativePath);
    if (!fs.existsSync(fullPath)) {
      errors.push(`Artifact missing on disk: ${artifact.relativePath}`);
      continue;
    }
    const content = fs.readFileSync(fullPath);
    const actualSha = sha256Buffer(content);
    if (actualSha !== artifact.sha256) {
      errors.push(
        `Artifact hash mismatch for ${artifact.relativePath}: expected ${artifact.sha256}, got ${actualSha}`
      );
    } else {
      verifiedCount++;
    }
    artifactHashes.push(actualSha);
  }

  // 3. Merkle root verification over artifact entries
  const computedMerkle = `merkle_b1:${sha256Buffer(
    manifest.artifacts.map((a) => `${a.relativePath}:${a.sha256}:${a.byteSize}`).join('|')
  )}`;
  if (computedMerkle !== manifest.merkleRootOverAllArtifacts) {
    errors.push(
      `Merkle root mismatch: expected ${manifest.merkleRootOverAllArtifacts}, computed ${computedMerkle}`
    );
  }

  // 4. Ed25519 signature verification (read-only, out-of-process)
  try {
    const {
      ed25519SignatureHex,
      signatureVerifiedOutOfProcess: _,
      ...unsignedPayload
    } = manifest;
    const canonicalBytes = Buffer.from(JSON.stringify(unsignedPayload), 'utf8');
    const sigBuf = Buffer.from(ed25519SignatureHex, 'hex');
    const pubKey = crypto.createPublicKey(manifest.ed25519PublicKeyPem);

    const sigValid = crypto.verify(null, canonicalBytes, pubKey, sigBuf);
    if (!sigValid) {
      errors.push('Ed25519 signature verification failed over SOURCE_MANIFEST.json payload');
    }
  } catch (err) {
    errors.push(`Ed25519 signature check error: ${String(err)}`);
  }

  // 5. Verify STATE_BEACON.json
  const beaconPath = path.join(rootDir, 'STATE_BEACON.json');
  if (fs.existsSync(beaconPath)) {
    try {
      const beaconRaw = fs.readFileSync(beaconPath, 'utf8');
      JSON.parse(beaconRaw);
    } catch {
      errors.push('STATE_BEACON.json is not valid JSON');
    }
  } else {
    errors.push('STATE_BEACON.json missing on disk');
  }

  return {
    verified: errors.length === 0,
    errors,
    manifestCommit: manifest.gitHeadCommitSha,
    manifestTag: manifest.gitTag,
    artifactsVerifiedCount: verifiedCount,
  };
}

if (
  typeof process !== 'undefined' &&
  process.argv[1] &&
  process.argv[1].endsWith('verify_release.ts')
) {
  const result = verifyRelease(process.cwd());
  if (result.verified) {
    console.log(
      JSON.stringify(
        {
          status: 'RELEASE_VERIFICATION_PASSED',
          commit: result.manifestCommit,
          tag: result.manifestTag,
          artifactsVerified: result.artifactsVerifiedCount,
          nonMutating: true,
        },
        null,
        2
      )
    );
    process.exit(0);
  } else {
    console.error('RELEASE_VERIFICATION_FAILED:', result.errors);
    process.exit(1);
  }
}
