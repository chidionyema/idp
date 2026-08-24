# Build an image

Ruling R24 (2026-08-25): every estate image carries `linux/amd64` and `linux/arm64` under one
tag. The Mac (x86_64) pulls amd64; OKE (Ampere) pulls arm64; nobody configures anything.

- **To a registry:** `bin/build-image --push -t ghcr.io/<owner>/<name>:<tag> <context>`. It builds
  both architectures and pushes one manifest list. A `--platform` naming anything else is refused.
- **Locally:** `bin/build-image --load -t <name>:<tag> <context>`. Native architecture only, never
  pushed. Docker's local driver cannot load a manifest list, so this is the one honest local path.
- **In CI:** `.github/workflows/build-multiarch.yml` finds every `Dockerfile` here and builds both
  architectures on every pull request; on `main` it pushes to GHCR.
- **The gate:** `bin/multiarch-gate [path]` refuses a `build-push-action` step without both
  platforms and any raw `docker build`. `bin/idp-ci` runs it against fixtures both ways and
  against this repository. Point it at another repository to sweep it.
