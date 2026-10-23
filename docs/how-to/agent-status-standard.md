# The one status block — how an agent reports, so the founder never has to ask

Founder, 2026-10-23: *"the fact that I'm having to ask shows a fundamental concerning gap in how we
work and report updates to founder, this should be standardised... agents should be aware of where
they are and their objectives and should only be reporting as such, not waffling and cryptic posts
that require the founder to interrogate. This should be one time, consistent, easy to see at a
glance — else what exactly is agent doing?"*

He is right, and the cause is not secrecy. It is that the estate had no **shape** for an update, so
each agent invented prose, and prose has to be interrogated. Everything an update needs was already
on disk, machine-readable, in four places nobody joined up:

| What the founder asks | Where it already is |
|---|---|
| what is this agent trying to do? | the issue title |
| what are its sub-goals, and which are done? | the `- [ ]` checklist in the issue body |
| who holds what right now? | the `CLAIM agent= paths= heartbeat=` comment (AGENTS.md §5) |
| what has it actually attempted? | every commit carrying `Claim: <owner>/<repo>#<n>` |
| where does it stand? | the `greenlane` commit status on that commit's sha |
| what has landed? | whether that commit is an ancestor of `origin/main` |

So there is exactly one command, and no hand-written status:

```bash
bin/estate-work-status              # every live claim, glanceable table first
bin/estate-work-status --agent pi   # one agent
bin/estate-work-status --issue 6984 # one claim, in full
bin/estate-work-status --json       # the same facts, for /fleet
```

It measures; it does not remember. It writes nothing. An agent that keeps its issue checklist
current and stamps its trailer cannot report badly, and cannot flatter itself: the state word is
computed from GitHub and git, not chosen.

## The five states, and what each obliges

| State | Means | What the agent does next |
|---|---|---|
| `IN LANE` | pushed, the lane has a verdict or is still testing | wait on the lane; do not re-run it by hand |
| `LANDED` | a commit naming this claim is an ancestor of `main` | close the issue with the proof line |
| `BLOCKED` | the lane printed a failure on the newest commit | fix or relane; the state carries the lane's own words |
| `LOCAL` | commits exist, none is on a `lane/*` branch | push the lane, or the work is invisible |
| `IDLE` | the claim is live and not one commit names it | start, or release the claim |
| `STALE` | no heartbeat for two hours | the claim is released; the next agent may take it |

`BLOCKED` exits non-zero, so a scheduled job can mail it and no agent has to notice by hand.

## What an agent posts when it speaks to the founder

The block `bin/estate-work-status` prints for its own claim, verbatim, plus at most one sentence of
intent. Nothing else: no narrative of what it tried, no apology, no "next I will". If a claim is
missing from the table, the agent has not declared its work and the first thing to fix is the claim,
not the sentence.

## The checklist is the plan

The issue body carries the sub-goals as a task list, in the order they will be done:

```markdown
- [x] pin the behaviour as Given/When/Then
- [x] store the claim and prove it re-executes
- [ ] render the block on /fleet
```

Sub-goals move from `- [ ]` to `- [x]` only when they are proven — the same rule as §3 of AGENTS.md,
applied to the plan itself. An issue with no checklist renders `sub-goals: none written`, which is
itself the finding.

## What this does not do

It does not grade the work: `LANDED` is a fact about git, not a claim that the change is any good, and
`BLOCKED` is the lane's sentence, not a diagnosis. Those verdicts belong to the gate, `/fleet` and the
founder — this command's whole job is to make "what exactly is the agent doing" answerable without
asking the agent.
