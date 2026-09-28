# Demo — `vm-shared-path`

`bin/vm-shared-path` refuses a compose bind-mount source the container VM cannot see. colima shares only your home directory (plus any `mounts:` entries in `~/.colima/default/colima.yaml`) with its VM. A source outside that tree does not fail: the VM hands the container an **empty directory**, so a file mount becomes "Is a directory" and a database becomes "unable to open database file".

## The incident it comes from

2026-08-25, 05:02Z to 05:04Z: `bin/mcp-up` was run from a git worktree under `/private/tmp`. Every checkout-relative mount arrived empty. agentgateway logged `failed to read from file /config/agentgateway.yaml: Is a directory`, datasette logged `sqlite3.OperationalError: unable to open database file`, and the shared estate MCP stack restart-looped until it was rebuilt from `~/dev/code/idp`. The host-side `[ -r file ]` checks passed the whole time, because the files exist on the host.

## Run it

```
$ bin/vm-shared-path ~/dev/code/idp ; echo rc=$?
rc=0

$ bin/vm-shared-path /private/tmp/somewhere ; echo rc=$?
FAIL  /private/tmp/somewhere resolves to /private/tmp/somewhere, outside the VM-shared tree (/Users/you); the container would see an empty directory
rc=2
```

`bin/mcp-up`, `bin/litellm-up` and `bin/langfuse-up` call it before `compose up`, so the refusal above is what you see when you run any of them from a checkout outside your home directory.

## Proof both ways

`bin/idp-ci` row `vmmount` runs the guard on a path under the shared root (must permit) and on `/private/tmp` (must refuse) in the same run:

```
ok    vmmount  vm-shared-path permits a path under the shared root and refuses one outside it
```

## Residual

The guard reads the `default` colima profile only. A Docker engine that is not colima is graded by the same home-directory rule, which is stricter than that engine needs.
