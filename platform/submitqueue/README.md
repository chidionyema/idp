# Greenlane Ferrari — upstream SubmitQueue integration

Owner: IDP #7738 · source branch: lane/greenlane-ferrari-uber-adoption-20261109

**Source, not a rewrite:** [Uber SubmitQueue](https://github.com/uber/submitqueue), Apache-2.0, full pinned revision `694373f380bb405d562dd359f27832d6bdb120f0`. `bootstrap.sh git` starts the actual upstream Gateway + Orchestrator + Runway + databases with real local-git landing. Its fake-build CI mode does **not** prove production eligibility. The exact SHA is a supply-chain boundary. No vendored proprietary files.

## Existing Ferrari production slice

`greenlane/ferrari.py`, `greenlane/engine.py`, and `greenlane/github.py` run the **existing trusted-base DoF checker on each exactly-rebased candidate before allocating a full CI build**. A proven negative is RED with a fingerprint; UNKNOWN passes to full CI, not to main. If main changes, the lane is automatically reconsidered without re-push. The cost-gate cannot assert a successful test or bypass required checks. Adversarial tests: `tests/test_submitqueue_preflight.py`; runner: `submitqueue-acceptance.yml`.

## Why upstream does not replace live IDP simply by enabling a config

Upstream currently models **GitHub pull requests** (`github://github.com/<owner>/<repo>/pull/<number>/<40-byte-head>`), but IDP's source contract accepts `lane/*` branches directly. Upstream's GitHub Runway **pushes to main** under its token and may leave pull requests open; IDP's active protected ruleset requires nine named check runs, including Greenlane. Upstream's GitHubActions build runner **polls** for workflow completion; the founder has forbidden polling.

Therefore the only truthful adoption path is to run upstream's existing orchestrator with an IDP-specific lane provider, GitHub-event build completion adapter, and a protected-main *certified* landing adapter. **Do not configure upstream's direct GitHub merger as production**, give it a bypass token, or infer CI proof from `fake`/local `git` mode. The source pin is ready; the final adapter and protected-main readback are not yet shipped.

## Immediate acceptance

`python3 -m pytest -q tests/test_submitqueue_preflight.py` must pass. The runtime test `platform/submitqueue/bootstrap.sh git` is a full upstream service start, requiring Docker/Bazel and host network. Real cutover additionally requires:
- replicated real queue state, idempotent receipts and durable event replay across failure/restart;
- zero polling on native events, no timer-driven work; deadline-triggered fault reaction;
- lossless lane-branch admission and guarded SHA-exact CI materialization of both `sq_base_uris` and `sq_head_uris`;
- only the currently authorised Greenlane promoter can update protected main; no second lander;
- Jev risk/impact decisions advisory only, missing signals => safe deterministic fallback;
- separate production deployment/rollback proof and Founder Surface transparency.

Operational status remains **SOURCE_CANDIDATE**, not delivered production, until those independent runtime receipts exist.
