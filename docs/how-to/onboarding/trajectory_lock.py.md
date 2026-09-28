# How to put the Trajectory Lock on a session

The lock stops cognitive drift: an agent told to add a button chases a React deprecation warning, a
broken test and a Node upgrade, and never adds the button. It works by refusing any action that does
not serve the plan the agent itself declared.

## The four mechanisms

**1. The bounded goal stack.** No work without a contract. Until `declare_plan` is called with a goal
and at least one sub-goal, every tool call is refused.

```python
lock.declare_plan("s1", goal="add a button to the settings page",
                  subgoals=[{"id": "goal_1", "text": "add the button component"}])
```

**2. Tool-to-goal binding.** Every action names the goal it serves. An action naming a goal that is
not on the plan, or naming none, is refused `403 Trajectory Drift`.

```python
lock.authorize("bash", {"command": "touch button.tsx"}, session_id="s1", target_goal_id="goal_1")
# {'allowed': True, ...}

lock.authorize("bash", {"command": "npm i -g node@20"}, session_id="s1", target_goal_id="goal_9")
# {'allowed': False, 'code': 403,
#  'reason': 'Trajectory Drift: goal_9 is not on this plan. Return to `goal_1`...'}
```

**3. The micro-budget kill switch.** The budget is **per sub-goal**, not per session — that is what
stops a loop from becoming a bill. At the ceiling the agent is halted and must choose.

```python
lock = TrajectoryLock(budget_per_goal=5)
# ... after 5 calls on goal_1:
# {'allowed': False, 'halt': True,
#  'reason': 'budget exhausted for goal_1 (5/5). You are spinning.
#             Execute revise_plan, or escalate to a human.'}
```

**4. Forced context pruning.** On three consecutive failed attempts the failed turns are erased and
the objective is re-injected at the **bottom** of the window — the freshest, most heavily weighted
position.

```python
out = lock.prune("s1", messages, goal="add a button to the settings page")
# {'pruned': True, 'removed': 3, 'messages': [...]}
# messages[-1] ends with:
#   [SYSTEM: Trajectory Drift Detected. Your recent attempts failed and have been erased to
#    clear your context. The original objective is: add a button to the settings page.
#    Re-evaluate your approach from first principles.]
```

## The fence between the two firewalls

Pruning edits the agent's memory, so it is the one mechanism that needs a fence. It may prune **only
turns recorded as failed** (`record_failure`), and it never removes a successful tool call, because
that is the evidence `bin/epistemic_firewall.py` grades a claim against. Both gates read one
transcript.

## Never blocked

`declare_plan`, `revise_plan` and `escalate` are always allowed, even from a halted state. A trapped
agent cannot report that it is trapped.

## Exit codes

| code | meaning |
|------|---------|
| 0 | the agent stayed inside its declared plan |
| 1 | drift — an action outside the plan, or work with no plan at all |
| 2 | BLIND — the transcript could not be read |

## What it will and will not do

**Does** bound the corridor: the agent cannot act outside the plan it declared, cannot loop past its
per-goal budget, and cannot lose the objective to its own error logs.

**Does not** choose the goal. A plan that is itself wrong is followed faithfully. The lock
guarantees the agent reaches the end of what it declared — not that what it declared was right.
