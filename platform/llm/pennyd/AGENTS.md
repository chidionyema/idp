# pennyd — repo laws

1. **Gate law**: a rule that has no gate is not a rule here. Every Rego/loader
   law has must-fail/must-pass fixtures; every failure mode in
   `FAILURE_MODES.md` names its test. FMEA and tests move together or not at all.
2. **No stubs**: no `todo!()`, no `unimplemented!()`, no silent `unwrap()` on
   user-controlled paths. Load-time validation is loud and names the file.
3. **Proof protocol** (ADOPTION.md): one cohort, one intervention,
   pre-registered decision rule. If the decision log can't show the effect,
   the effect doesn't exist.
4. **Identity law**: a request for model A never executes as model B unless
   the operator declared that fallback in `providers/*.toml`.
5. **Enterprise defaults**: unknown keys are 401, unknown models are 400 with
   discovery, bodies are capped, budgets are hard ceilings. Loosening any of
   these is an explicit config decision, never implicit.

CI (`make ci`) = fmt + clippy -D warnings + tests + audit. All four must pass.

Failure-pack law (critical services): a PR touching a critical service must
name the affected P0/P1 rows from FAILURE_MODES.md, add/change the exact test
that reproduces each affected row, and record symptom + operator recovery in
the PR body. No row, no merge.
