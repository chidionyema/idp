# Incident report: three incidents, one defect

Date: 2026-08-30. Author of the analysis: the founder, in two messages at 23:26Z and 23:32Z,
captured verbatim by `founder-doc-capture.py` as
`~/.claude/docs/founder/2026-08-30T2326Z-1-delete-the-enumerated-list-secret-reloader-stakater-4ca529a0.md`
and `~/.claude/docs/founder/2026-08-30T2332Z-yes-and-the-pattern-is-sound-but-two-c08d08d9.md`.
Every quotation below is his, unedited. Every receipt beside it is a path in this repository at
the commit that carries this page.

This is not a report about one outage. It is the report that says three separate outages, already
written up as three separate incidents, were one defect wearing three costumes, and it names the
rule that ends the class rather than the three fixes that ended the instances.

## The meta-class, in his words

> Your three incidents are one defect:
>
> **An invariant that exists only in a person's head, enforced nowhere, discoverable only in
> production.**
>
> Reloader: "this annotation must list every Secret the pod consumes" — enforced by a hand-edited
> test in the same PR as the change.
> Kyverno gridlock: "the rendered manifest must satisfy cluster policy" — checked only after merge,
> by the cluster.
> envsubst: "this field must stay a string through the render pipeline" — checked only by the API
> server at dry-run.
>
> Same shape three times.

| Instance | The invariant nobody could enforce | Where it was discovered | Receipt |
|---|---|---|---|
| Reloader / idp#955, crew#684 | "this annotation lists every Secret the pod consumes" | production, twice: Otto silently omitted the Langfuse Secret added in the same commit, and the healthchecks and portal annotations sat in namespaces the watcher did not read | `git show 5a151c2b -- platform/hermes-agent/gateway.yaml`; the namespace list at `platform/reloader/reloader.yaml` before this change |
| Kyverno gridlock / crew#539, crew#325 | "the rendered manifest satisfies cluster policy" | production, after merge: the release went `Failed` and monitoring stayed down 8h | `bin/idp-kyverno-render` header, which is the control written after it |
| envsubst / run 33339964930 | "this field stays a string through the render pipeline" | production, at API-server dry-run: `.spec.appID: expected string, got 4740261` | `tests/test_incident_run33339964930_the_cluster_takes_what_git_holds.py` |

The Reloader instance is the one worth reading twice, because it had a test:

> That's the actual lesson from the stale test: an assertion a developer can green by editing the
> expectation is not a control. It lived in the same repo, same PR, same reviewer as the change
> that broke it. Controls have to sit outside the blast radius of the thing they guard.

## The ladder

> Every control gets placed at the lowest-numbered rung that's achievable, and the session must
> state why lower rungs were rejected:
>
> 0. **Delete the surface.** No enumerated list means no stale list. (Reloader `auto` instead of
>    the explicit list.)
> 1. **Make it inexpressible.** Type, schema, or mutating admission that renders the wrong state
>    unconstructible.
> 2. **Fail before merge.** kubeconform, kyverno apply, rendered-manifest tests in CI.
> 3. **Fail at admission.** Cluster-side validating policy.
> 4. **Detect at runtime.** Generic invariant alert.
> 5. **Document it.** Not a control. Counts as zero.

Where each instance now sits:

| Instance | Rung | The control | Why no lower rung |
|---|---|---|---|
| Reloader | 0, then 1 | `reloader.stakater.com/auto: "true"` has no names in it, so it cannot be stale; `platform/edge/require-auto-reload.yaml` then injects it at admission on every workload | rung 0 alone leaves a new service free to forget the annotation entirely, which is the same defect with a different first symptom |
| Kyverno gridlock | 2 | `bin/idp-kyverno-render` renders every HelmRelease the way helm-controller will and judges it with the cluster's own policies before the pull request | there is no schema that makes a policy-violating pod unconstructible; the policies are the schema |
| envsubst | 0 available, at rung 1 today | quotes ride inside the substituted value | his own note: the rung-0 move, "stop text-substituting into typed CRDs at all", is designed and not built — Blueprint 2, kubeconform plus Kustomize replacements |

## The proof obligation

> A control must be demonstrated failing against the pre-fix state before the task can close.
>
> Write the policy, then run it against the broken manifest and show it rejecting. A control nobody
> has watched fail is not known to work — it's a green check of unknown provenance, which is
> precisely what the stale expected list was. This is a red-test discipline applied to
> infrastructure.

