# One workflow for every harness

`AGENTS.md` is the single workflow. `render.py` copies it, verbatim and stamped with its sha256,
into the instruction file each harness loads. `render.py check` exits 1 on any copy that is
MISSING or has DRIFTed, and names the harness.

    python3 platform/estate/harness/render.py check  --source AGENTS.md --home ~
    python3 platform/estate/harness/render.py render --source AGENTS.md --home ~

| harness     | instruction file               | status of the path                          |
|-------------|--------------------------------|---------------------------------------------|
| claude-code | `~/.claude/CLAUDE.md`          | documented global file                      |
| codex       | `~/.codex/AGENTS.md`           | documented global file                      |
| opencode    | `~/.config/opencode/AGENTS.md` | documented global file                      |
| pi          | `~/.pi/AGENTS.md`              | **declared, not yet confirmed against pi**  |
| kimi        | `~/.kimi/AGENTS.md`            | **declared, not yet confirmed against kimi**|

## What this does not prove

`check` proves a file matches the source. It does not prove the harness reads that file. Until a
live session per harness shows the workflow in its context, pi and kimi are unproven.

## Not done in this lane

- No installer: rendering into `~/.claude/CLAUDE.md` would replace a hand-written file, so the
  installer must back it up first.
- No wiring into CI or a scheduled job. On 2026-10-30 `check` on the real machine reports
  MISSING for all five.
- Never edit a rendered copy. Change `AGENTS.md` and re-render.
