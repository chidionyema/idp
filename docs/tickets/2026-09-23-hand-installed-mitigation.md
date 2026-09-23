# Hand-installed mitigation — the eight items, and how each stops recurring

**Status:** open
**Opened:** 2026-09-23
**Laws:** LAW 0 (one of each layer), LAW 38, THE EMPIRICAL PROOF RULE
**Companion:** `2026-09-23-host-provisioning-drift-metric.md` (the layer that makes this visible)
**Depends on:** `bin/idp-install-deps`, `bin/serve-fleetview`, `platform/executor/daemon.py`

---

## What this is

The metric ticket measures drift. This one **clears the debt** and closes the path each item
arrived by, so it cannot recur. Every row below is a thing that exists on the founder's Mac today
because it was installed by hand, and each gets two answers: the immediate fix, and the structural
fix that makes the hand-install impossible rather than merely discouraged.

## The eight

| # | Item | Immediate fix | Structural fix (why it cannot recur) |
|---|---|---|---|
| 1 | Kokoro models, hand-`curl`ed | add the model set to the artifact rail (the estate's OCI model path already exists) and have the service pull by digest | a declared artifact with a hash, not a URL in a shell history. The service already refuses to start half-configured (`config_guard.py`) — extend it to the models it needs |
| 2 | `kokoro-onnx` undeclared | add to the declared dependency set the server interpreter installs | **the voice requirement was in no requirements file.** Declaration is the fix; the metric makes the absence visible before a person discovers it by speaking |
| 3 | `jsonschema` undeclared | add to `sovereign/requirements.txt` | it is a RUNTIME import of `voice_media.py`. An undeclared runtime import is the exact class this repo's own `cryptography`/`z3-solver` comments record being caught by a CI run |
| 4 | `ruff` undeclared | add to `bin/idp-install-deps`'s tool set at a pinned version | **the gate's own checker is not installed by the gate's own installer.** Every agent reported "ruff not installed" and was right for their interpreter |
| 5 | `/usr/local/bin/timeout` hand-dropped | make the executor's timeout wrapper a declared dependency of the daemon, installed by the bootstrap | a root-owned, unversioned binary the daemon requires and nothing installs. The daemon should name it and refuse loudly, or ship its own |
| 6 | `helm` shadowed by Rancher Desktop | PATH precedence: pinned `estate-tools` before `~/.rd/bin` | the metric's `shadowed_total` counter makes the second copy visible; today it is silent |
| 7 | `conftest` shadowed by `~/.local/bin` | same PATH fix | same counter |
| 8 | `kokoro-v1.0.int8.onnx` dead weight | delete; the loader wants fp32 and the int8 graph has no kernel on this runtime (already documented in `engine.py`) | a declared model set has ONE entry per role, so a wrong variant is not merely unused, it is absent |

## Why this is urgent, honestly

Three of the eight (4, 3, 5) are load-bearing for something that **currently works on this machine
and would not on another**. That is the same shape as all four failures of 2026-09-23. The voice
pipeline was "working" in exactly this sense: correct on the founder's Mac, absent everywhere else.

## Acceptance

- Each row's structural fix is in place, or the row is explicitly declined with a reason.
- `bin/idp-install-deps` on a fresh host installs **every** item the gates and services need — the
  list at `#4` is the proof, since it is the tool that already claims to do this.
- No item requires a hand `pip`, `curl`, `brew` or `cp` to reach a working state.

## Non-goals

- Not a rewrite of the bootstrap. Each row is a declaration or a PATH ordering.
- Not a refusal. The preflight WARNS while the declaration and the bootstrap disagree, and only
  becomes a gate once a fresh host reaches green by the declared path alone.
