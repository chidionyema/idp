# Otto on the founder's Mac: the setup, the friction, and what fixed it (crew#561)

Written 2026-08-30 at the founder's request (record:
`~/.claude/docs/founder/2026-08-30T0948Z-thasnk-can-you-write-up-the-full-setup-b4ab7085.md`).
The how-to page is [Onboarding: Otto](../how-to/onboarding/otto.md); this page is the story
behind it, kept so nobody walks the same road twice (LAW 3).

## What was being built

Otto is the hermes-agent gateway pod on the OKE cluster. It holds the one Telegram bot token. When
the founder types `mac-run hostname` in Telegram, the pod opens an SSH session to his MacBook over
the tailnet and answers `chidis-MacBook-Pro.local`. Done means his own round trip, not ours.

## The setup, layer by layer

| Layer | What it is | Where it lives |
|---|---|---|
| The pod | one replica, `Recreate` strategy, because one token admits one poller | `platform/hermes-agent/gateway.yaml` |
| The wrapper | `mac-run`, an `ssh` one-liner mounted at `/usr/local/bin/mac-run` | `platform/hermes-agent/mac-run.tpl`, rendered into a ConfigMap by a `configMapGenerator` in `kustomization.yaml` |
| The key | an ed25519 private key, minted by CI, held as the vault entry `hermes-mac-run`, synced by external-secrets, mounted read-only at `/run/secrets/hermes-agent-mac-run/id_ed25519` | `platform/hermes-agent/mac-run-key.yaml` |
| The public half on the Mac | adopted into `~/.ssh/authorized_keys` by `bin/idp-mac-adopt-otto`, which reads it from any dispatched run that minted it (idp#885) | `bin/idp-mac-adopt-otto` |
| The network | a Tailscale sidecar in the pod exposing a SOCKS5 proxy on `localhost:1055`; `ssh` goes through it with `ProxyCommand nc -x localhost:1055 %h %p` | `platform/tailscale/policy.hujson` (`tag:k8s` may reach `tag:founder-mac` on port 22) |
| The two facts about the Mac | `FOUNDER_MAC_USER` and `FOUNDER_MAC_TS_IP`, substituted by Flux at apply time, never typed into a file (LAW 46) | `clusters/oke/estate-config.yaml` |
| Host keys | `UserKnownHostsFile` under `HERMES_HOME` (`/data`, the PVC), `StrictHostKeyChecking=accept-new` | the pod's PVC `hermes-agent-data` |
| The proof | the `otto-parity` playbook: `gateway-ready`, `no-restart-loop`, `key-usable`, `key-direct`, `tailnet-up`, `mac-run-hostname`, `hindsight-answers`, `cron-lanes-installed` | `bin/idp-oke-break-glass`; run with `gh workflow run oke-check.yml -R chidionyema/idp -f mode=break-glass -f playbook=otto-parity` |

The script, as shipped:

```sh
src=${MAC_RUN_KEY_DIR:-/run/secrets/hermes-agent-mac-run}/id_ed25519
exec ssh -i "$src" -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new \
  -o UserKnownHostsFile="${HERMES_HOME:-/data}/known_hosts" -o ConnectTimeout=5 \
  -o ProxyCommand='nc -x localhost:1055 %h %p' \
  "${FOUNDER_MAC_USER}@${FOUNDER_MAC_TS_IP}" "$@"
```

## The friction, in the order it was met

Each row is a real failure, the wrong theory if there was one, and the fix that landed.

| # | What broke | What it looked like | Root cause | Fix |
|---|---|---|---|---|
| 1 | The policy applier refused its own policy | Tailscale ACL apply failed on the first push | the policy header spelled the `${...}` placeholder literally, so the applier read a variable name where it wanted a tag | idp#883: header no longer spells the placeholder |
| 2 | The Mac never learned the key | `mac-run` answered `Permission denied (publickey)` | the adopter looked for the public key in one run id; the minting run was a different dispatch | idp#885: the adopter reads any dispatched run that minted it |
| 3 | The gateway crash-looped on the new image | `no-restart-loop` red; Telegram went dark because the cluster pod was now the only Hermes | the image's boot copied the build tree with `cp --preserve=mode` onto the mount root, so it also `chmod`ed the volume mount itself and the process could not start | hermes-v2#51 then #55 (copy the build's children, never the mount root); rolled by idp#897 and #903 |
| 4 | A `DONE:` was posted and retracted within two minutes | founder: "OTTO CLAIMS NO ACCESS TO GITHUB OR MAC" | the plumbing worked but every estate skill in the image told Otto it had no Mac and no GitHub; the parity playbook graded the pod, not what Otto believed | hermes-v2#56 (a `gh` skill and a `founder-mac` skill); the rule that DONE needs his receipt, not ours |
| 5 | `mac-run` died copying its key | `cp: cannot create regular file '/tmp/mac-run.id_ed25519': Permission denied` (run 33297964325) | the container has a read-only root filesystem; `/tmp` is not writable | idp#935 moved the copy under `HERMES_HOME`; idp#949 removed the copy altogether and passes the mounted key to `ssh -i`; parity row `key-direct` grades exactly that |
| 6 | The pod kept running the old script after #949 merged | `key-direct ok`, `mac-run-hostname` still failing with the `/tmp` error | a `subPath` ConfigMap mount is never refreshed by the kubelet; only a pod restart changes the file. Nothing restarted the pod | idp#955 added Reloader annotations to the Deployment |
| 7 | Reloader did not roll it either | same symptom after #955 | the ConfigMap change and the annotation landed in the same Flux reconcile, so Reloader (autoReloadAll false, reloadOnCreate true) never saw a change to react to. A `needs-hash` annotation on a plain ConfigMap does nothing, proved with a local `kustomize build` | idp#970: the script became `mac-run.tpl` behind a `configMapGenerator`. Its name now carries a content hash, so a change to the script changes the pod spec and Kubernetes rolls the pod by itself |
| 8 | Flux showed 41 Kustomizations not Ready during the work | `revision is not up to date` everywhere | 64 commits in 6 hours on main (half of them image automation) while leaf Kustomizations reconcile every 10 minutes with `wait: true`; each dependency lagged the source by a reconcile | nothing to fix; it cleared alone. A stall of this shape is a push-rate symptom, not a cluster fault |
| 9 | Proof runs kept vanishing | otto-parity runs 33297680866 and 33300864087 `cancelled` | `oke-check.yml` has one concurrency group; any lane's dispatch cancels the queued one | nothing to fix; accept another lane's green run when the rows are the same (33300944301 is the one on record) |
| 10 | `gateway-ready` red on an otherwise green run | run 33300585891: `timed out waiting for the condition`, every other row `ok` | the row ran while the pod was mid-roll from #970; a new image or script is a 4 to 5 minute outage by design | none; `no-restart-loop` tells a boot apart from a crash |

