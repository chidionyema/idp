# Demo: the session engine names no vendor

Run the gate on the repository and on the fixture that branches on a runner name in `workflow.py`.

```
$ bin/vendor-agnostic-gate
vendor-agnostic-gate: 0 vendor-name line(s) outside the runner registry
$ VENDOR_AGNOSTIC_ROOT=tests/fixtures/vendor-agnostic/bad bin/vendor-agnostic-gate
sovereign/engine/workflow.py:5: if runner == "claude":
sovereign/engine/workflow.py:6: return "special-cased for anthropic's CLI"
vendor-agnostic-gate: 2 vendor-name line(s) outside the runner registry
$ VENDOR_AGNOSTIC_ROOT=tests/fixtures/vendor-agnostic/good bin/vendor-agnostic-gate
vendor-agnostic-gate: 0 vendor-name line(s) outside the runner registry
```

The first run is the state of `sovereign/engine` today: zero lines name Claude or Anthropic
outside `runners.py`, the one file `sovereign/CONTRACT.md:41` allows to (the registry) and
any file under an `adapters/` directory (a real vendor CLI wrapper, kept out of the engine's
own files). The second run shows the gate refusing `workflow.py` the moment it branches on a
runner's name instead of treating it as an opaque string. The third run shows the same tree
with the branch removed passes clean, and the good fixture also carries a `runners.py` with a
vendor name in it and an `adapters/claude_adapter.py` -- both pass, proving the two
exemptions are real and not just "nothing was scanned." `bin/idp-ci` runs this gate on every
pull request, so a vendor name cannot creep back into the engine without a red check.
