Feature: The Greenlane: main never goes red, and no pull request that can fail is ever raised
  Founder, 2026-09-29: "I need mathematical guarantees PRs can't fail on this platform",
  "main must never go red, never", "a PR that can fail should never be allowed to be raised",
  "simulate the chaos we cause now, worktrees and branch mess, everything, and our system must
  not break or go red", "prove it with minimum 500 concurrent lanes".

  The lane is a serial gated trunk (Rust's bors, 2013; Uber's SubmitQueue, EuroSys 2019) with
  batching and bisection, run by one engine (greenlane/engine.py). Only the engine's GitHub App
  may move main (ruleset idp-main-writer); it moves main only by fast-forward to a sha whose
  required checks passed at that exact sha; a pull request is raised for a lane only when its
  candidate is green on top of the current main, and it is merged by the same fast-forward.

  These scenarios run the real engine against an in-memory model of the estate's chaos
  (greenlane/simulate.py). Checks in the model are flaky one way only: a green tree may be
  reported red, never the reverse. A check that passes on a broken tree is a missing test, and
  no queue can repair that; that is the one assumption the guarantee rests on.

  Background:
    Given 500 lanes cut from stale worktrees, with broken commits, incompatible pairs, overlapping files, re-pushes, deletions, hand-raised pull requests, direct pushes to main, a bot lane and flaky checks

  Scenario: Main never goes red
    When the engine runs the lanes to completion
    Then every sha main ever pointed to is green
    And no broken change is in main

  Scenario: Nothing but the engine can move main
    When the engine runs the lanes to completion
    Then at least one agent tried to push main directly
    And zero direct pushes to main succeeded

  Scenario: A pull request that can fail is never raised
    When the engine runs the lanes to completion
    Then at least one agent raised a pull request by hand
    And every hand-raised pull request was refused and its branch kept as a lane
    And no open pull request was ever observed after the platform handled the event
    And every pull request the engine raised was green at the sha it was raised with, and merged in the same act

  Scenario: No work is lost and every lane ends with a verdict
    When the engine runs the lanes to completion
    Then every lane is landed, red with a reason, in conflict with a reason, or deleted by its own agent
    And no lane is silent

  Scenario: A lane that is green on its own always lands
    When the engine runs the lanes to completion
    Then every lane that is green on top of main has landed
    And the run finished in a bounded number of ticks

  Scenario: The engine survives being restarted between every tick
    Given the same chaos
    When the engine runs the lanes with its state serialised and reloaded on every tick
    Then the outcome is identical to the uninterrupted run
