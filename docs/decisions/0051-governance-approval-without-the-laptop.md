# 0051 - Governance approval without the laptop

- Status: proposed
- Date: 2026-11-06
- Deciders: founder
- Binding: Genesis gate changes in `argon` and `argon-sync`

## Context

Every gate approval in the estate currently needs the laptop:

- `ops/git/gate_approval.mjs request` runs on the Mac and writes the patch-bound
  request to `~/.estate/state/gate-approvals/`.
- The founder approves it through Otto, which polls Telegram on the Mac and signs
  with `ESTATE_RECEIPT_KEY`.
- `inbox/reviews/<approval-id>/<reviewer>.json` must be committed before the
  approval is accepted.

The estate is moving off the laptop today. With the Mac shut, a gate change can
never be approved, so every governance fix stops - which is the failure we are
looking at right now with the three argon-sync policy files.

## Decision

Move the approval authority to GitHub's own signed review event, and generate the
request in CI.

1. **The request is produced by the approval workflow**, not by a script on a
   laptop: on `pull_request` it computes the patch digest with the same code
   (`gate_approval.mjs request`) and posts the `GEN-GATE-...` id as a PR comment.
2. **The founder approves from the GitHub mobile app.** A
   `pull_request_review` event with `state: approved` by the founder's account is
   the approval. It is authenticated by GitHub, carries a timestamp and a commit
   SHA, and cannot be forged by an agent without the founder's account.
3. **The workflow signs** with `ESTATE_RECEIPT_KEY` from Actions secrets and
   writes the approval record the verifier already reads. No secret is ever on a
   laptop, and no Mac process is in the path.
4. **The verifier accepts either proof**: a signed approval record (as today) or
   a GitHub-approved review by the founder on the exact head SHA that is being
   promoted. The second is what makes the gate laptop-free.

## Consequences

- A gate change becomes: push branch -> CI proposes `GEN-GATE-...` -> founder taps
  Approve on the phone -> the workflow signs -> verify goes green. No laptop, no
  Telegram poller, no local state directory.
- The signing key's blast radius moves from the Mac to GitHub Actions secrets.
  That is a real trust move and it is bounded: only maintainers can change
  workflows, and the verifier itself is loaded from the trusted SHA, not from the
  branch.
- A compromised founder account can approve. That is already true of every
  GitHub-protected repository, and it is strictly stronger than a Telegram
  message that any process on the Mac could replay.
- The Mac keeps the dev loop (disk-sentinel, local builds); it stops being part of
  the approval path for anything.

## What this does not fix

The GitHub plan. `argon` and `argon-sync` are private on a free account, so
server-side rulesets cannot be enabled; this decision makes approval remote, not
branch protection. The capability split (agents never hold a write token for
`main`) and the restore lane remain the controls that do not need the plan.

## Alternatives considered

- **Keep Otto as the approver, move it to a small cloud host.** Works, but adds a
  service that holds the key and a poller that can miss messages. GitHub already
  has the identity, the event and the audit trail.
- **Approve by signed commit from the phone.** No phone-side git signing exists
  that the estate can verify.
- **Make the repos public to buy rulesets.** A visibility decision, not a
  governance one; still on the table for `argon`.