## What the class of mistake was

Rows 5, 6 and 7 are one lesson: **a fix was proved on the wrong surface.** The repository held the
right script three times before the pod did. The rule that came out of it is on the how-to page
and in the parity playbook: the proof is the row that runs the shipped command from inside the
pod (`mac-run-hostname`), and a merge is never the receipt.

Row 4 is the estate's other recurring class: a `DONE:` from a session's own evidence. The
definition of done (`docs/reference/policy/definition-of-done.md`) says built, merged and green is
inventory; only the founder's use is done.

## Where it stands

- Shipped: idp#876, #883, #885, #897, #903, #935, #949, #955, #970; hermes-v2#51, #55, #56.
- Proof from the pod: otto-parity run 33300944301, every row `ok`, `mac-run-hostname` answering
  `chidis-MacBook-Pro.local`.
- Waiting: the founder's own Telegram `mac-run hostname` (blocker pinned in his DM), which turns
  the crew#561 handoff from INVENTORY into DONE.

## Gates met on the way

The rule-guard refused, correctly, a two-point `git diff` (use the merge-base), a bare
`gh pr merge` while main's last run was red, a FOUNDER ACTION line with no Telegram message and no
device word, and any branch a sibling worktree already owned. Each refusal saved a repeat of a
recorded incident; none was worked around.
