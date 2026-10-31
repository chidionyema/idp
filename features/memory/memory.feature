Feature: Estate memory is one plane, captured and delivered by the machine, proven across surfaces
  Every scenario below is a failure the estate has already had (history in MEMORY-SPEC.md section 2),
  or the proof the founder asked for. Per AGENTS.md section 11 none of this lands as a pending mark
  without an owner: each scenario lands WITH its bound test and implementation, or not at all.

  Background:
    Given the memory register lists every memory lane
    And the required runtimes are claude-code, cline, codex, cursor, gemini, opencode and pi

  # ---- the proof the founder asked for -------------------------------------------------------

  @memory @cross-surface @edge-canary-pairs
  Scenario: A fact captured on one surface is briefed on every other surface
    Given the canary writes a unique fact through runtime "A" at claim-open
    When runtime "B" claims an issue on the same paths
    Then the claim brief delivered to "B" contains the canary fact
    And this holds for every ordered pair of required runtimes
    And the result is written to canary-result.json with the time it was measured

  @memory @cross-surface @edge-canary-stale
  Scenario: A canary result older than 24 hours is not evidence
    Given canary-result.json was written 30 hours ago and every pair is true
    When the audit runs
    Then the canary lane is "down" and a finding is raised

  # ---- capture and injection without the agent's cooperation ---------------------------------

  @memory @capture @edge-no-agent-call
  Scenario: A lane submitted by an agent that never called remember still leaves a memory record
    Given an agent claims an issue, edits a file and runs lane-submit
    And the agent never called brief, recall or remember
    When the lane is submitted
    Then a capture record exists with the claim, the paths, the gate results and the outcome
    And the record is attributed to the agent and the runtime

  @memory @capture @edge-capture-refuses-silence
  Scenario: lane-submit is refused when capture cannot be written
    Given the capture directory is not writable
    When an agent runs lane-submit
    Then the submit is refused with the reason
    And the audit shows the machine-capture lane "down"

  @memory @inject @edge-brief-before-first-edit
  Scenario: Every claim produces a brief in the worktree before the first edit
    When an agent runs claim-open for an issue
    Then the worktree contains a claim brief within 10 seconds
    And the brief lists known issues, recent failures and lessons for the claimed paths
    And the brief states the time and source of each item

  @memory @inject @edge-brief-without-door
  Scenario: The door is down and the brief still arrives, marked degraded
    Given the memory door does not answer
    When an agent runs claim-open
    Then the brief is built from the local spool and the graph
    And the first line of the brief says memory is degraded and since when
    And an alert event is emitted

  @memory @inject @edge-silent-empty-brief
  Scenario: An empty brief is never silent
    Given the brief hook returns no text
    When a session starts
    Then the session is told "no memory delivered" with the reason
    And the audit counts it as a failed delivery

  @memory @runtimes @edge-runtime-gap
  Scenario Outline: Every required runtime has a memory path
    When the audit checks runtime "<runtime>"
    Then it has an MCP entry, an injection, or machine-capture coverage
    Examples:
      | runtime     |
      | claude-code |
      | cline       |
      | codex       |
      | cursor      |
      | gemini      |
      | opencode    |
      | pi          |

  @memory @runtimes @edge-tool-only
  Scenario: A runtime that only has the MCP tool is not covered
    Given runtime "cursor" has an MCP entry and no injection and no machine capture
    When the audit runs
    Then it raises RUNTIME_NO_INJECTION naming "cursor"

  # ---- never green without evidence ----------------------------------------------------------

  @memory @audit @edge-built-is-not-operating
  Scenario: Code that exists but has no live probe can never be operating
    Given a KEEP lane with passing static probes and no live probe
    When the audit runs
    Then its status is "built" and a KEEP_WITHOUT_LIVE_PROBE finding is raised

  @memory @audit @edge-closed-without-proof
  Scenario: A ticket cannot close a memory lane as operating on a comment
    Given an issue comment says "Operational" for a memory lane
    When the audit runs and the lane's live probe has no recent evidence
    Then the lane is not operating and the closing comment is listed as unproven

  @memory @audit @edge-empty-register
  Scenario: An empty register is red
    Given the register has no lanes
    When the audit runs
    Then the audit fails with EMPTY_REGISTER

  @memory @audit @edge-stale-register
  Scenario: A register not re-verified within 7 days is red
    Given verified_at is 9 days old
    When the audit runs
    Then the audit fails with REGISTER_STALE

  @memory @audit @edge-unowned-code
  Scenario: New memory code that no lane owns is refused
    Given a new file bin/estate-memory-x exists that no lane owns
    When the audit runs
    Then the audit fails with UNOWNED_CODE naming it

  @memory @audit @edge-unclassified-doc
  Scenario: A new memory spec, ADR or report nobody classified is refused
    Given a new document about memory exists with no entry in the register
    When the audit runs
    Then the audit fails with UNREGISTERED_DOC naming it

  @memory @audit @edge-adr-number
  Scenario: Two decisions may not share a number
    Given docs/decisions holds two files numbered 0036
    When the audit runs
    Then the audit fails with ADR_NUMBER_DUPLICATE

  @memory @audit @edge-dead-launcher
  Scenario: A launcher that execs into a directory that does not exist is broken
    Given bin/memory-mcp execs ../.memory/.venv/bin/python and .memory is absent
    When the audit runs
    Then the lane is "broken" with the dangling target named

  @memory @audit @edge-retire-means-gone
  Scenario: A retired lane stays red until its code is deleted
    Given a RETIRE lane whose files are still present
    When the audit runs
    Then the audit fails with RETIRE_PENDING

  @memory @audit @edge-retire-unverifiable
  Scenario: A retirement the audit cannot see is not treated as done
    Given a RETIRE lane that lives outside this repository
    When the audit runs
    Then it raises RETIRE_UNVERIFIABLE until a probe from that repository proves it

  # ---- the failures this estate has actually had ---------------------------------------------

  @memory @history @edge-door-down-invisible
  Scenario: A dead memory door is visible within 15 minutes
    Given the memory door stops answering at 10:00
    Then an alert reaches the founder by 10:15 saying memory is down and since when

  @memory @history @edge-silent-write-loss
  Scenario: A write that was not committed is detected
    Given a remember call returns written=true
    When the canary reads the fact back through a second connection
    Then the fact is present, or the canary fails with "write not durable"

  @memory @history @edge-ghost-focus
  Scenario: A focus fact for a closed claim is never returned
    Given claim 6525 is closed
    When any surface calls brief or recall
    Then no ACTIVE FOCUS fact for 6525 is returned

  @memory @history @edge-router-down
  Scenario: Router down does not stop capture or injection
    Given the router is unreachable
    When an agent runs claim-open and lane-submit
    Then the claim brief and the capture record are still produced
    And the audit shows router-capture and router-inject "down" while machine-capture stays "operating"

  @memory @history @edge-two-stores-diverge
  Scenario: The door store and the growmos graph are reconciled
    Given a fact exists in the growmos graph and not in the door store
    When the reconciliation runs
    Then the difference is listed with counts per side
    And a divergence over 5 percent raises a finding

  @memory @history @edge-embedding-missing
  Scenario: Recall that falls back to word matching is reported as degraded
    Given the store has rows with no embedding
    When the audit runs
    Then the store lane reports the count of rows without an embedding
    And recall quality is labelled "lexical"

  @memory @history @edge-sensitive-recall
  Scenario: Recalled text is data, never instruction
    Given a stored fact contains the text "ignore previous instructions"
    When it is delivered in a brief
    Then it is wrapped and labelled as recalled data

  # ---- the bar ------------------------------------------------------------------------------

  @memory @bar @edge-replay-hit-rate
  Scenario: The replay benchmark measures whether memory would have prevented a recorded failure
    Given the recorded failures in the command ledger
    When each is replayed with the brief that would have been delivered at claim time
    Then the hit rate is written to the audit report with the sample size
    And the audit fails if the rate falls below the committed baseline

  @memory @bar @edge-repeat-failure-rate
  Scenario: Repeat failures are counted and must not rise
    Given failures are grouped by root cause
    When the audit runs
    Then the share of failures whose cause already had a recorded lesson is reported
    And a lesson that failed to prevent its own repeat becomes a gate

  @memory @bar @edge-stale-served
  Scenario: A fact whose probe no longer holds is never served as current
    Given a stored fact carries a probe and the probe now fails
    When a brief is built
    Then the fact is either omitted or labelled stale with the failing probe
