# NEXT SESSION PACK — read this first

This is the seamless-resume document. If anything here disagrees with the machine, the machine wins;
fix this file in the same lane.

## 1. One command to resume

    estate-session && estate-pack verify && estate-protocol check

If all three say OK, the estate is coherent. Then verify surfaces in section 3.

## 2. Live state (as of 2026-11-12)

| Surface | URL | Notes |
|---|---|---|
| Founder surface | https://cal-heater-anybody-routes.trycloudflare.com | quick tunnel; ephemeral |
| Projector | same URL /#projector | golden replay, not live SSE |
| Yield board | same URL /yield | proxies to bus 4300 |
| Escalations | same URL /escalations | ESCALATE/1 only |
| Bus | http://127.0.0.1:4300 | /health open; /packs token |
| Founder gate | http://127.0.0.1:4320 | prose 422, violations logged |
| Brain/Optimus | http://127.0.0.1:4319 | router metrics only |
| Router | http://127.0.0.1:4200 | pennyd; health ok=false |
| Control plane view | http://127.0.0.1:4090 | 302 to 3000 |
| ICP cockpit | http://127.0.0.1:4101 | packets/grants |

Token: ~/.estate/state/bus-token (0600). Never print it.

## 3. Start order if everything is down

    # 1 bus
    nohup ~/.estate/bin/estate-bus > /tmp/estate-bus.log 2>&1 &

    # 2 founder gate
    FOUNDER_GATE_PORT=4320 nohup ~/.estate/bin/estate-founder-gate > /tmp/founder-gate.log 2>&1 &

    # 3 founder surface
    cd ~/Documents/code/argon
    nohup npm run dev -- --port 3000 --host 0.0.0.0 > /tmp/argon-dev.log 2>&1 &

    # 4 tunnel
    printf 'url: http://127.0.0.1:3000\n' > /tmp/cf-founder.yml
    nohup ~/.estate/bin/cloudflared tunnel --config /tmp/cf-founder.yml \
      --url http://127.0.0.1:3000 --protocol http2 --edge-ip-version 4 --no-autoupdate \
      > /tmp/cf-founder.log 2>&1 &
    # parse URL from log, write it:
    grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' /tmp/cf-founder.log | tail -1 > ~/.estate/state/founder-surface-url

## 4. Verify (copy-paste)

    curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:4300/health
    curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:4320/health
    curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:3000/
    URL=$(cat ~/.estate/state/founder-surface-url)
    HOST=$(echo "$URL" | sed 's|https://||'); IP=$(dig @1.1.1.1 +short "$HOST" | head -1)
    curl -s --resolve "$HOST:443:$IP" -o /dev/null -w '%{http_code}\n' "$URL/yield"

## 5. Canonical files

| Purpose | Path |
|---|---|
| Boot law | AGENTS.md (line 1, both repos) |
| Session | ~/.estate/bin/estate-session |
| Packs | ~/.estate/packs/registry.json |
| Yield protocol | ~/.estate/protocol/PROTOCOL.md |
| Recursive factory | ~/.estate/protocol/RECURSIVE_FACTORY.md |
| Founder gate | ~/.estate/founder-gate/PROTOCOL.md |
| Control plane | ~/Documents/code/idp/docs/CONTROL_PLANE.md |
| Cage | ~/.estate/cage/ARCHITECTURE.md |
| Cage enrollment | ~/.estate/cage/ENROLLMENT.md |
| Security map | ~/.estate/cage/SECURITY_MAP.md |
| Build plan | ~/.estate/cage/BUILD_PLAN.md |
| Estate map | ~/Documents/code/idp/docs/ESTATE_MAP.md |
| Proof gate | ~/.estate/bin/estate-proof |
| Debug pack tool | ~/.estate/bin/estate-debug-pack |

## 6. Failure tree

### Public URL 403
Vite rejected the Host header. Check vite.config.ts server.allowedHosts contains '.trycloudflare.com'.
Restart Vite after editing.

### Public URL 000
Tunnel down or DNS unresolved. Check pgrep cloudflared; tail /tmp/cf-founder.log.
Resolve with: dig @1.1.1.1 +short <host>. If no answer, the quick tunnel is dead; restart it.

### Bus 000
estate-bus is not running. Start it; check /tmp/estate-bus.log for a Python traceback.

### Commit gate fails
Order matters: session handshake, then YIELD/1 report, then proof.
Run estate-session, estate-protocol run ..., estate-proof, then commit.

### Disk below 1500
Proof and YIELD both fail closed. Reclaim first:
rm -rf /tmp/cage-* /tmp/chrome-*; rm -rf ~/.cache/codex-runtimes; df -m /System/Volumes/Data.

### Cage EPERM
sandbox-exec denies by default. Required entitlements already in profile: process*, process-info*,
file-read*, file-write* grants, /dev/null, /private/var/folders, /var/folders, network-bind.
Do not add broad network*; it is denied deliberately.

### idp suite in cage fails
conftest os.nice is tolerated now. Remaining failures are test-repo git setup: global core.hooksPath
is inherited and reads ~/.estate (denied). The helper isolates commit hooks; if new tests appear,
set core.hooksPath= locally in the test repo.

### Optimus does not show yield
Known gap. server.ts ingests router receipts only. A yield adapter is not built. The metric is in
~/.estate/optimus/metrics.jsonl but /api/brain/optimus will not show it.

## 7. Known gaps (do not rediscover)

1. Optimus yield ingest not wired.
2. Named-tunnel DNS for estate-bus not created; quick URL is ephemeral.
3. Push to main blocked: 9 defect dispositions + expired GEN-GATE-20261105-REVIEW-CONTROL.
4. 32 stashes in idp unowned; see OUTSTANDING_AUDIT.md.
5. Remote policy control plane specified, not deployed; policy.key still local.
6. Cage key local and readable by the user; separate estate-agent UID not created.
7. Founder gate and bus are not launchd-managed; they die on reboot.
8. Projector is golden replay, not live SSE.
9. caged idp suite is 3/5; two test-env errors remain.

## 8. Work queue, in order

1. Wire Optimus yield adapter (server.ts) and prove /api/brain/optimus shows estate-yield.
2. launchd plists for estate-bus and estate-founder-gate (KeepAlive).
3. Durable DNS: estate-bus + founder hostnames (needs Cloudflare auth).
4. Move policy.key off-machine; deploy Worker /policy + /grant.
5. estate-agent UID + Keychain secrets.
6. Triage 32 idp stashes into packs or close.
7. Durable tunnel for founder surface.

## 9. Security posture

- All founder messages: YIELD/1 or ESCALATE/1 only.
- Prose: 422 + violation logged; log failure returns 500, never silent.
- Cage: Ed25519 token, single-use jti, epoch revoke, sandbox exec.
- Policy: pinned public key, signed off-machine; no local signing.
- Residual: root on this laptop can bypass; separate UID/VM is the real closure.

## 10. Ten-minute onboarding for a new agent

1. Read AGENTS.md line 1.
2. Run estate-session; if it fails, the pack registry is stale: estate-pack index.
3. Read this file (NEXT_SESSION.md).
4. Run estate-protocol check; if missing, run estate-protocol demo to seed.
5. Curl 4300/health, 4320/health, 3000/.
6. Pick one item from section 8, emit a YIELD/1 record, and only then commit.
