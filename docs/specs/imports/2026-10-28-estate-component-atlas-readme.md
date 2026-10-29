# Estate Component Atlas — runnable handoff

Read-only source atlas and operational evidence viewer for `chidionyema/idp`.
The Atlas deliberately distinguishes source-grounded structure, network-local health observations and **unconfirmed** incident conclusions. It does **not** deploy, restart, heal, write to GitHub or claim that a liveliness probe proves a model request works.

## Agent quick start

Requirements: Python 3.10+; a checkout of `chidionyema/idp`.

```bash
# In the atlas directory:
python -m unittest discover -s tests -v
python -m atlas.run --repo /absolute/path/to/idp --out-dir output
python -m atlas.serve
```

Open **http://127.0.0.1:8765/viewer.html**. The viewer automatically loads `output/atlas.json` and `output/report.json`. You may also load them manually using the two file selectors.

Offline test (no probes or GitHub requests):

```bash
python -m atlas.run --repo /absolute/path/to/idp --out-dir output --offline
```

## Commands

- `python -m atlas.build --repo ... --out atlas.json`: static graph only.
- `python -m atlas.operations --out observations.json`: router health probes and recent GitHub Actions metadata.
- `python -m atlas.report --atlas atlas.json --observations observations.json --out report.json`: evidence-bound report.
- `python -m atlas.run --repo ... --out-dir output`: all three stages.
- `python -m atlas.serve`: loopback-only HTTP viewer, default port 8765.

The operational collector probes `https://llm.mumchimp.com/health/liveliness` and the Mac's `127.0.0.1:4000`, `:4001`, `:4002` from **the machine running it**. On a remote machine the laptop probes do not reflect the founder's Mac. GitHub access to private repositories needs `GITHUB_TOKEN` in the agent's environment; never put tokens in the Atlas JSON or viewer.

## Acceptance checklist

1. Tests pass in a clean Python environment without network access.
2. Offline build produces all three JSON files and the viewer opens them.
3. Source paths and SHA-256 hashes match the selected checkout.
4. Online probes are time-stamped, show errors explicitly and do not mislabel HTTP 200 as a completed inference.
5. GitHub workflow failures remain correlation evidence, not proof of router outage.
6. Any deployment or GitHub integration is **separate** from this read-only package and requires explicit approval.

## Limitations and follow-on work

This is a working static/observational Atlas, **not** a production tracing backend. Component membership is an explicit seed manifest; Python imports are heuristics, not call edges. It does not prove live model availability, capture OTEL traces, inspect Kubernetes deployments, establish root cause or implement Greenlane's full topology. Add authenticated completion probes with secrets kept server-side, actual deployed revision/config hashes, Flux/Kubernetes evidence and trace-ID correlation before treating it as an incident control plane.
