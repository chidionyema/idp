# meridian-core-engines

Five crates: `meridian-ledger` (escrow ledger, signed `estate.lane-fitness.v1` leases, class-strict
lane selection), `meridian-battalion` (lane qualification, `--fitness-dir` export), `meridian-legion`
(same-class failover that releases escrow on a fault), `meridian-greenlane` (proxy-green and
zero-delta refusal, 3/3 blackbox settlement, auto-recovery lease), `meridian-cli`
(`meridian --optimus`, `meridian presubmit`).

```
cd platform/meridian-core-engines
cargo test --workspace --locked
cargo build --release --locked -p meridian-cli
./target/release/meridian --optimus     # optimus.estate.four_engines_interconnected=1
```

CI: `.github/workflows/meridian-core-engines.yml` (path-scoped).

## What the tests prove

35 Rust tests across the five crates. Each guard was proved by mutation: the guard was removed or
weakened in a scratch copy and the suite had to go red (16 of 16 mutations killed: duplicate
reservation id, cross-class mission, stale epoch, 100x escrow ceiling, untrusted signer, expired
lease, class-blind selection, wrong zone, SHA mismatch, 3/3 relaxed to 1 round, zero-delta contract,
epoch not bumped, userinfo host trick, githubusercontent subdomains, escrow not released on failover,
SEED escalation dropped).

Two defects the tests exposed were fixed before landing: a reused `reservation_id` overwrote a live
or committed escrow, and `is_proxy_green_url` accepted `gist.github.com` and other subdomain,
userinfo, trailing-dot and loopback shapes.

## Limits

* `--optimus` drives the engines with in-process probes. It proves wiring, not a production router.
* The workspace is standalone (its own `Cargo.lock`, no root workspace) so it does not touch the
  `crates/**` and `Cargo.toml` paths of the Rust gate lane (#8682). `meridian-greenlane` and
  `mitp-core`/`meridian-gate` both model proxy-green refusal, billing class and revocation epochs;
  merging them into one layer is a decision for the owners of both (AGENTS.md section 6).
* `meridian-ledger` is a second implementation beside `platform/router-edge/src/ledger-do.ts` (USD
  floats, no fencing). The router edge is not changed here.
