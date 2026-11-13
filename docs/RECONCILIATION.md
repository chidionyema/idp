# 48-hour reconciliation — assets, cage, export, yield

Date: 2026-11-12. Corrects the gross yield figure.

## 1. Assets handed over

| Asset | Where | State |
|---|---|---|
| Cage + broker + Telegram adapter | ~/.estate/cage | 19/19 caged tests; same-user; not commercial |
| genesis-2100-complete-export (1).tar.gz | ~/Downloads, 9.9 MB, 203 files | **not integrated**; separate source tree |
| Projector | argon/src + #projector | 19/19; fixture replay; live |
| Founder Control | /founder | live, public, Telegram pinned |
| YIELD/1 + founder gate + escalation | ~/.estate/bin, bus | enforced locally |
| Release v2026.11.12.3 | GitHub | gate 8/8; install + rollback verified |
| Executor sort exemption | lane/executor-sort-diagnostic 911f6a9 | pushed; Greenlane blocked by ci-success |

## 2. Yield correction

| Measure | Value |
|---|---:|
| Gross ledger | 262.37 |
| Verified (E3) | 232.76 |
| Unverified (U) | 29.61 |
| Duplicate reports | 6 extra across 5 work items |
| **Unique E3 yield** | **162.73** |

The gross number counts re-runs and unverified rows. Real unique, verified output is **162.73**.
The 99.64 difference is repetition and U, not new work.

Duplicates:

- projector test argon ×2
- cage demo ×2
- opencode test idp ×2
- docs control-plane link ×2
- docs next-session pack ×3

## 3. The export

genesis-2100-complete-export (1).tar.gz: 9.9 MB, 203 files, dated 2026-11-12 12:45.
It contains a full src tree (App.tsx, engine, optimusAndReactor). It is **not merged, not tested, and
not the source of the running surface**. Until it is reconciled against argon/src, it is a parallel
copy — the split brain in artifact form.

## 4. Cage status

Real: token, sandbox, 19/19 projector tests inside the cage, single-use, epoch revoke.
Not real: OS-user separation, remote key custody, hard hooks for Codex/Claude.
Commercial readiness: partial.

## 5. Why yield went backwards

1. Re-runs counted as new yield (6 duplicates).
2. U verdicts counted in the total (29.61).
3. The export adds a parallel tree without reconciliation, so work appears done twice.
4. Stale proof and registry inflate confidence.

## 6. Corrected position

Verified unique yield: **162.73**.
Delivered: cage prototype, projector, founder surface, YIELD gate, release v3, executor fix lane.
Not delivered: export integration, main merge, Optimus yield, durable DNS, OS-user cage.

Use 162.73 in any commercial statement. Do not quote 262.37.
