# Codex Desktop forensic extraction - 2026-11-10 / 2026-11-11 GMT

Source: Codex Desktop rollouts (quarantined Codex home, `sessions/2026/11/09` and
`sessions/2026/11/11`), scoped by record timestamp to
[2026-11-10T00:00:00Z, 2026-11-12T00:00:00Z).

| file | what it is |
|---|---|
| `manifest.json` / `manifest.csv` | 358 recovered paths with recoverability, ops, sha256, bytes, stream, in_window, at_risk |
| `verify.json` / `verify.md` | the disk falsifier: SAFE-COMMITTED, ON-DISK-UNCOMMITTED, ON-DISK-DIFFERS, MISSING-RESTORABLE, MISSING-PARTIAL, MISSING-UNRECOVERABLE |
| `environments.json` | every Codex session: model, provider, CLI version, cwd, roots, approval/sandbox policy, parent thread, records, tokens |
| `sessions.json` | per-session summary |
| `conversation/*.jsonl` | the full normalised conversation stream per session (user / assistant / developer), ordered by (timestamp, ordinal) |
| `commands_ledger.jsonl` | every command and tool call, deduplicated by identity |
| `codex_reconstruction.json` | the producer-diff oracle: per path, the reconstructed content, base source and diff head |
| `codex_object_store.json` | the independent thread-history projection (a cross-check, not the transcript of record) |
| `recovered_bodies.jsonl` | the recovered file bodies, byte-exact, base64, each with its sha256 |

Restore a body: `base64 -d` the `content_b64` of its line and write it to `path`.
Only write a path that does not already exist; where the disk differs, the disk is newer.
