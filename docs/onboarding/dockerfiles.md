# Onboarding: dockerfiles

## What it is

`bin/dockerfiles` finds every `Dockerfile` and `<name>.Dockerfile` in the
repository and prints one row per image: name, Dockerfile path, build context.
`--json` prints the same as a JSON array. It is a plain finder, not a builder —
it does not read or validate the Dockerfile contents.

## Why it exists

Founder ruling R24 says every estate image is built through `bin/build-image`
with both architectures. That rule can only be enforced if there is one
canonical list of "every image this repository builds" to check builders
against. `bin/multiarch-gate` walks the repository for anything Dockerfile-
shaped and fails if it is not on this list or explicitly excluded — an image
found by chidionyema-b0 on 2026-08-25 that had escaped the build workflow by
its file name, before this coverage check existed.

## When it runs

`.github/workflows/build-multiarch.yml` calls `bin/dockerfiles --json` to
build its build matrix on every push and pull request.
`bin/multiarch-gate` calls the plain (non-JSON) form to check coverage every
time it runs, including inside `bin/idp-ci`.

## Related files

```
bin/dockerfiles                       this list
bin/multiarch-gate                    fails on anything not listed here
bin/build-image                       the one way a listed image gets built
.github/workflows/build-multiarch.yml consumes the JSON form to build a matrix
```
