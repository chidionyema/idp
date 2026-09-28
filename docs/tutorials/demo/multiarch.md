# Demo: multiarch-gate

`bin/multiarch-gate` proves ruling R24 (every image build names both
architectures) against a real tree. Report mode only — it never edits
anything. Run on this repository:

```
$ python3 bin/multiarch-gate .
ok    multiarch 0 findings across 1 root(s)
```

Three things make a finding: a `docker/build-push-action` workflow step whose
`platforms:` is not `linux/amd64,linux/arm64`; a raw `docker build` or `docker
buildx build` in a workflow, shell script or Makefile that does not go through
`bin/build-image`; and a Dockerfile-shaped file that `bin/dockerfiles` neither
builds nor excludes. `bin/idp-ci` proves the first two against fixtures:

```
$ python3 bin/multiarch-gate tests/fixtures/multiarch/bad
FAIL  multiarch tests/fixtures/multiarch/bad/.github/workflows/images.yml: job build step 0 build-push-action platforms=(unset); R24 needs linux/amd64,linux/arm64
FAIL  multiarch tests/fixtures/multiarch/bad/.github/workflows/images.yml:9: raw `docker build` without both platforms; use bin/build-image (R24)
FAIL  multiarch 2 findings across 1 root(s)
```

and the coverage check by copying this repository, adding a stray Dockerfile
nothing builds, and confirming that alone turns the run red:

```
$ cp -R . /tmp/ma && touch /tmp/ma/mcp/Dockerfile.stray
$ python3 bin/multiarch-gate /tmp/ma
FAIL  multiarch mcp/Dockerfile.stray: Dockerfile-shaped file that bin/dockerfiles neither builds nor excludes (R24)
FAIL  multiarch 1 findings across 1 root(s)
```

A matrix step whose platforms come from `${{ matrix.X }}` is resolved to the
job's matrix values before judging, so a per-architecture matrix that is later
merged into one manifest — a legitimate shape used elsewhere in the estate —
is not a false finding.
