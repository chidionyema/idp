# Demo: build-image

`bin/build-image` is the one way an estate container image gets built, per
founder ruling R24: every image that can reach a registry names both
`linux/amd64` and `linux/arm64`, in one manifest list. Called with no mode, it
refuses to guess:

```
$ bin/build-image
build-image: choose --push (multi-arch to a registry) or --load (native only, local)
```

`--push` always builds both architectures and pushes one manifest list; a
`--platform` naming anything other than `linux/amd64,linux/arm64` is refused
for the same reason a raw `docker build` is refused elsewhere — a single-arch
push is exactly what R24 exists to stop:

```
$ bin/build-image --push -t ghcr.io/example/demo:test --platform linux/amd64 .
build-image: refused: --platform linux/amd64 is not linux/amd64,linux/arm64 (R24: one tag, two architectures)
```

`--load` builds for the machine you are on only and never pushes, because the
`docker` driver cannot load a manifest list into a local daemon — that is a
`buildx` limitation, not a policy choice. It runs a plain
`docker buildx build --load -t <name>:<tag> <context>` and exists for local
iteration before a real `--push`.

`bin/multiarch-gate` is the other half of R24: it scans workflows and shell
scripts for a raw `docker build`/`docker buildx build` that does not go
through this script, and for a `build-push-action` step missing either
platform. See `docs/demo/multiarch.md`.
