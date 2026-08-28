# sovereign/attach — estate attach (cp21), owner: builder D
`sb attach <path>` mounts any repo/dir/workspace: git-tracked nodes (else a
filesystem walk minus `attach.ignored_dirnames`), a sha256 root hash over
canonical relpaths + content hashes, two receipts in the estate's own
`.estate/receipts.jsonl` chain (`estate_mounted`, `policy_inherited`), a
conservative AGENTS.md scaffolded into `.estate/` (never the repo root
unless `--write-policy`). `sb status` / `sb halt --all --by X [--signed]`
read `$ESTATE_HOME/registry.jsonl` and `engine.client.list_sessions()`.

Run: `bin/sb attach <path> --json` / `bin/sb status` / `bin/sb halt --all --by founder`
Prove: `sovereign/.venv/bin/python -m unittest sovereign.attach.test_attach -v`

## Line A adds to `sovereign/cli.py`'s plug-in tuple in `main()`
```python
for modname in ("sovereign.otto.cli", "sovereign.cockpit.cli", "sovereign.attach.cli"):
```
(`sovereign.trust` has no CLI subcommands of its own — nothing to add for it.)

## Two blocks A adds to `sovereign/config.py` — see sovereign/trust/README.md,
same two blocks (TRUST_KEYS and ATTACH_KEYS are merged together there).

## Five-line change A makes to `cmd_start`/the `start` subparser for `--estate`
```python
p.add_argument("--estate", default=None, help="attach root; repo defaults to it, receipts chain under its .estate/")
# in cmd_start, before building `res`:
if args.estate:
    from sovereign.attach import core as attach_core
    args.repo = args.repo or args.estate
    # receipts for this session's steps should land under
    # attach_core.estate_dir_for(Path(args.estate)) / "receipts.jsonl" --
    # engine/workflow.py's append-receipt activity needs a `path` param
    # (currently always config.SB_RECEIPTS) to honor this; today
    # `core.append_estate_receipt` only covers attach's own two lines.
```

**Residual:** node counting hashes file *content* (sha256), not git's own
object SHAs — portable across OSes/git configs, but two clones with
different `core.autocrlf` settings will still hash identically only if
their working-tree bytes match (they do, by design of that git setting).
`estate_dir_for(..., mode="global")` collides if two different absolute
paths ever sha256 to the same 12 hex chars (astronomically unlikely;
`attach.path_hash_hex_len` raises this if it ever matters).
