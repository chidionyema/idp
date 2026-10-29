# Agent handoff: test and ship (no architecture redesign)

1. Unzip this package outside the estate checkout. Verify Python >= 3.10.
2. Run `python -m unittest discover -s tests -v` and preserve the output.
3. Run `python -m atlas.run --repo "$IDP_REPO" --out-dir output --offline` and verify three JSON files exist. Inspect `warnings` in `output/atlas.json` and confirm file paths are correct for the checked-out revision.
4. On the founder's Mac, run without `--offline` and inspect the probes. A `healthy` status means only HTTP 200 liveliness, **not** an authenticated completion.
5. Run `python -m atlas.serve`; open `http://127.0.0.1:8765/viewer.html`; verify component selection, symbol evidence and operational report rendering. Check narrow screen layout.
6. Compare the output graph with source; do not infer unverified execution order or live call edges.
7. Ship as a separately reviewed, read-only tool. Do not alter router deployment, routing policy, GitHub workflow, or production cluster as part of this handoff.

**Ship gate:** tests pass; output generated; viewer inspected; source warnings reviewed; no secrets in JSON; no write or restart operations. Report failures and exact commands. Any additional operational integration is a separate scoped PR.
