# Founder judgement as fleet training material (2026-10-30)

**What this is.** The founder's judgement is the estate's scarcest input: it arrives in a
sentence, it generalises to a hundred situations, and it is gone by the next session unless
it is written down where the fleet loads it. This file writes it down once -- in the founder's
words, with the incident it came from, generalised into a rule an agent can apply to a
situation the founder never saw, and the place in the estate that holds it.

**How to use it.** Before you act, find the judgement that matches your situation. Each one
has a **trigger** (when it applies), the **words** (the founder, attributed), the **incident**
(measured, not remembered), the **rule** (the generalisation), and the **enforcement** (the
probe, gate or file that keeps it true when nobody is watching). If your situation matches a
trigger and you cannot point at the rule, you are about to repeat the incident.

Related: [ADR 0049 -- one unified estate metric](../decisions/0049-one-unified-estate-metric.md)
(the machinery these judgements now run on), and `catalog/critical-functions.json` (the data
that carries the priorities).

---

## J1 -- "We dont have to degrade the services."

**Incident (measured 2026-10-30).** The estate's memory door, `https://mcp.mumchimp.com/estate/mcp`,
is unreachable: TCP 443 opens, the TLS handshake dies (`TLSv1.3 (OUT), TLS alert, decode error
(562)`; `unexpected eof while reading`), and the estate's own client says `memory door
unreachable: URLError: EOF occurred in violation of protocol`. Every agent's brief, recall and
remember go through that one door.

**Rule.** A service that comes back in a worse shape than it went down has not been restored.
When an estate capability goes down, the answer is a tier that keeps the **same contract**
behind the **same door** -- all three of brief, recall and remember, marked `degraded`/`local`,
with the facts it held replayed when the door returns. A fallback that serves a *subset* is a
different product wearing the old name; a fallback that serves the same contract is a cache.
And there is never a second door: two doors become two truths, and the estate's memory is
one plane because one plane is the only thing that can be trusted to be shared.

**Trigger.** The door is unreachable, slow, or answering with less than it promised.

**Enforcement.** One client, one URL: `platform/estate/memory/door.py`. The bridge marks its
replies `degraded`/`local` and replays pending facts when the door returns. The
**memory-plane** probe (`platform/estate/libexec/critical-probe.py`) fails a door that answers
without all three tools: degraded is red, never a quiet pass.

---

## J2 -- "Do not merely raise an error or fail a gate when no free tier exists; fix the root cause."

**Incident.** A chain whose tail is a paid lane, or a lane with no bounded cost, is a limit
waiting to be hit; and the estate's own guard only noticed after the bill. The founder's
instruction was not "make the gate red" -- it was to make the *root* go away.

**Rule.** A gate that fails is a report, not a repair. When a guard trips, the work is to find
the class of thing that produced it and remove the class -- not to add a second error message,
and not to leave a standing red for someone else to inherit. A failure the platform could have
predicted must never reach a caller: measure it before the founder finds it.

**Trigger.** Any gate, guard or probe you are about to make stricter, or any red you inherited.

**Enforcement.** The **spend-bound** probe reads the estate's own rendered router configs and
fails a chain with no zero-cost floor, no hard ceiling, or a paid tail -- before a call is made,
not after. The registry judge refuses an entry that cannot be measured, so a guard cannot be
added that only complains.

---

## J3 -- Alive is not healthy.

**Incident (measured 2026-10-30).** The disk guardian was loaded, ticking every cycle, and on
its last step freed **-2 MB** (2263 -> 2261 MB free, against a 2500 MB target, volume 98% full).
It was green on liveness and doing nothing for the job it exists to do. The same shape: a
router that answers `/v1/models` with 161 models while four of the lanes the estate declares
(`cerebras`, `glm`, `nvidia`, `sambanova`) are not served at all.

**Rule.** Measure the **goal**, not the process. A liveness probe answers "is it running?"; a
goal probe answers "is it doing its job?". A watcher that cannot say the second is a heartbeat
for nothing -- and a green one is worse than a red one, because it spends the founder's
attention.

**Trigger.** You are about to call something healthy because a process, socket or file is there.

**Enforcement.** Every entry in `catalog/critical-functions.json` carries a **goal** where one
exists, and the spine grades the goal first: alive but missing its goal is FAILING. The
probes write *why* they went red to `~/.estate/heartbeats/<name>.json` -- the evidence, not
the verdict alone.

---

## J4 -- Unknown is refuse.

**Incident.** The estate's own law records the class: gates that fail open ("cannot judge" ->
pass) let ruff errors through the pre-push gate (#7434), and a gate that cannot fail is not a
gate. A probe that cannot measure its subject is the same defect wearing a sensor.

**Rule.** An unmeasurable thing is not a healthy thing. If the probe cannot read the subject,
the subject's state is **unknown**, and unknown is red -- BLIND, never PASS. The same applies
to a registry entry that names a probe type the spine does not implement: it is not "watched
soon", it is watched by nothing, and the founder must not read "watched" there.

**Trigger.** You are tempted to return "ok" because the check could not run.

**Enforcement.** The spine has three verdicts -- PASS, FAIL, BLIND -- and BLIND does not pass.
The command probes exit non-zero when they cannot measure. The registry judge
(`tests/test_critical_functions_registry.py`) refuses a type the spine cannot measure, and
ships fixtures proving it can fail.

---

## J5 -- Founder concerns first, in the data and in the weight.

**Incident.** The critical-watch spine watched three functions while the founder's own stressed
surfaces -- the memory plane, the router's lanes, the cost bound, the cluster substrate -- were
watched by nothing, and two of them were down at the time. The three that were watched were
the three that were easiest to watch.

**Rule.** Priority is a property of the **data**, not of a reader's memory. The registry's
order *is* the priority order the estate walks, and the weight *is* how the one metric counts
a founder's surface against the rest. When the founder asks what matters most, the answer is
an ordering in a file that the machine reads, not a judgement made from memory at 3 a.m.

**Trigger.** You are choosing what to watch, what to fix first, or what to wake an agent for.

**Enforcement.** `catalog/critical-functions.json`: founder-critical entries come first and
carry weight 2; the judge refuses a registry that puts one below a non-founder entry. The
spine raises the first failing entry's incident first.

---

## J6 -- "Move idle agents onto the highest-value work for the estate."

**Incident.** The estate has agents idle and work that matters; the link between them was a
judgement call with no measurement behind it, so the highest-value work was whichever task the
nearest agent happened to see.

**Rule.** The work order and the health number are the same thing. The failing entries, in
registry order, are the estate's highest-value work -- founder-first -- and the first of them is
where an idle agent belongs. An agent that is woken onto a task must be able to say, in one
line, that it is the head of the queue.

**Trigger.** An agent is free, or you are deciding what to do next.

**Enforcement.** `critical-probe.py estate-health` prints the number and the queue; the spine
raises a structured incident for the first failing entry and invokes the agent with the
incident attached. Each entry carries a structured remedy -- runner, repo, budget, task -- so the
woken agent never has to invent the next step.

---

## J7 -- "We need to know this when our underlying assumptions break."

**Incident.** The estate runs its own code from a runtime tree. When that tree is not on main,
the estate is running code nobody landed, and every proof it produces is about the wrong
binary -- while every green light still looks green.

**Rule.** Measure the assumptions, not only the functions. An assumption the estate depends on
and has never checked is a belief, and beliefs fail silently. If the estate's behaviour
depends on something being true, that something gets a probe, a heartbeat and an alert.

**Trigger.** You find yourself writing "we assume" anywhere.

**Enforcement.** The registry carries **assumptions** beside functions (today:
`runtime-tree-on-main`), measured by the same spine, with the same three verdicts.

---

## J8 -- The founder measures by hand; make the machine do it.

**Incident.** The founder has been measuring lane outcomes by hand because the estate's own
telemetry did not answer the question (issue #7503: "lane-submit 53% not-ok in 30d, no
ask-to-landed telemetry; founder measures by hand"). A metric only the founder can produce is
a metric that is read once and never trusted.

**Rule.** Every claim the estate makes carries machine output: the command, its exit status,
the line it printed, and a hash anyone can re-derive. If a number only a human can produce,
it is not a metric yet -- it is a chore, and chores are what the estate exists to remove.

**Trigger.** You are about to report a number, a status, or a "done".

**Enforcement.** `~/.estate/heartbeats/<name>.json` holds each probe's receipt -- the exact
line the subject printed, with its exit status. The metric writes
`~/.estate/heartbeats/estate-health.json`. The spine's log is the production line.

---

## The judgement test

Six questions, asked before you call anything done:

1. **Is this the same contract as before?** (J1) Did the service lose a capability, or only
   its route?
2. **What did I fix -- the instance or the class?** (J2, J3)
3. **Can this gate actually fail, and has it failed on a known-bad input?** (J4)
4. **Is the founder's surface weighted above the rest?** (J5)
5. **Is an idle agent's next task the head of the queue?** (J6)
6. **What did the machine print, and can anyone else re-run it?** (J8)

A "no" or an "I cannot point at the evidence" is the work, not the answer.
