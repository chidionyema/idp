# Fleet voice session control: requirements from the founder's own sessions

**Date:** 2026-09-29
**Surface:** `/fleet` (Backstage, http://localhost:3100/fleet), voice first
**Status:** requirements only, derived from measured data; no design proposed here

Every number below was measured on 2026-09-29 by scripts run over the raw files. Nothing is
estimated. Where a count depends on a keyword classifier, the classifier is described so it can be
rerun.

---

## (a) Evidence summary

### Sources and window

| Source | What was read | Window |
|---|---|---|
| `~/.claude/projects/*/*.jsonl` (top-level sessions, not subagents) | `type:"user"` entries with human text; tool results, system reminders, task notifications, command wrappers, meta and sidechain entries excluded; `<pasted_content>` bodies kept apart from the typed text | 2026-09-22T00:00Z to 2026-09-29T15:21Z |
| `~/.estate/efficiency-ledger.jsonl` | 17,334 non-`pre` records (`at, session, model, ok, latency_ms, ...`) | 2026-09-26T14:06Z to 2026-09-29T16:22Z (the file starts on the 26th) |
| `~/Library/Logs/litellm-local.log` | error-string counts. Lines carry no dates, so these are whole-file totals | whole file, 45.7 MB |
| `platform/estate/intents/*.yaml` and `fleetview_backend/voice_intents.py`, `signals.py`, `sessions.py` | what voice can trigger today | repo at `fix/mutation-workflows` |

### Headline numbers

- **1,473 founder-typed messages across 83 interactive Claude Code sessions** (entrypoint `cli`).
  The 127 `sdk-cli` sessions are automated probes ("Reply with exactly: ROUTER-PROBE-OK") and were excluded.
- Sessions touched per day: 22 Sep 17, 23 Sep 10, 25 Sep 2, 26 Sep 9, 27 Sep 8, **28 Sep 33**, 29 Sep 17
  (24 Sep had none).
- **Concurrency.** Sessions the founder typed into within the same 30-minute bucket: median 3, p90 5,
  max 10; 80 of 140 buckets had 3 or more. The ledger shows distinct sessions calling the router per
  10 minutes: median 4, p90 8, max 14.
- **Context switching.** 577 of 1,472 consecutive founder messages (39 %) went to a *different*
  session less than 5 minutes after the previous one.
- **Messages are terse.** Median typed length is 25 characters, and 561 messages (38 %) are 12
  characters or fewer. The most frequent messages were `ok` (145), `continue` (70), `hi` (34),
  `hello` (31), `/compact` (15), `huh` (14).

### Sessions stall on the router, not on the founder

- **416 API-error turns appeared in 76 of the 83 sessions.** By kind: ECONNREFUSED 157,
  `/login` or 401 121, request timeout 57, other 31, ECONNRESET or connection lost 23, rate limit 13,
  5xx 9, model missing 5.
- Errors rose through the week: 44, 30, 4, 27, 43, **101, 167** per day (22 Sep to 29 Sep).
- **311 founder messages (21 %) were the first reply after an API error.** The top replies were
  `ok` 71, `continue` 69, `hi`/`hello` 36. **102 of 107 "continue"-type messages followed an API
  error**; 3 followed ordinary agent text.
- Time from the error to the founder's resume message: median 82 s, p90 1,847 s (about 31 min),
  n = 284.
- Ledger `ok=false`: 2,888 of 17,334 (16.7 %). On 29 Sep it was **1,924 of 4,816 (40 %)**.
  Latency was p50 3.98 s and p90 15.6 s.
- Router log totals: `AuthenticationError` 9,381, `RateLimitError` 4,879, "You passed in model"
  3,312, `DeepseekException` 1,689, 64 router start-ups ("Uvicorn running").
- The ledger's `session` field is the Claude Code session UUID (for example `ebdbd82a…`, 2,677 calls),
  so router health can be joined to a session.

### Other harness-level actions the founder performed

- **158 Esc interrupts** (`[Request interrupted by user]`) in 25 sessions; 96 of them were on 22 Sep.
- Slash commands: `/model` 27, `/compact` 16 (plus 15 typed as text), `/clear` 6, `/login` 5, `/mcp` 2.
- 8 `!` shell commands, for example `! kill 11639 11647 11655`.
- 173 messages directly answered an agent turn that ended in a question.
- **102 messages carried a pasted block, in 31 sessions.** Of those, 30 were another session's
  terminal output (it contains `⏺`, `❯` or `▣ build`), 15 were PR links or numbers, 8 were error logs
  and 49 were other text. This is the founder acting as the copy-paste bus between sessions.

---

## (b) Ranked actions the founder needs from /fleet by voice

The ranking is by founder messages, with the number of distinct sessions in brackets. Labels
overlap, so one message can count toward several actions. The classifier used a regex per label
plus the error context of the previous assistant turn.

Every criterion below is written so that a **spoken-turn probe** can check it. The probe plays
audio into `/voice/hear` on the live page and reads back the evidence named in the **Then**
clause from the environment (session transcript JSONL, router ledger, bus, page DOM). A criterion
is met only when the probe reads that evidence. A 200 from an endpoint does not count.

| # | Action | Msgs (sessions) | Evidence it is real |
|---|---|---|---|
| 1 | Resume a session stalled by a router or API error | 311 (51) | 416 error turns in 76/83 sessions; replies `ok`/`continue`/`hi` |
| 2 | Give a running session a new task or directive | 177 (40) | "i need work merged and inbeanched an worktress cleaniend up apart for active cluade sesisons" |
| 3 | Answer or acknowledge an agent's question | 171 (40) | 173 replies to turns ending in `?`; `ok`, `yes`, `both`, `sounds perfect` |
| 4 | See and switch the model or lane a session uses, and its quota | 117 (31) | 27× `/model`; "are we rusin g the token efficency or not i need to see realtime traffic" |
| 5 | Nudge a stopped session ("continue", "go on") | 110 (17) | `continue`, `contiuue`, `conitue`, `go on` |
| 6 | Pass one session's output or PR to another | 102 (31) | pasted `⏺ …` terminal output; "look addr4s sthgis ionoise [paste]" |
| 7 | Ask whether a session is alive, or what it just said ("hi", "huh") | 96 (52) | 44 of 89 sampled `hi`/`huh` followed an API error; 25 opened a session |
| 8 | Ship: commit, open a PR, merge, clear uncommitted work | 78 (22) | "we need to merge and etele brnaches"; "we have too much work sitting uncommited/unpushed" |
| 9 | Ask whether it is live, or demand proof | 76 (23) | "how do built but not operating is the stroy of our lives"; "\\prove this works [paste]" |
| 10 | Check logs, CI or errors | 73 (21) | "confkcts [paste]"; "/mcp ⎿ Failed to reconnect to memory" |
| 11 | Know which agent owns which work | 59 (23) | "another agnet is fixing that"; "lol got 5 frontier models actibe like this" |
| 12 | Redirect or correct scope | 50 (19) | "5i asked for audit nothoing else"; "no this is how work gets lost" |
| 13 | Stop, interrupt or halt a session (or all sessions) | 47 (14), plus 158 Esc interrupts in 25 | "stop all work until you passclearancer"; `! kill 11639 …` |
| 14 | Ask for status or progress | 47 (15) | `wtf u doing` ×2, `update`, "whats the ipdate" |
| 15 | Fix a session's login or permission | 37 (22), plus 5 `/login` and 121 login/401 errors | `login`, "keeps asgin for login" |
| 16 | Compact or clear a session's context | 15 typed plus 22 slash commands (10) | `/compact`, `/clear` |
| — | Signals rather than actions: frustration or trust breach 123 (27), regression 48 (22) | | "you have ben broken for days now"; "voice is not working and im fed up of the regsessin" |

### Acceptance criteria (Given / When / Then)

The **Given** state is always "/fleet is open with the mic live, and N ≥ 3 real Claude Code
sessions are running on this laptop." A session is named by what the board shows for it: its
spoken name, its repo, or its task.

1. **Resume after error.**
   - Given session S's last assistant turn in its JSONL is an API error (ECONNREFUSED, timeout,
     reset, 5xx or rate limit),
   - When the founder says "resume S" (or "resume all stalled"),
   - Then within 10 s S's JSONL gains a new user turn and a non-error assistant turn follows,
     and the ledger shows a call with `session=S` and `ok=true`.
   - And: when the router is down, the page says so and names the lane before the founder speaks.
     The board flags S as `stalled: router` within 5 s of the error, measured from the error's
     JSONL timestamp to the board event.

