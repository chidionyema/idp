# How an agent's change reaches main

One loop, four doors. Read this once; it is the whole of it.

```
  you have a change
        |
        v
  bin/claim-open --title "..."        opens/claims the ticket and proves claim-gate green
        |
        v
  commit                              pre-commit refuses: unformatted Python, ruff errors,
        |                             tsc errors, shellcheck, yamllint. Fix, re-stage, commit.
        v
  git push origin HEAD:lane/<name>    the lane. Never main, never a PR you raised yourself.
        |
        v
  greenlane                          stacks lanes onto current main, runs the required checks on
        |                             that exact sha, fast-forwards main when green
        v
  red?  bin/lane-error <sha>          the failing job and its annotation lines, one call
        |                             (also posted as a commit comment and an open ticket)
        v
  fix, push again                     same lane, same claim
```

## The four doors

| door | what it is for |
|---|---|
| `bin/claim-open` | say what you are touching before you touch it; derives the paths from your diff |
| `bin/lane-error <sha>` | the exact reason a lane is red, without API archaeology |
| `bin/lane-red` | the red lanes right now; `estate-brief` prints it at session start |
| `bin/bot-commit` workflow | commit from a cloud runner without a laptop: dispatch `bot-commit` with branch, path, content, message |

## What refuses you, and the one move that fixes it

| refusal | fix |
|---|---|
| `pre-commit: ruff format failed` | run the printed command, re-stage |
| `pre-commit: REFUSED -- ruff is not installed` | `bin/idp-install-deps` |
| `claim-gate: N file(s) outside every claim's paths` | the printed `bin/claim-open --issue <n>` line |
| `language-gate: new Python file with no documented reason` | write it in Rust, or add `Language-Exception: <path> -- <reason>` to the commit message |
| `guarded-paths: HEAD is unsigned` | you committed with hooks off; commit again normally, or use the `bot-commit` workflow |
| `greenlane: does not rebase onto main` | rebuild your commit on current main; the engine will not merge a stale base |

## What never happens, and never needs to

- **You never push main.** The ruleset refuses non-App writers, and the greenlane is the only door.
- **You never raise a PR.** The lane raises it and lands the tested sha.
- **You never guess a failure.** The annotation, the commit comment and the ticket carry the line that failed.
- **You never wait in a poll loop.** Push, then read `bin/lane-red` or the ticket; the answer arrives.
