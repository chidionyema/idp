# Mission evidence packet -- INS-00011 (Legion real worker canary, idp #7932)

**What this is.** The evidence for ONE dispatched cloud mission, read from the canonical state
that mission produced. Nothing here is a promise or a plan: every line names the source it was
read from, and the receipt marks what is NOT yet true as NOT VERIFIED.

- instruction: **#7932** -- https://github.com/chidionyema/idp/issues/7932
- run: **[43074179589](https://github.com/chidionyema/idp/actions/runs/43074179589)**
  (workflow `agent-sandbox.yml`, run number 134, event `issues`, hosted runner
  `GitHub Actions 1000823182`, job `agent`)
- source SHA the worker started from: **`0a4abe6a4bcba03e94fc98afa25e45f8c9046171`**
- this runner's own env: harness `gemini`, provider actually running
  **`minimax`**, `LEGION_FAILOVER=1`
- read at: `2026-11-11T18:22:32Z`
- files this change touches (the claim of record is posted by the run's own submit step, with
  these paths):
  - `backstage/plugins/fleetview-backend/src/fleetview_backend/agent_jobs.py`
  - `backstage/plugins/fleetview-backend/src/fleetview_backend/routes.py`
  - `backstage/plugins/fleetview-backend/src/fleetview_backend/serve.py`
  - `backstage/plugins/fleetview-backend/schemas/mission-receipt-v1.json`
  - `backstage/plugins/fleetview-backend/tests/test_mission_receipt.py`
  - `backstage/plugins/fleetview-backend/tests/test_agent_jobs_truthful_status.py`
  - `tests/test_fleet_agent_jobs.py`
  - `docs/evidence/2026-11-11-ins-00011-mission-receipt.md`

## The provider that ACTUALLY ran

The run title says `agent (gemini)`: that is what was REQUESTED. The provider that ran was
**MiniMax** (`minimax` in this runner's own environment), after Gemini failed
with HTTP 429 -- quota exceeded on the free tier. The workflow classifies that failure as
`capacity-or-rate-limit` and prints its own marker in the agent job's log; the sealed artifact
of the failed Gemini attempt is where the raw provider answer lives. The receipt reads the
provider from that log marker when it can (the log needs `actions:read`), and when it cannot it
says `provider: null` with the reason, rather than repeating the title. That is why the
projection below carries `provider: null`: this packet was produced without the App token.

## The receipt, as the projection read it

```json
{
  "failure_class": null,
  "freshness": {
    "age_s": 1100.8,
    "read_at": "2026-11-11T18:22:30Z",
    "run_updated_at": "2026-11-11T18:04:10Z",
    "stale": true,
    "stale_after_s": 300.0
  },
  "harness": "gemini",
  "instruction_id": "7932",
  "instruction_url": "https://github.com/chidionyema/idp/issues/7932",
  "lane": {
    "branch": "lane/agent-gemini-43074179589",
    "commit": null,
    "files_changed": [],
    "url": "https://github.com/chidionyema/idp/tree/lane/agent-gemini-43074179589"
  },
  "model": {
    "failed_provider": null,
    "failure_class": null,
    "fallback": false,
    "name": null,
    "name_source": null,
    "provider": null,
    "provider_source": "not evidenced: the agent job's log could not be read, and the run title names the provider that was requested, not the one that ran"
  },
  "operational": {
    "code": "no-live-effect-evidence",
    "reason": "a landed lane is not a live effect; nothing in this projection evidences a running system, so nothing is claimed",
    "status": "NOT VERIFIED"
  },
  "provenance": {
    "claim_age_s": 40356.8,
    "claim_heartbeat": "2026-11-11T07:09:54Z",
    "claim_live": false,
    "claim_source": "CLAIM comment on the instruction issue",
    "claim_url": "https://github.com/chidionyema/idp/issues/7932#issuecomment-6789511902",
    "role": "gemini",
    "scope": [
      "backstage/plugins/fleetview-backend/src/fleetview_backend/__init__.py",
      "backstage/plugins/fleetview-backend/src/fleetview_backend/agent_jobs.py",
      "backstage/plugins/fleetview-backend/src/fleetview_backend/mission_receipt.py",
      "backstage/plugins/fleetview-backend/src/fleetview_backend/routes.py",
      "backstage/plugins/fleetview-backend/src/fleetview_backend/serve.py",
      "backstage/plugins/fleetview-backend/tests/test_mission_receipt.py",
      "tests/test_fleet_mission_receipt.py"
    ]
  },
  "recovery": [
    {
      "code": "in-flight",
      "next": {
        "action": "wait-for-the-run",
        "note": "",
        "target": "https://github.com/chidionyema/idp/actions/runs/43074179589"
      },
      "why": "the run is still working"
    }
  ],
  "run": {
    "conclusion": "",
    "created_at": "2026-11-11T18:04:06Z",
    "event": "issues",
    "head_sha": "0a4abe6a4bcba03e94fc98afa25e45f8c9046171",
    "run_id": 43074179589,
    "status": "in_progress",
    "triggered_by": "chidionyema",
    "updated_at": "2026-11-11T18:04:10Z",
    "url": "https://github.com/chidionyema/idp/actions/runs/43074179589"
  },
  "schema": "estate.mission-receipt/1",
  "source_sha": "0a4abe6a4bcba03e94fc98afa25e45f8c9046171",
  "sources": [
    {
      "kind": "actions_run",
      "url": "https://github.com/chidionyema/idp/actions/runs/43074179589"
    },
    {
      "kind": "actions_jobs",
      "url": "https://github.com/chidionyema/idp/actions/runs/43074179589"
    },
    {
      "kind": "agent_job_log",
      "url": "https://github.com/chidionyema/idp/actions/runs/43074179589"
    },
    {
      "kind": "instruction_issue",
      "url": "https://github.com/chidionyema/idp/issues/7932"
    }
  ],
  "stage": "started",
  "stage_evidence": {
    "live_effect": {
      "reason": "a merged lane is not a live effect; this projection reads no post-merge production receipt, so it does not claim one",
      "source": "none"
    },
    "queued": {
      "run_id": 43074179589,
      "source": "actions run"
    },
    "started": {
      "conclusion": null,
      "source": "actions job (agent)",
      "status": "in_progress"
    }
  },
  "stages": {
    "cif_passed": false,
    "greenlane_landed": false,
    "live_effect": false,
    "patch_produced": false,
    "queued": true,
    "started": true
  },
  "title": "LEGION #7932",
  "verification": {
    "codes": [
      "in-flight"
    ],
    "reasons": [
      "the run is still in progress: the worker has started and the result is not known yet"
    ],
    "scope": "the mission produced a real changed file, passed the epistemic firewall, and landed on main",
    "status": "NOT VERIFIED"
  }
}
```

## What the receipt says, in one line

`verification.status = NOT VERIFIED` -- the run is still in progress: the worker has started and the result is not known yet

That is the honest state of this mission **while the run was still working**. It is not a
failure: the run had started and had not finished. The ladder shows exactly which rungs were
open: `patch_produced`, `cif_passed`, `greenlane_landed` and `live_effect` were all still
false at read time. A merge would still not be a live effect: the projection reads no
post-merge production receipt, so `operational.status` stays `NOT VERIFIED` with the reason
`no-live-effect-evidence`.

## The negative control (the thing that must NOT read as success)

`tests/test_mission_receipt.py` proves, with the projection itself, that:

- a worker that never started -> `NOT VERIFIED`, code `worker-did-not-start`;
- a run that ended green having produced no changed file -> `NOT VERIFIED`, codes
  `no-output` and `conflict-run-succeeded-without-output`;
- a firewall that refused -> `NOT VERIFIED`, code `firewall-refused`;
- a run whose conclusion disagrees with its own agent job -> `NOT VERIFIED`, code
  `conflict-run-succeeded-agent-failed`;
- a branch that is not on main -> `NOT VERIFIED`, code `not-landed`;
- an unreadable provider log -> `provider: null`, never a guessed provider;
- a missing upstream, an empty credential and a mismatched instruction -> a refusal with a
  machine-readable code, never a fabricated receipt.

The tests fail on a naive implementation: replacing the verdict with `verified = True` turns 6
of the 20 red (measured on this tree, 2026-11-11).

## The capability this run produced

The projection is a READ-ONLY projection of GitHub's own records -- the run, its jobs, the agent
job's log, the lane branch and its commit, the pull request the Greenlane raised, and the
CLAIM comment on the instruction issue. It stores nothing, so a receipt can never disagree
with the run it describes, and a receipt that cannot be read says so instead of inventing a
state.

- `backstage/plugins/fleetview-backend/src/fleetview_backend/agent_jobs.py` -- the projection
  (`receipt`, `project_receipt`), the plain-text job-log read (`gh_text`), and two fixes to the
  job LIST that made it lie:
  1. the workflow's third job is named `submit-lane`, and the stage vocabulary never matched
     it, so a run that died in the submission step read as "The run ended failure." -- the
     run's own failing step was never read. The board's word for that step is unchanged
     ("open-pr"); what changed is that the real job is now found and its failing step named.
  2. the pull request belongs to the lane the sandbox pushes (`lane/agent-<harness>-<run>`;
     the Greenlane raises it with that lane as its head -- `greenlane/github.py`'s `_ensure_pr`
     posts `{"head": lane}`). The lookup still asked for the older `agent/<harness>-<run>`
     head, so a run that had landed answered "The run passed but no PR was found" -- a false
     failure. It is still ONE GitHub call per poll: the portal's token shares an hourly budget.
  Both are covered by `backstage/plugins/fleetview-backend/tests/test_agent_jobs_truthful_status.py`;
  the pull-request convention is covered by `tests/test_fleet_agent_jobs.py`, whose fakes named
  the old branch.
- `backstage/plugins/fleetview-backend/src/fleetview_backend/routes.py` and `.../serve.py` --
  the trusted server-side door: `GET /mission-receipt?run_id=...` (or `?instruction_id=...`).
  Argon reads this; the schema is published at
  `backstage/plugins/fleetview-backend/schemas/mission-receipt-v1.json`.
- `backstage/plugins/fleetview-backend/tests/test_mission_receipt.py` -- 20 tests, and
  `.../tests/test_agent_jobs_truthful_status.py` -- 2 tests.

Tests run in this runner: `22 passed, 1 warning in 0.39s`.

## Why the projection lives in an existing Python module, and not a new one

`bin/language-gate` (the founder's 2026-10-30 ruling) refuses a NEW Python file without a
`Language-Exception:` trailer in the commit message, and the agent-sandbox submit step builds a
FIXED commit message that cannot carry one. Measured on the previous run of this same mission
(run 42975234558): the worker produced the patch, the epistemic firewall passed it, and the
commit-msg hook refused it -- `FAIL language-gate: 1 new Python file(s) with no documented
reason`. The founder's correction on this issue says this work "belongs to the extant Python
FleetView service and the reason ... should be maintaining an existing Python runtime/route
contract rather than inventing a Rust sidecar". A MODIFIED existing Python file is not a new
language default being chosen -- the gate says so itself -- so the projection went into the
module that already owns the GitHub-hosted agent-run contract. No gate was weakened, no
exception was forged, and `.github/` and `.githooks/` were not touched.

## How the lane of THIS run is checked (measured, not assumed)

`git ls-files -s .githooks/` shows `.githooks/pre-push` at mode **100644** while
`.githooks/commit-msg` and `.githooks/pre-commit` are 100755, and git runs a hook only when it
is executable. The sandbox's submit step sets `core.hooksPath .githooks` and pushes, so the
commit-msg and pre-commit gates DO run for a cloud lane (that is where the previous run of this
mission died: `FAIL language-gate`) and the pre-push fast gate does NOT run for it. The lane
is therefore judged by the remote `claim-gate` in `ci-success` and by the Greenlane, which is
the check the estate intends for a pushed branch. This is recorded because it is measured
state of the estate's own door, not a licence: nothing in this change weakens a gate, and no
hook file was touched.

## The blocker on this packet, stated plainly

The agent job of `agent-sandbox` holds `contents: read` and no write token (`gh auth status`:
not logged in; no `GITHUB_TOKEN` in the environment), so **this worker cannot post to #7932 or
#7775**. The submit-lane step of the same run posts the CLAIM comment and the `Submitted
lane/...` comment on #7932 with the App token, and the Greenlane raises and lands the pull
request from the lane. The projection of THIS run, read after the lane exists, is one
`GET /mission-receipt?run_id=43074179589` away.

Until the lane is on main and a live effect can be evidenced, the mission is **NOT VERIFIED**.
That is the receipt's own verdict, not an opinion.
