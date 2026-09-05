# Demo: pr-report

`bin/pr-report <n>` reshapes one pull request into the input that
`policy/operating_model.rego` reads and runs the gate with conftest. It exists
because the operating model (crew#286, `docs/policy/enterprise-operating-model.md`)
is a set of rules a PR must satisfy: an identity ships with its scope, no
instruction line sends a person to a console, a founder-facing change names the
word he can veto with (nothing waits for `APPROVE:` since 2026-08-27), a `platform/oci`
change declares its monthly cost and its canary label. A rule nobody can be stopped by is a wish, so the rules run on
every PR.

Run on a live PR. On the evening it landed, idp#155 was refused because it changed
`docs/policy/` without an `Approval-word:` line (that rule was retired on 2026-08-27; a
`DENY: <word>` from the founder still refuses):

```
$ bin/pr-report 155
rule=founder_approval_required | the PR changes a founder-facing surface (backstage/, platform/identity/, platform/edge/, docs/policy/, estate-defaults.yaml) and names no approval word | fix: add a line `Approval-word: <word>` to the PR body; the founder replies `APPROVE: <word>` or `DENY: <word>`
FAIL    operating-model gate #155
```

And the PR that carried the gate itself, which declares everything:

```
$ bin/pr-report 163
PASS    operating-model gate #163
```

Every refusal is one line in the shape `rule=<name> | <what is wrong> | fix: <what
to change>`. In CI (`operating-model-gate` job) the same lines are posted as a PR
comment with `--comment`, so the author repairs from the comment and the founder
is not in the loop.

Proof both ways, without a live PR:

```
$ bin/policy-test
opmodel-ok.json      0        0        allows an identity with its grant, an approval word, a cost line and the canary label (crew#286)
opmodel-half-provisioned.json 1        1        refuses an identity created with no grant or policy in the same PR (ZCP, crew#287)
opmodel-gui.json     1        1        refuses an instruction line that sends a person to a console
opmodel-no-approval.json 0        0        allows a founder-facing change with no Approval-word line (retired rule, 2026-08-27)
opmodel-over-budget.json 1        1        refuses a platform/oci change whose declared monthly cost beats the budget
opmodel-no-canary.json 1        1        refuses a platform/oci change with no canary label
PASS      every policy allows its good case and refuses its bad ones
```
