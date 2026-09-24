# Every pull request says what it cleans up

Founder ruling, 2026-08-31: every pull request must have a mandatory cleanup section. His words: "we never cleannup" and "i will defie what it says" — he defines the section's required content.

The day the ruling landed, 13 leftover work folders sat inside the idp checkout and 325 were registered against the repository. Work piles up because no pull request accounts for what it leaves behind.

## The rule

Every pull request body carries a `## Cleanup` section (a `Cleanup: ...` line also counts). It says what the change removes or leaves behind: work folders, branches, dead files, stored state. If there is nothing to clean, the section says `nothing to clean` — explicitly, never by omission.

The operating-model gate enforces presence (rule `cleanup_section` in `policy/operating_model.rego`). The founder defines what the section must say; until that definition lands, the gate refuses nothing about the content. A pull request opened before the rule existed is not refused.

## Why presence only

The founder said he will define the required content himself. Inventing required fields before his definition would put words in his mouth and refuse correct work — and a guard that refuses correct work is an outage, by the estate's own law on guardrails.
