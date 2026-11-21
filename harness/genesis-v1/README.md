# genesis-harness-v1 — Slice 1

The portable, stateless coding harness: one OCI image, five deterministic tools, no ambient
credentials, and a model bound to a **logical role** rather than to a vendor model id. It runs
the same bytes on Lane 1 (Cloudflare Containers), Lane 2 (OCI ARM) and Lane 3 (Actions).

This crate is **never built on a laptop** (AGENTS.md §2). `bin/idp-ci` rung `1d.6` compiles it in
Actions for every change under `harness/`, and that is the only place its tests run.

## The five tools

One JSON envelope in on stdin, one `StepReceipt.v1` out:

```json
{"schema_version": "InstructionEnvelope.v1", "instruction_id": "INS-1",
 "parent_instruction_id": null, "role": "coder", "target_repo": "idp",
 "worktree_root": "/workspace", "ttl_secs": 300, "max_output_bytes": 4096,
 "tool_call": {"tool": "file_read_bounded",
               "args": {"rel_path": "src/main.rs", "start_line": 1, "end_line": 40}}}
```

| tool | what it is allowed to do |
|---|---|
| `repo_search` | walks the worktree for a literal, returns locations and signatures, never file bodies |
| `file_read_bounded` | one bounded line slice plus the file's `sha256`, which every later patch to it must present |
| `patch_apply_anchored` | exact search-and-replace, pre-hash-checked, so line drift is refused instead of guessed |
| `exec_scoped` | runs a **verb** declared in `.genesis/allowlist.json`, nothing else |
| `diff_export_candidate` | seals the loop: `git diff` against the base, emitted as an unsigned candidate |

## The exec door

`exec_scoped` takes a verb name, not a program. The verb resolves through the repository's own
manifest:

```json
{"check": ["bin/pre-push-wall.py", "--fast"], "unit_test": ["cargo", "test"]}
```

An undeclared verb is refused, arguments smuggled onto a declared verb are refused, and a missing
or unreadable manifest is refused — a missing contract is not a licence. `tests/allowlist_tests.rs`
holds one falsifier per refusal.

## Mechanically refused

`PROTECTED_PATH_PREFIXES` is write-blocked inside the dispatcher before any hash is considered:
`.github/workflows/`, `cage/`, `certifier/`, `features/`, `tests/acceptance/`. The acceptance
suite that grades this loop is not writable by the loop.

Output is clipped to `max_output_bytes` (clamped 512..32768) and `ttl_secs` is bounded by the
caller, so a runaway turn costs a bounded amount of the founder's money and time.
