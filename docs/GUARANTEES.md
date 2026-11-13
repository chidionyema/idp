# Guarantees, authority, and one-pass playbooks

Status: formalises what the estate can and cannot guarantee. No claim is stronger than the check that enforces it.

## 1. Model

Let S_t be the local estate state at time t (disk, processes, git refs, DB rows, files).
estate-demo-all evaluates a finite set of predicates P = {P1..P15}.

Detection theorem. For any run, estate-demo-all exits 0 iff every P_i evaluated true; it exits 1 otherwise,
and writes the failing P_i with evidence to DEMO_OF_DEMOS.md. This is a decision procedure over the
predicates actually implemented — not a proof of external liveness.

Corollary (no silent green). A surface not covered by a predicate is reported as absent, not assumed healthy.
bus DNS record is currently FAIL and the harness exits 1.

## 2. What is guaranteed

| ID | Predicate | Check |
|---|---|---|
| G1 | Disk free >= 1500 MB | df |
| G2 | Bus answers /health | HTTP 200 |
| G3 | Bus is read-only gated | 401 without token, 200 with |
| G4 | Preflight has bus/map/log pointers | file contains |
| G5 | AGENTS.md carries the block in idp + argon | marker present |
| G6 | Estate map has >= 8 sections | parsed |
| G7 | Projector suite 19/19 | test:projector |
| G8 | Projector builds | npm run build |
| G9 | Projector bundle + route exist | dist string + 3000 root |
| G10 | ICP integration 5/5 | node --test |
| G11 | pennyd answers /health | HTTP 200 (reports ok=false) |
| G12 | llm/otto named DNS resolves | getaddrinfo |
| G13 | estate-bus DNS resolves | getaddrinfo (currently FAIL) |
| G14 | cloudflared connector running | pgrep |
| G15 | Telegram creds + otto present | env keys + process |

## 3. What is NOT guaranteed

- DNS propagation. Creating a record is not proof of resolution; G13 checks resolution, not the dashboard.
- Telegram delivery. G15 checks credentials and process, not that a message arrived.
- Model behaviour. No predicate can bound a provider's output; the receipt gate rejects, it cannot prevent.
- Wall-clock bounds. Timeouts are per call, not a global duration theorem.
- Correctness of a candidate. A passing suite is evidence, not certification.

Any doc claiming more than this is lying.

## 4. Authority matrix (no promotion by assertion)

| Stamp | Meaning | Required proof | Allowed |
|---|---|---|---|
| U | unverified proposal | none | stage in propose/* or .genesis/outbox/; may not replace a baseline |
| E3 | local trial | HMAC step_runs + paired trial rows (n >= 5) | submit lane/* for CI |
| E1 | certified | 40-char SHA + Ed25519 + Welch t >= 2.571 | Greenlane may land |
| PASS-0 | antibody | signed catechism row | automatic remediation, 0 LLM passes |

bin/estate-yield is a CANDIDATE at U. It does not replace the four scripts by assertion. Promotion requires
the preregistered study in experiment_preregistrations, paired trials, Welch's t and CVaR. That study has
not been run; it is parked, not promoted.

## 5. One-pass playbooks

### DNS / tunnel down
1. dig +short estate-bus.mumchimp.com -> NXDOMAIN means the record, not the tunnel.
2. Create proxied CNAME -> d77a438e-996e-4eac-9c1b-96b3dc07d9f1.cfargotunnel.com.
3. pgrep -fl cloudflared; llm.mumchimp.com/health = 200 proves the connector.
4. If resolution works but HTTP 000: TLS/edge, not app.

### Telegram
1. pgrep -fl otto; lsof -iTCP:8099.
2. Token/chat presence in ~/.config/estate/estate.env (names only).
3. Exactly one poller; never start a second bridge.

### Disk
1. df -m /System/Volumes/Data; floor 1500.
2. Clear tmp packs, then uv cache, browser profiles, snapshots, re-downloadable binaries.
3. Never drop a DB table to free space.

### Projector
1. npm run test:projector (19).
2. npm run build; serve from ~/Documents/code/argon, not the runtime copy.
3. If blank: check the served checkout and console exceptions, not the route.

### Bus
1. curl -s localhost:4300/health; 200 = up, 000 = process.
2. 401 is correct without x-estate-token.
3. Token lives at ~/.estate/state/bus-token (0600), never in docs.

## 6. Protocol for every future session

    read AGENTS.md (preflight block)
      -> curl bus /preflight (with token)
      -> run estate-demo-all
      -> if FAIL: run estate-debug-pack
      -> fix one failing predicate
      -> rerun estate-demo-all

This is the whole loop. No session needs to rediscover the estate; it needs to run the predicates and read
the failure.
