# Onboarding: multiarch-gate

## What it is

`bin/multiarch-gate [PATH ...]` (default: this repository) is a report-mode
check for ruling R24: every image build that can reach a registry names both
`linux/amd64` and `linux/arm64`. It scans GitHub workflows for
`docker/build-push-action` steps missing a platform, scans workflows, shell
scripts and Makefiles for a raw `docker build`/`docker buildx build` that
bypasses `bin/build-image`, and checks that every Dockerfile-shaped file in
the tree is accounted for by `bin/dockerfiles`. It prints one line per finding
and never edits anything.

## Why it exists

R24 exists because this estate runs on two different architectures — an
x86_64 Mac and an Ampere (arm64) Oracle worker — and a single-arch image built
by hand fails silently on whichever machine does not match the builder.
`bin/build-image` is the one path that builds both; this gate is what stops a
`docker build` typed directly in a workflow, a script, or a Makefile from
reintroducing a single-arch image, and stops an image escaping the check
entirely by not appearing on `bin/dockerfiles`' list (the exact gap found by
chidionyema-b0 on 2026-08-25).

## When it runs

Inside `bin/idp-ci`, proved against a passing fixture, a failing fixture, and
a live copy of this repository with a stray Dockerfile added — three separate
assertions in one run. It can also be pointed at any other repository to
sweep it for the same three findings.

## Related files

```
bin/multiarch-gate                    the gate
bin/build-image                       the one build path it enforces
bin/dockerfiles                       the coverage list it checks against
tests/fixtures/multiarch/bad          a workflow missing both platforms
tests/fixtures/multiarch/good         the same workflow, fixed
```
