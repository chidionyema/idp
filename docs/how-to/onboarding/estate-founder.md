# Onboarding: reading and extending the founder's god's view

The founder's three standing questions — what shipped, what changed for me, what is stuck — are answered by `docs/FOUNDER.md`, a page generated from GitHub by `bin/estate-founder`. Nobody types it. If the founder asks one of those questions in a session, the answer is the link to this page, not a paragraph.

## As the founder

Open the portal, catalogue, **Founder: what shipped, what changed for you, what is stuck**. The `Taken:` stamp at the top is when GitHub was read; the cron renders at 01:58, 07:58, 13:58 and 19:58 UTC. Anything under **What is stuck** that says `you` in the owner column is waiting on a word from you and nothing else.

## As a session

Every merged pull request must carry a `Use:` line in its body when it changes something the founder touches (the handoff shape in `~/AGENTS.md`). That line is what the page shows him; a pull request without one shows him nothing, deliberately. Write `Use: nothing` when that is honest.

A checkpoint that waits on the founder says so in its text with one of the words the page looks for: confirm, receipt, opens, closes, replies, picks, decision. That is how the checkpoint reaches his stuck list.

## Extending it

The page is one Python file with no dependencies beyond `gh`. Inputs are three JSON documents (merged pull requests, open pull requests, crew issues); the test in `tests/test_incident_crew412_founder_page_answers_from_github_not_memory.py` feeds them from files, so a change to a section is proved offline. Repository trailers are read with `git log origin/main` in the checkout beside this one (`ESTATE_CODE`); a repository not checked out is reported BLIND, never silently zero.

Window and review threshold are `ESTATE_FOUNDER_WINDOW_H` (24) and `ESTATE_FOUNDER_REVIEW_H` (2).
