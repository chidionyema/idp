# Host provisioning drift — a metric layer for declared-vs-present

**Status:** open
**Opened:** 2026-09-23
**Laws:** LAW 0 (one of each layer — extend the metric layer, do not add one),
         LAW 38 (a fence a correct machine cannot satisfy is an outage),
         THE EMPIRICAL PROOF RULE
**Source:** hand-installed audit, 2026-09-23 (this ticket's own Evidence section)
**Depends on:** `bin/idp-install-deps`, `bin/estate-drift-reconciler`, `platform/telemetry/`
**Module:** `platform/`, `bin/`

---

## The failure this removes

On 2026-09-23 **eight** items were found hand-installed on the founder's Mac. Three of them are
load-bearing for gates that currently pass. Each one is the identical defect: **it works on this
machine and nowhere else**, and nobody knows until it breaks something.

The day's cost, in order:

1. **Voice was silent.** `kokoro-onnx` was not installed for the server interpreter and the Kokoro
   models were absent. A person spoke and got nothing. Found by hand, hours in.
2. **"Cannot reach the router."** Python had **no CA certificates**, so every outbound HTTPS call
   failed `CERTIFICATE_VERIFY_FAILED`. `curl` worked the whole time, which is why it read as a
   network fault rather than a host fault.
3. **`ruff` "not installed."** Reported by several agents, then found installed for one interpreter
   and not another. The gate's own checker was undeclared in `bin/idp-install-deps`.
4. **The executor's `timeout`.** The daemon invokes `/usr/local/bin/timeout`; every command
   capability failed until it existed.

None of these are code defects. All four are **provisioning drift**, and the platform has no way
to see any of them.

## Why the existing layers do not cover it

| Layer | Measures | Does it see host tools? |
|---|---|---|
| `platform/observability` (SigNoz, Langfuse) | cluster services | no |
| `platform/telemetry/` | agent spans and transcripts | no |
| `platform/estate-state/` | declared estate state | no |
| `bin/estate-drift-reconciler` | **repo** drift — stale PRs, unmerged branches | no |
| `bin/idp-install-deps` | installs the declared tool set | **only if it is run** |

The last row is the gap: the installer KNOWS the declared set (`KYVERNO_VER=1.19.0`, `HELM_VER`,
`CONFTEST_VER`, `FLUX_VER`, `KUSTOMIZE_VER`, `KUBECONFORM_VER` → `~/.cache/estate-tools/`), and
nothing ever compares what is installed to that list.

## Evidence (measured 2026-09-23, this host)

| # | Item | Path | Installed by | Load-bearing? |
|---|---|---|---|---|
| 1 | Kokoro models (468MB) | `~/.cache/sovereign-voice/` | hand `curl` | yes — voice |
| 2 | `kokoro-onnx` 0.6.1 | Python 3.12 site-packages | hand `pip` | yes — voice |
| 3 | `jsonschema` 4.26.0 | Python 3.12 site-packages | hand `pip` | yes — `voice_media.py` runtime |
| 4 | `ruff` 0.15.18 | `~/Library/Python/3.9` | hand `pip --user` | yes — the gate's checker |
| 5 | `timeout` | `/usr/local/bin/` (root) | hand, 2026-09-23 | yes — the executor |
| 6 | `helm` | `~/.rd/bin/` | Rancher Desktop | shadows the pinned copy |
| 7 | `conftest` | `~/.local/bin/` | hand | shadows the pinned copy |
| 8 | `kokoro-v1.0.int8.onnx` | `~/.cache/sovereign-voice/` | hand `curl` | no — wrong variant, dead weight |

Declared tools at their declared path: 6/6 present, **2 shadowed on PATH** — so the gate may test
one version while the author runs another. That is silent divergence, and it is exactly what a
metric makes visible.

## The metric

One number, and it should be on a dashboard, not in an agent's transcript:

```
estate_host_drift_undeclared_total
```

— the count of present-on-host items that no declared source names. Plus:

- `estate_host_drift_missing_total` — declared, not present (the voice case)
- `estate_host_drift_shadowed_total` — present at two paths, PATH resolving to the undeclared one
  (the `helm`/`conftest` case)

## The work

1. **Declare.** The host tool set becomes a file, not a script's local variables: what must exist,
   at which version, at which path, for which interpreter. `bin/idp-install-deps` reads it, so
   there is one list rather than a script and a document that drift apart.
2. **Measure.** A `bin/idp-host-drift` that compares declared to present and emits the three
   counters. Follows `bin/estate-drift-reconciler`'s shape: deterministic, model-free, **reports
   only, never installs or deletes** (the suggest-only boundary).
3. **Surface.** Publish the counters to the existing metric layer (`platform/telemetry/` →
   the collector that already runs). No new store, no new endpoint.
4. **Gate.** `--check` exits non-zero on drift, for a preflight — but as a **WARN** on a host that
   cannot yet satisfy the declaration, never a refusal, until the declaration and the bootstrap
   agree (LAW 38: a fence a correct machine cannot satisfy is an outage).

## Acceptance

- A fresh clone on a fresh Mac reaches **zero declared-vs-present drift** by running the estate's
  own bootstrap, with no hand `pip install`, `curl`, or `brew` in the path.
- The three counters are readable from the existing metric layer, and a drift introduced by hand
  turns the counter within one collection interval.
- The gate that reports drift **fails** when drift is present (it can fail — LAW 38's other half).

## Non-goals

- Not a package manager. It measures; `bin/idp-install-deps` installs.
- Not a second observability stack. It publishes into the one that exists.
- Not a refusal. Until the bootstrap satisfies the declaration, this is a visible number and a
  warn, because a fence nobody can satisfy is how the estate learned to type overrides.
