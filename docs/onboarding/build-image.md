# Onboarding: build-image

## What it is

`bin/build-image` is the single entry point for building an estate container
image. `--push -t ghcr.io/<owner>/<name>:<tag> <context>` builds
`linux/amd64` and `linux/arm64` and pushes one manifest list. `--load -t
<name>:<tag> <context>` builds for the machine you are on only, and never
pushes — the local `docker` driver cannot load a manifest list, so this is the
only path for a local build.

## Why it exists

Founder ruling R24: every image that can reach a registry names both
architectures under one tag, because the Mac in this estate is x86_64 and
Oracle's OKE worker is Ampere (arm64), and nobody should have to configure
which one they get. Before this script, a `docker build` or `docker buildx
build` typed by hand could push a single-arch image that silently failed on
whichever machine did not match the builder. `--platform` is refused unless it
names both architectures, which closes that door at the one place a build can
happen rather than relying on every caller to remember the flag.

## When it runs

By hand for a local `--load` build, and from
`.github/workflows/build-multiarch.yml` for every pull request and for the
`--push` that runs on `main`. `bin/dockerfiles` supplies the workflow with the
list of Dockerfiles to build; `bin/multiarch-gate` checks that nothing in the
repository builds an image by any other route.

## Related files

```
bin/build-image                       the one build path (R24)
bin/dockerfiles                       lists what to build
bin/multiarch-gate                    refuses any other build path
.github/workflows/build-multiarch.yml CI: discovers, builds, pushes
docs/how-to/build-an-image.md         the how-to for this whole flow
docs/demo/build-image.md              a working run of each mode
```
