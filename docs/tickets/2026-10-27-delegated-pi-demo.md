# Delegated Pi demo — a real routed child, on the installed intent path

**2026-10-27 · issue #7310 · agent `pi-delegate-intent`**

This is the demonstration of the generic launch path
([design](2026-10-27-routed-pi-delegation.md)) on the **real** path: the installed intent
(`estate-execute delegate-build`), the installed dispatcher (`~/.estate/libexec/delegate-build.py`
after `estate-runtime-sync` staged it), the real estate router and a real Pi child.

## The task the child is given

The child is asked to write one file, and nothing else:

> Write `delegated-pi-demo.md` in the working directory. The first line must be exactly
> `DELEGATED BY PI`. The second line must be the model id you were routed on. Do not touch any
> other file. Do not search the repository.

The done-check is the reality, and it is checked by the dispatcher, not by the child:

```
head -1 delegated-pi-demo.md | grep -qx "DELEGATED BY PI" && sed -n 2p delegated-pi-demo.md | grep -q minimax_m27
```

The milestone is a file that must exist; the launcher verifies it itself.

## The packet

```json
{
  "task_id": "pi-demo-2026-10-27",
  "spec": "/private/tmp/pi-demo-spec.md",
  "worktree": "<a scratch worktree of idp main>",
  "identity": "pi-delegate-intent",
  "claim_issue": 7310,
  "harness": "pi",
  "provider": "estate",
  "model": "minimax_m27",
  "done_check": "head -1 delegated-pi-demo.md | grep -qx 'DELEGATED BY PI' && sed -n 2p delegated-pi-demo.md | grep -q minimax_m27",
  "milestones": [{"id": "artifact", "kind": "file", "path": "delegated-pi-demo.md"}],
  "budget": {"max_wall_s": 75, "max_attempts": 2, "max_steps": 32},
  "strategies": ["write the file directly", "write the file with the same content, then verify it"]
}
```

## The evidence

*(filled in from the measured run — the numbers below are read from
`~/.estate/delegate/pi-demo-2026-10-27/state.json`, not narrated)*

| Fact | Value |
|---|---|
| Intent run | `estate-execute delegate-build verb=launch …` |
| Exit status | *measured* |
| Route | *measured* (`provider/model` from the state) |
| Child identity | *measured* (`ESTATE_AGENT` bound to the declared identity) |
| Done-check | *measured* (rc) |
| Verified milestone | *measured* |
| Tokens | *measured* (unknown stays unknown) |
| Wall clock | *measured* |
| State | *measured* |

The child's own artifact, verbatim, and the raw event log path, follow.
