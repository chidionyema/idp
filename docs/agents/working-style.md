<!-- estate:routed-from AGENTS.md -- current law, not history. It is loaded on demand through the AGENTS.md route table instead of at Turn 1 (idp#8636). Moved verbatim. -->

## 10. Working style

- Only make the change that was asked for. No unsolicited refactoring.
- Do not guess. Search.
- Do not report a number you did not measure this turn.
- Do not grade a proxy — grade the thing itself.
- **Never use `grep -r`. Use `rg -l "pattern" path`** — `rg -l` finishes in <1s where
  `grep -r` times out at the 60s ceiling. A broad `grep -r` that hits the ceiling is a defect
  in the search, not evidence the thing is absent.

