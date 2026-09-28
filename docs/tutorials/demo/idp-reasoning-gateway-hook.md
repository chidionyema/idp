# Demo: `idp-reasoning-gateway-hook`

`idp-reasoning-gateway-hook` is the CLI entry point (a symlink to `bin/reasoning_gateway_hook.py`)
that `.claude/settings.json`'s `Stop` hook calls after every session. See
[`tutorials/demo/reasoning_gateway_hook.py.md`](reasoning_gateway_hook.py.md) for the full demo
with real command output -- this page exists only so the name a person actually types
(`idp-reasoning-gateway-hook`) has its own page, matching every other `idp-*` entry point in this
directory (`idp-rules`, `idp-probe-host`, and the rest).

```bash
python3 bin/idp-reasoning-gateway-hook --self-test
python3 bin/idp-reasoning-gateway-hook --report
```
