## RESUME HERE (2026-09-04T21:43:53Z)

crew#841: the bridge could reach nothing because this VCN's security list has zero egress rules
and reachability comes from network security groups, which the instance was in none of. It now
has its own egress-only group and was rebuilt into it. New instance
ocid1.instance.oc1.uk-london-1.anwgiljtpixfknic4lgidj4qofl6b4ngh6mbivgni4he74liqkzjdbjtvtnq,
RUNNING, 10.0.144.222. Follow-up PR carries the group in platform/oci/bridge.tf and the new
OCID in platform/rbac/bridge.yaml.

# RESUME HERE — 2026-09-04T21:5xZ · session 85f840c5 · idp

Answered "who used 176M MiniMax tokens". Measured from LiteLLM_SpendLogs (estate-1, db litellm):

| consumer | what it is | 30 Aug | 31 Aug | 1 Sep | 2 Sep | 3 Sep | 4 Sep |
|---|---|---|---|---|---|---|---|
| sovereign-kernel | KINI, the Temporal kernel | 39.6M | 29.9M | 9.2M | 5.9M | 4.7M | 0.3M |
| k8sgpt-20260827T223258Z | the healing loop, in-cluster | 1.1M | 9.0M | 8.6M | 10.4M | 9.7M | 6.8M |
| laptop-20260829T143252Z | opencode on the Mac | 0.03M | 0.09M | 20.6M | 0.002M | 0.001M | 18.0M |
| science-20260830T053056Z | research engine | 0.25M | – | – | – | – | 0.05M |

hermes agent appears nowhere in the ledger, consistent with it being down.
laptop key = ~/.config/prospector/secrets.d/LITELLM_API_KEY, used by ~/.zshrc:73 and
~/.config/opencode/opencode.json (default model estate/minimax).

k8sgpt root cause: 52 Result objects (25 ConfigMap "is empty" = noise, 18 Service, 5 Job,
4 Pod), re-explained ~77 cycles/day because spec.analysis is unset and noCache: true.
4,004 calls/day, ~1,950 output tokens each.

## NEXT STEP
Branch fix/k8sgpt-stop-re-explaining: platform/healing/analyzer/k8sgpt.yaml gets
spec.analysis.interval: 1h and spec.filters limited to the nine core analyzers
(drops ConfigMap). Drill: oke-check. Then PR with auto-merge.

## 2026-09-04T22:45Z update
Founder said disable. Stopped and launchctl-disabled: ai.estate.sovereign-worker,
ai.estate.cockpit, com.chidionyema.maestro. All three confirmed gone from launchctl list
and from ps. Aiden was already dormant (no launchd job, untouched since 26 Aug) and makes
no model calls; Maestro made none either — neither appears in the router ledger.

## NEXT STEP
k8sgpt is the only remaining spender. Worktree off origin/main, edit
platform/healing/analyzer/k8sgpt.yaml: add spec.analysis.interval: 1h and spec.filters
(Pod, Deployment, ReplicaSet, StatefulSet, CronJob, Service, Ingress,
PersistentVolumeClaim, Node) to drop the 25 ConfigMap "is empty" findings.
Drill: oke-check. PR with auto-merge.

## RESUME HERE — 2026-09-04T22:2xZ — session 1790f775

**Otto is mute and the cause is measured.** The `llm` Flux row has been failing since the spend
breaker was rewritten today: `post build failed for 'ConfigMap.v1/spend-check-scripts': envsubst
error: variable substitution failed: variable not set (strict mode): "CALLS"`. Flux's post-build
substitution is eating the `${...}` shell variables in `platform/llm/spend-breaker-digest.yaml`,
so the whole namespace stopped applying. That is why the Gemini-first router config merged at
22:01Z (idp#1580) has never reached the router, and why `hindsight` and `research-engine` are also
False on `dependency 'flux-system/llm' is not ready`.

Fix in flight on branch `fix/llm-row-envsubst-blocks-router`: annotate the ConfigMap with
`kustomize.toolkit.fluxcd.io/substitute: disabled`, which is the documented Flux escape for a
resource that is a script rather than a template. It is the only ConfigMap in `platform/llm`
carrying a script, so one annotation clears the class.

**Measured facts, 22:1x–22:2xZ, from `OCI_CLI_PROFILE=DEFAULT OCI_CLI_AUTH=api_key bin/idp-kube`
(the laptop's API key still works; only the `otto` session profile is expired):**

- Gemini answers: `gemini-2.5-flash` returned "alive" on the estate key, and both model ids the
  router declares (`gemini-2.5-flash`, `gemini-2.5-pro`) are in the live model list.
- DeepSeek: two distinct keys exist on this machine (vault `...af0f`, `~/.config/estate/estate.env`
  `...bc56`) and the vendor refuses both with "api key is invalid". The founder confirms the
  account has credit, so this is a stale credential, not a lapsed account.
- Telegram delivers to the OLD door, `otto.mumchimp.com/telegram`; 0 pending, no delivery errors.
  The one door `/webhook/telegram` is live (401 on an unsigned POST).
- `scheduling` reports Ready=True, but `otto-gateway`, `otto-golden` and `hermes-agent` still say
  `dependency 'flux-system/scheduling' is not ready` — re-check after the llm row is green.

**Next after the fix lands:** the founder's 19:35Z ruling (`~/.claude/docs/founder/
2026-09-04T1935Z-in-this-otto-dilemma-state-of-the-art-918ecd6f.md`) is that otto-gateway is the
Universal Event Gateway and the flakiness IS the three doors — hermes-agent, otto-golden and
otto-gateway — competing to register with Telegram. Retiring the two losing doors is the follow-on,
not a new decision.
