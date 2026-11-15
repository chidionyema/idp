# Gemini recovery — forensics inventory (OpenCode 1)

Role: OpenCode 1, Forensics & Recovery. Canonical issue `chidionyema/idp#7819`.
Claim: `agent=oc6-7c1a`, heartbeat `2026-11-15T22:33:10Z`, lease until `2026-11-15T23:33:10Z`.
This is a source inventory, not a recovery certification. Operational integration is NOT_RUN.

## Preserved source sets (measured on this host)

| source | evidence | integrity |
|---|---|---|
| `~/.estate/handover-20261111T1010Z/` | `SHA256SUMS` (42 entries), `BRANCHES.json`, `git-bundles/`, `patches/`, `receipts/`, `ins-00006/` | 41/42 payload `OK`; the 42nd is the manifest's own self-entry, which cannot match itself |
| `~/.estate/quarantine/codex-company-assets-20261111T1020Z/` | Codex session rollouts | present, read-only |
| `~/.estate/instructions/ledger.jsonl` | instruction records: rego x6, symbiont x13, investor x2, topological x60 | present |
| `~/.estate/plans/pi-1794337118269-ij3uzn4w.jsonl` | symbiont x3 | present |

## Branch reconciliation (`BRANCHES.json` vs the repos)

| branch | head | worktree on disk | bundle | verdict |
|---|---|---|---|---|
| `lane/dsh-output-continuity` | `d287a7818` | yes (`dsh-workspace-fix-20261111`) | present, **PARTIAL** (missing prerequisite `4fcdfd86`) | SOURCE PRESENT / BUNDLE PARTIAL |
| `lane/foreground-budget` | `1980abebe` | yes (`foreground-budget-fix-20261111`) | **none** | SOURCE PRESENT / NO BUNDLE |
| `lane/goal-progress-timeline` | `b2415b26c` | yes (`idp-tracker-deploy-20261111`, 6 dirty files) + `patches/idp-tracker-dirty.patch` | present, **PARTIAL** (missing prerequisite `471366be`) | SOURCE PRESENT / PARTIAL |
| `lane/memory-bridge-live-20261111` | `e2c102208c` | worktree path absent | present, **OK** against idp | BUNDLE RECOVERABLE |

`git bundle verify` against idp: `memory-bridge-live` is okay; the other two name a prerequisite
commit idp does not have, so they need their base repository before they are complete.

## Workstreams (founder's six)

| workstream | evidence found | status |
|---|---|---|
| BEAST / Mini-NASA | instruction ledger (topological x60) and #7819 comment describing 18 files and routes; no source tree found on this host in this pass | SOURCE UNKNOWN |
| Genesis control plane | #7819 comment (fleet, Legion, FLOW watchdog, claim gate, voice, ledger); no source tree found | SOURCE UNKNOWN |
| Genesis Symbiont / ICP | `handover-20261111T1010Z/ins-00006/` MV3 extension, `functions/`, `migrations/`, tests, docs, debug pack, `tools/install-into-repo.sh` | SOURCE PRESENT |
| Genesis Kernel | no source tree found | SOURCE UNKNOWN |
| OMEGA / BEAST governance | instruction ledger (rego x6); no source tree found | SOURCE UNKNOWN |
| Investor / commercial surfaces | instruction ledger (investor x2); no source tree found | SOURCE UNKNOWN |

## Preserved failures

- The recovered Gemini Rust middleware candidate quarantined for a signature defect (it verified a
  claimed body hash without binding the signature to the request body) is preserved as a known
  failure, not deployed. Recovery must keep both the implementation and the defect record.

## Not inspected (explicit unknown)

- Private Gemini conversation history and AI Studio workspaces: not accessible in this pass. They
  are recorded as UNKNOWN, not "missing".

## Harvesting gap

The recovery is repeatable: `bin/gemini-intake` copies a source tree into quarantine, writes
`MANIFEST.json` and `SHA256SUMS`, never overwrites a differing file, and is idempotent. Covered by
`tests/test_gemini_intake.py`.
