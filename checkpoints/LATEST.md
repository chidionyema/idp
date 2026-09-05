# LATEST — session 102eafc6 (idp, Otto door spec lane)

## RESUME HERE (2026-09-05T22:05Z)

Founder rejected the 3-day estimate: "need minutes, spec for deepseek". Writing
`docs/specs/otto-door-hands-and-senses.md`: DeepSeek brief for wiring the fork's 35 toolsets
behind the door's tool gateway (crew#768 CP2 on otto/ingress/worker.py, router tool loop) and
voice/photo into the Telegram binding (crew#773 CP2-CP4). Founder record:
`~/.claude/docs/founder/2026-09-05T2200Z-what-did-founder-request-9360268a.md`.
Reading hermes-v2 origin/main in a scratchpad worktree, never the stale ~/dev/code/hermes-v2.
Bypass to hermes-agent gateway: dropped, spec demands the door with hands.

# LATEST — session 56eac889 (idp, specs review lane)

## RESUME HERE (2026-09-05T22:0xZ)

**Founder ask:** "so review all and lets plan this for deepseek"
(`~/.claude/docs/founder/2026-09-05T2132Z-so-review-all-and-lets-plan-this-for-87f5df34.md`).

**Shipped:** PR #1889, branch `spec/two-hats-and-key-ingest`, worktree
`/private/tmp/claude-501/-Users-chidionyema-dev-code-idp/2eb24bf7-.../scratchpad/wt-specs`.
Three commits: the three build specs + ADR 0023 + ADR 0020 amendment; the review finding; the
cutover warning. New file `docs/specs/deepseek-work-order.md` — one dependency order across all
eighteen changes in the three specs, each item lanned repo / estate / founder with the command
that proves it done. 14 of 18 are repo work a model with no privileges can finish.

**THE FIRE (LAW 1, unfixed, needs a founder decision):** the estate's 154 NetworkPolicy objects
enforce nothing. `kubectl get ds -A` -> `kube-flannel-ds` is the only CNI DaemonSet; flannel does
not implement NetworkPolicy. From `dagster-daemon-9cd8bd67f-45h8x` (namespace carries
`default-deny-all`, both policyTypes, empty podSelector): `1.1.1.1:443` CONNECTED, `8.8.8.8:53`
CONNECTED, `10.244.1.240:3100` (backstage/catalogue, equally fenced) CONNECTED.
Remedy: Calico policy-only beside flannel — but log-only first. The 154 policies have never been
graded against real traffic, so a flag-day cutover is an estate-wide outage with 154 causes.
LAW 11 decision, not a same-night fix.

**FOUNDER ACTION:** the `deepseek` lane does not answer. `llm/config.yaml` names it in five
fallback chains with no `model_name` row; no DeepSeek env var in the router pod;
`api.deepseek.com/models` -> 401. `consoles.yaml` marks it `console_lanes: [deepseek]`, so the
key comes through https://litellm.mumchimp.com -> Models -> `deepseek`, as Kimi did on 09-04.
`[routing] default` and `cheap` in AGENTS.md both name that unserved lane.

**Two method corrections landed in the specs:** a drill is a scheduled workflow PLUS its
`drills/catalogue.yaml` row (`bin/idp-verify` only grades freshness of the last green run), and a
cluster drill runs as service user `estate-ci` via the `oke-check.yml` OIDC propagation — the
cluster refuses writes from user principals outright.

**Next:** merge #1889 when CI is green (`gh pr merge 1889 --squash --delete-branch` from the
worktree). Then item 1 of the work order: the `fence-enforcement` drill workflow + row.

---

# LATEST — session 2c88870e (.wt-vendor-probe, Kimi/aider lane)

## RESUME HERE (2026-09-05T21:29Z)

