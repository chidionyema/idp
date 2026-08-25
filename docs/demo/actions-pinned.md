# Demo: actions-pinned

`bin/actions-pinned` checks every `uses:` line in `.github/workflows` and fails
the ones that are not pinned to a 40-character commit SHA. It exists because a
tag can be moved by the action's own owner after review passed — the tj-actions
incident in March 2025, where a widely used action was repointed at malicious
code under a tag thousands of workflows already trusted. A SHA cannot be moved.

Run on this checkout:

```
$ bin/actions-pinned
ok    actions-pinned 12 of 12 pinned
```

To see a failure, point it at a workflow with a tag instead of a SHA:

```
$ mkdir -p /tmp/bad-wf/.github/workflows
$ cat > /tmp/bad-wf/.github/workflows/x.yml <<'EOF'
jobs:
  build:
    steps:
      - uses: actions/checkout@v4
EOF
$ bin/actions-pinned /tmp/bad-wf
      actions/checkout@v4
FAIL  actions-pinned 1 of 1 uses: not pinned to a commit SHA
```

The bad ref is printed before the FAIL line so the offending workflow can be
found without re-running the check. An empty `.github/workflows` directory, or
one with no `uses:` lines at all, prints `BLIND` and exits 2 — nothing was
graded, which is a different state from everything passing.

This is one of the fourteen controls on `docs/reference/security-policy.md`
(A.5.21, supply-chain integrity); see `docs/demo/security-policy.md` for it in
that context and `docs/onboarding/security-policy.md` for how to turn the
control off.