In this repository that obligation is not a habit, it is a test:
`tests/test_incident_crew684_every_workload_restarts_when_its_config_changes.py::test_the_control_refuses_the_state_it_was_written_for`
runs the Kyverno policy against `tests/fixtures/reloader/hand-kept-list.bad.yaml`, which is the
pre-fix healthchecks Deployment verbatim from commit 5a151c2b, and fails if the policy admits it.
The control is watched failing on every gate run, not once by the person who wrote it.

## The budget

> "Every incident yields a new control" is unbounded growth, and controls rot — your stale test was
> a control. Without a budget you build a second system as complex as the first, with its own
> failure modes, and the estate gets less predictable rather than more.
>
> Two rules bound it:
>
> A control that names a specific service is the wrong control. Per-service assertions are O(n)
> rot. Estate-wide policy is O(1). If the session's fix mentions `hermes-agent-langfuse`, it hasn't
> finished — it's still at the incident, not the class.
>
> Adding a control at rung 2 or above requires deleting a weaker one it subsumes. The Kyverno
> mutation makes the Reloader test redundant; delete the test. Net control count should stay
> roughly flat while coverage rises.

Applied, on the change that carries this page: five per-workload assertions deleted, one estate-wide
guard added, net minus four.

| Deleted | Was in |
|---|---|
| `test_a_rotated_key_rolls_both_pods` | `tests/test_incident_crew684_the_read_only_key_is_32_characters_and_a_rotation_rolls_both_pods.py` |
| `test_router_opts_in_to_a_restart_on_its_upstream_secret` | `tests/test_incident_crew506_cp4_rotated_secret_never_reaches_a_running_pod.py` |
| `test_reloader_row_watches_the_router_namespace_and_only_opted_in_workloads` | same file |
| `test_a_secret_that_predates_reloader_still_rolls_its_workload` | same file |
| `test_a_reloader_annotation_is_not_the_guard_for_mac_run` | `tests/test_incident_crew561_a_subpath_configmap_needs_a_hashed_name_to_reach_the_pod.py` |
| `test_the_pod_rolls_when_the_vault_entry_changes` | `tests/test_hermes_agent_row.py` |

## The advice that undercut the goal

The same message refused a piece of advice this estate had already merged, in idp#1027, nine hours
earlier:

> `remediation: strategy: uninstall` and `kubectl delete namespace` as routine practice are the
> opposite of what you're asking for. Uninstalling a wedged HelmRelease turns a degraded service
> into a deleted one — PVCs, PDBs, Secrets created by the release, gone — and for anything stateful
> that's a self-inflicted outage triggered automatically at 3am by a chart bug. Namespace deletion
> also hangs on finalizers roughly as often as it works.
>
> More importantly, both destroy the evidence. You cannot convert an incident into a permanent
> control if your first move erases the state that tells you which invariant was violated. Paving
> over is a way to survive incidents forever without ever eliminating a class. It's a stability
> strategy in direct conflict with the strategy you actually want.
>
> Keep the ability to repave — but as a manual break-glass after capture, never as automated
> remediation.

`strategy: uninstall` is gone from all nine rows that carried it. The bounded retries stay, the
default rollback strategy stays, and the repave is a named hand: `bin/idp-oke-break-glass
helm-retry`. `tests/test_incident_run33339964930_the_cluster_takes_what_git_holds.py` refuses a
tenth row that tries to add it back.

## What is still not a control

Named here so it is not mistaken for done:

- **Every infra change ships a control or says why not.** His rule, machine-checked on the pull
  request rather than written in a rules file — "prose in a CLAUDE.md is itself an invariant living
  in someone's head, you'd be violating your own pattern". Not built.
- **kubeconform before merge**, and Kustomize replacements instead of text substitution into typed
  CRDs (Blueprint 2, the rung-0 move for the envsubst instance). Designed, not built.
- **The runtime backstop**: an alert on any Secret whose `resourceVersion` is newer than the
  creation time of every pod referencing it. His rung 4, "generic query, catches this class
  regardless of cause — bad annotation, Reloader crashlooped, webhook down". Not built.
- **The number he says is the one worth putting on a wall**: the count of signals the estate
  routinely dismisses. "All-green is easy to fake by ignoring amber, and a dashboard you've learned
  to discount is worse than no dashboard." Nothing measures it.

## On sleeping at night

> Achievable for this family. Config and manifest defects are deterministic and statically
> decidable; there's no reason a type error or a missing annotation should ever reach your cluster
> again, and driving that to zero is a finite project.
>
> Not achievable for capacity, upstream dependency failure, or hardware. Those you absorb rather
> than eliminate.