Otto: gateway pods on main-84 (idp #1872 force annotation fixed the immutable memory Job; both
bots answered 4 tasks at ~20:26Z, tenant estate). Founder says the bot is still awkward: every
Telegram message on both bots lands on the v1 spine (`otto/`, no tools, no git, no research);
the proactive hermes-agent gateway holds Ottototbot's token as DISABLED_TELEGRAM_BOT_TOKEN
(platform/hermes-agent/gateway.yaml:19-29, founder 2026-09-05) and received 0 messages in 14h.
Open founder decision: keep both bots on the spine, or point Ottototbot's webhook back at the
hermes-agent gateway until crew#768 CP2 gives the spine hands.
Merged tonight: idp #1872, #1874 (ADR 0021 two hats), #1876 (five-capabilities spec), #1873
(root-trust rows, fixed red main); hermes-v2 #86 (aux/vision -> gemini), #87 (ADR 0022: voice on,
flags kept, STT local-first; image build pending -> idp pin PR by cron).
Waiting: task bz0rhijmu (main CI on #1873 merge, then #1887 checks). Then merge idp #1880 (ADR
0022 record) and #1887 (spec defers to ADR 0022): `gh pr merge <n> --squash --delete-branch`
from the branch's worktree. Then watch the main-86 image pin land and Flux roll hermes-agent.
Board: crew#768 0/7, #773 0/7, #717 0/33 ticked. Founder records:
`~/.claude/docs/founder/2026-09-05T2023Z-spec-for-deepseek-to-get-everything-done-and-a8f82afe.md`,
`~/.claude/docs/founder/2026-09-05T1904Z-document-e37607fd.md`.

## RESUME HERE (2026-09-05 12:55Z, Headlamp)
Headlamp credential prompt: the minted kubeconfig now carries the absolute oci path and SUPPRESS_LABEL_WARNING in its exec block (bin/idp-kube), and bin/idp-headlamp-mac links it into the desktop app store and ~/.kube/estate.yaml. PR fix/headlamp-exec-plugin.

## RESUME HERE (2026-09-05 13:25Z, Otto lanes)
Probe otto-answer-probe-29810160: bulk and verify lanes point at deepseek, which the router does not serve (400); Otto key allowlist was kimi,minimax,deepseek so gemini and embed were 403. PR fix/otto-lanes-gemini moves bulk+verify to gemini in the three lane files and sets the key rows in bin/idp-estate-seed to minimax,gemini,embed (agent-workforce: minimax,fast,embed). After merge: gh workflow run oke-check.yml -f mode=apply so idp-router-key updates the live keys.

## RESUME HERE — 2026-09-05T20:5xZ, idp session 2eb24bf7 (specs lane)

**Doing:** writing the two build specs the founder asked for
(`~/.claude/docs/founder/2026-09-05T2025Z-ok-need-do-addrees-quicck-wwe-have-deepseek-29766295.md`):
`docs/specs/key-ingest-door.md` and `docs/specs/two-hats-tenant-split.md`, plus the ADR 0020
amendment recording that Bitwarden cannot be written to.

**Why a worktree:** this checkout is shared. At ~20:50Z another session stashed my tracked edits
(`stash@{0}`, "wip before sync branch") and a `git clean` deleted my untracked new files —
`bin/idp-human-vault-probe`, `docs/specs/key-ingest-door.md`,
`docs/specs/two-hats-tenant-split.md` — which had to be rewritten. Branch:
`spec/two-hats-and-key-ingest`. Worktree under the session scratchpad. Nothing of another
session's is carried: `stash@{0}` also holds their `checkpoints/LATEST.md` and is left alone.

**Measured, and it is the load-bearing fact:** Bitwarden Secrets Manager refuses a plaintext write
(`400 Key is not a valid encrypted string`) because it is zero-knowledge, and the estate project
holds zero secrets while the machine account reads it fine. So the portal's one-shot ingest road
writes to `estate-vault`; a zero-knowledge store is a source to sync from, never a destination.
Re-measure with `bin/idp-human-vault-probe --write`.

**Still down:** `cyrus-webhook` is `SecretSyncedError` on `cyrus-linear-api-token`. The fix is the
door, not a fourth trip to Bitwarden's web interface.

**Next:** commit the specs in the worktree, push, open the PR.