2. **Directive to a running session.**
   - Given S is idle at its prompt or mid-turn,
   - When the founder says "tell S: <task>",
   - Then the exact words appear as a user turn in S's JSONL, no later than the end of the current
     turn, with `author=voice`. The page reads back "sent to S".
   - And: no other session's JSONL gains that text.

3. **Answer an agent's question.**
   - Given S's last assistant turn ends in a question or a pending choice,
   - When the board speaks the question and the founder answers ("yes", "both", "option two"),
   - Then the answer lands as S's next user turn and S's next assistant turn is not an error.
   - And: the board has a "waiting on you" queue. When a session goes waiting it is announced
     within 5 s, and it leaves the queue when answered.

4. **Model, lane and quota.**
   - When the founder asks "which model is S on?" the spoken answer equals the `model` field of
     S's most recent ledger row.
   - When the founder says "switch S to sonnet", S's next ledger row has that model.
   - When the founder asks "how much quota is left?", the answer comes from the router's own
     accounting and says which source it used.

5. **Nudge.**
   - Given S has had no assistant output for more than 60 s and is not waiting on a tool,
   - When the founder says "continue S",
   - Then S's JSONL gains a user turn followed by a new assistant turn within 30 s.

6. **Hand-off between sessions.**
   - When the founder says "give S2 what S1 just said" (or "send PR 4831 to S2"),
   - Then S2's next user turn contains S1's last assistant text, or the PR reference, verbatim,
     with S1 named as the source, and the founder never pastes anything.

