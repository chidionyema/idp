@cp7
Feature: Cockpit — a screen, not a command list, on the phone and the laptop
  Founder: "the current UI is unusable, I need a reimagining." The cockpit is
  one page: Sessions, Decisions, Inbox. Tap to stop, steer, approve. It is
  served by the estate on the laptop and opened on the phone as a Telegram
  Mini App through the estate's public URL.

  Scenario: The cockpit serves the truth from Temporal
    Given the cockpit is running
    When I GET "/api/sessions"
    Then the response is a JSON list that matches "bin/sb list --json"

  Scenario: A tap is a signal
    Given a running session started with "--runner sleep --task 'sleep 60'"
    When I POST "/api/sessions/<session_id>/stop" with by "founder"
    Then "bin/sb show <session_id> --json" "status" is "stopped" within 5 seconds

  Scenario: The Inbox is on the screen, not in the chat
    Given the inbox file has at least one line
    When I GET "/api/inbox"
    Then the response lists that line

  Scenario: The menu button opens the cockpit
    Given ESTATE_PUBLIC_URL is set
    When I run "bin/sb menu --json"
    Then Telegram getChatMenuButton returns type "web_app" with that URL
