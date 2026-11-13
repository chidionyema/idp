# Release and delivery model

Status: signed, versioned artifact; clean-HOME install verified; public download verified.
Not yet on GitHub Releases or a package registry.

## 1. Versioning

Calendar version: YYYY.MM.DD.N. Current: 2026.11.12.2.
Channels:

| Channel | Source | Guarantee |
|---|---|---|
| dev | working tree | none; may be broken |
| lane | signed tar from a lane | tests pass, signature verified |
| stable | installed from verified tar | clean-HOME install passed, rollback tested |

## 2. Artifact

estate-2026.11.12.2.tar.gz — 26 files, 40 KB.

Contents:

- bin/: session, protocol, escalate, founder-gate, bus, proof, commit-gate,
  capabilities, pack, harness, standard, policy
- cage/: cage.py, cage_broker.py, cage_tg.py
- docs/: NEXT_SESSION, SURFACES, CONTROL_PLANE, PROTOCOL, RECURSIVE_FACTORY,
  FOUNDER_GATE, SECURITY_MAP, ARCHITECTURE, ENROLLMENT, BUILD_PLAN
- MANIFEST.json: every file with sha256 and size
- SHA256SUMS + SHA256SUMS.sig (Ed25519, detached)
- founder.pub (verification key)
- verify.py (dependency-free Ed25519 verifier)
- install.sh (verifies signature + checksums, then copies)

## 3. Signing and verification

- SHA256SUMS is signed with the founder Ed25519 key.
- verify.py implements RFC 8032 verification with the standard library only; it does not depend on
  cryptography or a user site-packages directory.
- install.sh runs verify.py, then shasum -c, then copies.

Verified output:

    SIGNATURE OK
    docs/SURFACES.md: OK
    installed estate 2026.11.12.2 to /private/tmp/estate-home/.estate
    installed_bins=12

## 4. Delivery

    # build
    estate-release 2026.11.12.3

    # local download
    curl -O http://127.0.0.1:4300/release

    # founder surface (one URL)
    https://<surface>/release

    # verify
    shasum -a 256 estate-2026.11.12.3.tar.gz
    tar -xzf estate-2026.11.12.3.tar.gz
    cd estate-2026.11.12.3 && ./install.sh

Artifacts live at ~/.estate/releases/; LATEST points at the current tar.

## 5. Release process

1. Tests green: projector 19/19, cage 11/11, telegram 5/5, protocol check.
2. Build: estate-release <version>.
3. Verify: extract to a clean directory, run install.sh with a temp HOME.
4. Confirm install count and signature.
5. Publish: copy tar to the download surface; update LATEST.
6. Record: write the version and sha256 into the next-session pack.
7. Rollback: install the previous version's tar; LATEST points back.

## 6. What is missing for commercial delivery

- No CI builder; the release is built on this laptop.
- No GitHub Release or package registry; distribution is the local bus and the tunnel.
- The founder URL is an ephemeral quick tunnel; a durable download host needs DNS.
- No automated rollback test in CI.
- No SBOM beyond MANIFEST.json.

These are named so the next release does not pretend to be more than it is.