7. **Alive and last words.**
   - When the founder says "is S alive?" or "what did S say?",
   - Then the spoken answer names S's state (working, waiting on you, stalled: router,
     stalled: login, idle, ended) and reads its last assistant sentence, and both match S's JSONL
     tail at that moment.

8. **Ship.**
   - When the founder says "what has S not shipped?", the answer lists the uncommitted files and
     unpushed commits in S's worktree and its open PRs, and it matches `git status` and GitHub.
   - When the founder says "open a PR for S" or "merge PR <n>", the PR number comes from speech,
     the page reads back what it will do, and on "yes" the PR state changes on GitHub.

9. **Is it live.**
   - When the founder asks "is S's work live?", the answer names the PR, whether it is merged,
     the deployed image or commit, and the newest production log line or runtime event attributed
     to it with its timestamp.
   - When no such line exists, the answer says "not operating" and does not say "done".

10. **Logs, CI and errors.**
    - When the founder says "why is S failing?" or "CI on PR <n>", the answer names the failing
      check or the last error line, taken from `ci-status`/`ci.errors` or S's JSONL, with its URL on
      screen.

11. **Who owns what.**
    - When the founder asks "who is working on X?", the answer names every session whose current
      task, branch or open PR matches X, and says so when two sessions overlap.

12. **Redirect.** Same mechanism as criterion 2, plus one check: after "S, only do the audit",
    S's next assistant turn acknowledges the narrowed scope.

13. **Stop.**
    - When the founder says "stop S", S's in-flight turn is interrupted within 5 s (the same effect
      as Esc: `[Request interrupted by user]` in the JSONL).
    - When the founder says "stop all", every running session shows that entry and the board shows
      each one as stopped.
    - Both require a read-back and a "yes".

14. **Status.**
    - When the founder asks "what's everyone doing?", each running session is named with its task
      and state, the count matches the number of live JSONLs written in the last 5 minutes, and a
      session that cannot be read is named as unreadable rather than left out.

15. **Login.**
    - Given S's last turn is "Please run /login" or a 401,
    - When the founder says "fix S's login",
    - Then either S's next call succeeds (a ledger `ok=true` row for S), or the page names the one
      human step and the device it needs.

16. **Compact or clear.**
    - When the founder says "compact S", S's JSONL shows a compaction boundary and the board shows
      S's context size dropping.

---

## (c) What the current intent catalogue covers, and the gaps

These facts were measured in the repo today.

- **Voice to intent** (`voice_intents.py`) runs an intent when its name tokens appear in the
  utterance. Only intents whose args all have defaults qualify: **52 of 73** in
  `platform/estate/intents/`. Seven read-only intents run at once (`ci-status`, `ci.errors`,
  `cost-today`, `git-log`, `router-status`, `voice-turns`, `ledger-verify`). The rest need a spoken
  "yes".
- **Speech cannot pass arguments.** `execute()` runs `[estate-execute, <name>]`. So `pr-merge` by
  voice runs with its defaults, `pr=0, dry_run=true`, and does nothing useful.
- **No intent in the catalogue targets a Claude Code session.** None takes a session id.
- **The audit log `~/.estate/voice-intents.jsonl` has 2 entries ever**, both `router-status` on
  27 Sep.
- "Give an agent a job: <task>" starts a **new** agent job after a read-back. It does not reach a
  running session.
- **Steer and nudge to Claude Code** (`signals._dispatch_steer_claude_code`) write
  `~/.claude/state/directives/<uuid>.json`. The docstring says a SessionStart or PostCompact hook
  reads that file. However, "directives" appears in neither `~/.claude/settings.json` nor
  `estate-core/scripts`, and the directory holds one file, from 27 Sep. **As measured, a steer is
  written but never delivered to a running session.**
