# Git is the only writer of the cluster

On 2026-09-03 the founder ordered a lockdown after the estate inventory showed objects that no
git file held: things written by hand at 2 AM, by whichever key was on a laptop, and never
recorded. His words: "we cant let this drift ever happen again", then "if you dont come up
with a solution then lockdown is happening". This page records the first of the three
controls, the one that stops the drift at the door.

## What changed

A cluster-wide admission policy, `flux-only-writes`, refuses any create, update or delete that
comes from an OCI user principal. On this cluster every person, laptop key and agent presents
to Kubernetes as the OCI user it signed with, so that identity class is the fence. Flux and
every controller that runs inside the cluster present as system accounts and are never judged.

One identity is excused: the service user that the deploy workflow signs with. That workflow
is the founder's deploy button. It is the only path a person has to change the cluster, and
its runs are the audit trail. The excused identity is named once, in the estate configuration
file, and substituted into the policy when Flux renders it. The policy file itself carries no
identifier.

The cluster's own control plane addons are not covered, on purpose. The admission webhook is
configured to leave the system namespace and the policy engine's own namespace alone, so the
managed control plane keeps working whatever this policy says.

## What it means in practice

- A `kubectl apply`, `edit`, `patch` or `delete` from any laptop is refused with a message
  that names the identity, the object and the rule. The fix is a change on main.
- A read from a laptop still works. Reading is not writing, and the read-only identity for
  laptops is the second control, delivered separately.
- Flux keeps reconciling exactly as before, and so does every operator in the cluster.
- The deploy workflow keeps working, because its service user is the excused identity.
- If the policy engine is down, writes fail closed. That is already the behaviour of the
  other enforced policies in this folder, and it is the behaviour the lockdown asks for.

## The proof

The test suite for this control runs the policy through the policy engine's own command-line
tool four times, with the same admission identities the cluster sees: the founder's laptop key
as measured on the day, which is refused; the deploy workflow's service user, which passes; the
Flux controller, which is skipped; and no identity at all, which is how the pull-request render
check applies every policy and which is also skipped. The suite also proves the identifier is
written once and that the policy is enforced on every kind and every write.

## What comes next

The second control turns the laptop identity into a read-only one, so a laptop cannot even
attempt a write. The third puts the cloud objects that today live outside git under the
infrastructure code with a daily drift check that reads red when anything differs.
