# Demo: matrix-gate

`bin/matrix-gate` grades the estate's one reference decision matrix, `docs/decisions/decision-matrix.yaml` (ADR 0009). The founder asked for it on 2026-08-28 (crew#562): "we need a matrix for decision making — rather than asking these questions it should be auto — for all requirements", then "i like the matrix, enforce it — rigorously, can't be cheated — need evidence — and we need to review weekly". Run on this checkout:

```
$ python3 bin/matrix-gate
PASS  matrix-gate
$ python3 bin/matrix-gate --slugs
["founder-screen-access"]
```

The weekly review (what `.github/workflows/matrix-review.yml` runs every Monday and posts on crew#562) re-reads every evidence URL and checks every receipt is a comment by the repository owner:

```
$ python3 bin/matrix-gate --review --verify-receipts
ok    evidence https://apps.apple.com/app/moonlight-game-streaming/id1000551566
ok    evidence https://artifacthub.io/packages/search?ts_query_web=guacamole
…
      founder-screen-access: proposed three-paths next_review 2026-09-04 reviews 0
ok    receipt weights author chidionyema, 1937 chars
ok    receipt founder-screen-access.tie_receipt author chidionyema, 2456 chars
PASS  matrix-gate
```

What it refuses, each proved by a red case in `tests/test_incident_crew562_decision_matrix.py`: a score that is a bare number instead of `{score, evidence}`; evidence that is a sentence rather than a URL, a repo path or `cmd:`; a weight changed without a new founder-receipted `weights_history` entry (the sha256 no longer matches); a decision that is not the top score and not within `tie_band` of it; a tie decided without the founder's `tie_receipt`; a candidate missing a criterion. The operating-model gate's `matrix_cited` rule then refuses a PR that adds an ADR or a new HelmRelease without a `Matrix: <slug>` line naming a scored entry.
