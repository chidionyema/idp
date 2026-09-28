# Onboarding — `vm-shared-path`

`bin/vm-shared-path PATH...` exits 0 when every path is under a tree the container VM shares, and exits 2 naming the first that is not. It exists so a compose bind mount never silently becomes an empty directory inside a container (see the demo for the incident).

## Once

Nothing to install. The script is plain bash and reads `~/.colima/default/colima.yaml` if present.

## Every time

1. Run `bin/mcp-up`, `bin/litellm-up` and `bin/langfuse-up` from a checkout under your home directory. A git worktree under `/tmp` or `/private/tmp` is refused before compose starts.
2. If you keep repositories somewhere else, add that directory to `mounts:` in `~/.colima/default/colima.yaml` and restart colima. The guard reads those entries and permits them.
3. To point a mount somewhere specific, use the existing overrides (`ESTATE_STATE_MD_HOST_PATH`, `ESTATE_CATALOG_HOST_PATH`); the guard checks the override value, not the default.

## Testing your own script

Set `VM_SHARED_ROOTS` to a colon-separated list of roots to grade against, instead of the real colima configuration:

```
VM_SHARED_ROOTS="$HOME" bin/vm-shared-path "$HOME/x" /private/tmp/y
```

## When it says FAIL

Move the checkout, or add its root to colima's `mounts:`. Do not bypass the guard: the failure it prevents is a shared service restart-looping with a healthy-looking host.
