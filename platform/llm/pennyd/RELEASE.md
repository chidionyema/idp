# Release checklist

- [ ] `make ci` green (fmt, clippy -D warnings, tests, audit)
- [ ] FMEA reviewed: every row has a passing test or an explicit accepted bound
- [ ] Version bump in workspace Cargo.tomls; CHANGELOG entry
- [ ] `cargo build --release`; smoke: boot → /health ok → one cached request
- [ ] Image built, `cosign sign`, SBOM attached (`make sbom`)
- [ ] Deploy gate: running git_sha == release tag (no stale binaries)
- [ ] Decision-log verify clean on the canary host before fleet rollout