- **The sessions board's Claude Code adapter** (`sessions._claude_code_sessions`) reads
  `~/.claude/state/prompt-ledger/`, which was **last written on 21 Sep at 22:14**. None of the 83
  sessions in this window can appear from that source.

| # | Action | Covered today | Gap |
|---|---|---|---|
| 1 | Resume after error | partly: `router-status` (voice, read-only) reports router health | no per-session error state and no resume of a Claude Code session; this is **the largest gap by volume** |
| 2 | Directive to a running session | no: the steer file is not read (above); agent-job creates a new job instead | delivery into the live session |
| 3 | Answer a question | no: yes/no exists only for pending intents | a "waiting on you" queue and answer delivery |
| 4 | Model, lane, quota | partly: `router-status`, `cost-today` (voice); the ledger has per-session model | per-session model on the board; switching a session's model |
| 5 | Nudge | no: `/nudge` uses the same undelivered path | delivery |
| 6 | Hand-off | no | a cross-session relay |
| 7 | Alive and last words | no for Claude Code (adapter stale) | JSONL-tail-backed state |
| 8 | Ship | partly: `pr-list`, `pr-ready`, `git-log` by voice; `pr-merge` only with defaults; `git.commit` is not voice-reachable | spoken arguments (PR number, session) and per-session worktree state |
| 9 | Is it live | partly: `fleet-regression`, `flux-status`, `ledger-verify` are estate-wide | a per-session chain from PR to deploy to production log line |
| 10 | Logs, CI | partly: `ci-status`, `ci.errors` (voice, defaults only); `k8s-logs` not voice-reachable | spoken PR or session argument |
| 11 | Who owns what | no | a session-to-branch-to-PR-to-task map |
| 12 | Redirect | no (same as 2) | delivery |
| 13 | Stop | no: `halt` is "print state and exit"; mutation reject applies only to mutations | interrupting a Claude Code turn, and stop-all |
| 14 | Status | partly: `fleet_summary` exists but its Claude Code data is stale | a live source |
| 15 | Login | no | per-session auth state |
| 16 | Compact or clear | no | a compact trigger |

**The biggest gaps, by founder messages affected:** (1) resume and error visibility, 311 messages;
(2) delivering a directive, nudge or redirect into a *running* Claude Code session, 177 + 110 + 50;
(3) answering an agent's question, 171; (6) hand-off between sessions, 102; (7) and (14) live
per-session state, where the board's Claude Code source is 8 days stale.

---

## (d) Minimum state /fleet must show per session

Each field below is justified by what the founder had to go and find, or send a message to learn.
Every field has a data source that exists today.

| Field | Why (evidence) | Source |
|---|---|---|
| Name, repo or worktree, current task (first line of the last directive) | 83 sessions, 39 % switch rate, no way to address one by voice | session JSONL path and last founder message |
| **State**: working, waiting on you, stalled: router, stalled: login, idle, ended | 311 resumes after errors; 96 "hi"/"huh" pings; 173 answers to questions | JSONL tail: last entry type, error text, a trailing `?` |
| Last error kind, and how long ago | 416 error turns; median 82 s and p90 31 min before the founder noticed | JSONL error turns, ledger `ok=false` |
| Last assistant sentence (spoken on request) | "huh"; 30 pastes of another session's terminal output | JSONL tail |
| Pending question, if any | 173 answers to questions | JSONL tail |
| Model and lane, last call latency, ok-rate over the last 15 min | 27× `/model`; 117 model/router messages; 40 % failures on 29 Sep | ledger rows where `session` = the session UUID |
| Branch, uncommitted file count, unpushed commits, open PRs with CI state | 78 ship messages; "too much work sitting uncommited/unpushed" | git in the worktree, `ci-status` |
| Live or not: merged? deployed? newest production line? | 76 "is it live / prove it" messages | PR, then Flux image, then log line |
| Context size (and whether compaction is due) | 31 `/compact`, 6 `/clear` | JSONL usage fields |
| Overlap warning when two sessions touch the same branch, PR or files | 59 coordination messages; "another agnet is fixing that" | branch and PR map across sessions |

Also shown estate-wide, not per session: router up or down, with the failing lane named, because
ECONNREFUSED stalls every session at once. On 29 Sep there were 167 error turns across the fleet.

---

### Reproducing

The counts were produced by throwaway scripts (extraction, a regex classifier per label, the
stall and error join) that were not kept, so they cannot be rerun byte for byte. Treat the numbers
as a well-evidenced estimate. Rerunning the method on the same sources should land close; making
it a repeatable tool is follow-up work.
