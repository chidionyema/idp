@cp5 @kini @digest
Feature: The daily digest is a job on the estate scheduler
  KINI master spec (crew#284) CP5, spec 2.5: one digest a day at 09:00 local,
  at most six lines, signed by the kernel. The estate has one scheduler
  (Dagster, scheduler/schedule.yml); the digest is a row in it, not a launchd
  plist of its own. Everything that is not the digest or a catastrophe is
  routed to Spatial/Haptic and never opens the chat: cp32 "The system never
  opens Converse" holds that rule and is not repeated here.

  Scenario: The digest job exists and fires at the configured hour
    Given scheduler/schedule.yml
    Then it has a job ai.estate.sovereign-digest running `sovereign.cli digest --send`
    And its cron hour equals presence.digest_hour in sovereign/presence/config_keys.py
    And the job resolves to a description (estate_scheduler.describe)
