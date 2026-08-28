# Demo: the founder's god's view

Founder, 2026-08-28: "where is the founders gods view". This is the page that answers, and this is how to watch it answer.

## Run it

```
bin/estate-founder
```

Output: one line, `estate-founder: N merged, M unreviewed, K on the founder -> docs/FOUNDER.md`. The page it wrote has three sections.

**The bar** — how many pull requests merged in the last 24 hours, across how many repositories, how many of them carried a `Use:` line, how many open pull requests have no `REVIEW:` verdict after two hours, and how many checkpoints wait on the founder himself.

**What changed for you** — only the `Use:` lines. A merged pull request with no `Use:` line, or one that says `Use: nothing`, changed nothing the founder touches and does not appear here.

**What is stuck** — open pull requests on repositories that shipped this window with no verdict, oldest first, and every open checkpoint whose text names the founder (confirm, receipt, opens, closes, replies, picks, decision).

**What shipped** — every merged pull request, by repository, with the crew issue it names and the model and session from the merge commit's trailers when the repository is checked out beside this one.

## Prove it is fresh

```
bin/estate-founder --check
```

Exit 1 with `FAIL  estate-founder` when the page on disk no longer matches GitHub; exit 0 after a render. The catalog-render cron runs the render four times a day and commits the page through the same pull request as `docs/NEXT.md`, so the founder reads it in the portal under **Founder** without asking anybody.

## Where it lives

- GitHub: `docs/FOUNDER.md` on main.
- Portal: the `founder-gods-view` Component in the founder catalogue links the TechDocs page.
