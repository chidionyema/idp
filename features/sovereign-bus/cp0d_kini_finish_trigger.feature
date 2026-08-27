Feature: CP0d "Finish KINI" is one word, and the answer is a receipt (crew#396 step 4)
  Founder, 2026-08-26: "type 'Finish KINI', close the laptop, wake up to a green dashboard."
  The word is an issue comment `FINISH: KINI` (or a dispatch). Actions renames the Job in
  platform/temporal/kini-finish.yaml to the request and auto-merges; Flux applies it; the Job
  runs `kini finish --wait` on the in-cluster engine; the kini-state CronJob publishes state/kini;
  bin/idp-kini-state grades it in oke-check job kini-state, catalogue row kini-finish.

  Scenario: the receipt head is total and the reader grades every branch both ways
    Given every status the CLI can report
    Then receipt_head maps NONE, RUNNING and a green COMPLETED to "ok" and anything red to "FAIL"
    And bin/idp-kini-state passes a fresh green receipt and refuses a red or stale one

  Scenario: the trigger is wired end to end in git
    Given the workflow kini-finish.yml
    Then it fires on an owner's `FINISH: KINI` comment, renames the Job and arms auto-merge
    And platform/temporal renders the Job and the kini-state CronJob on the worker image and service account
    And oke-check.yml has job kini-state and drills/catalogue.yaml has row kini-finish
    And `kini receipt` is a CLI subcommand
