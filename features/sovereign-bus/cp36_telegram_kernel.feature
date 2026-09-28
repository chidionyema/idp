Feature: cp36 Telegram is a receipt channel, not a chat (spec 2.2, 2.3; crew#284 CP1)

  Scenario: A photo with a caption becomes one DOC_COMMIT line and never reaches the model
    Given the founder sends a photo with caption "save this article"
    When the gateway pre-dispatch hook runs
    Then the message is skipped before dispatch
    And exactly one Telegram message is sent
    And that message is one line containing "DOC_COMMIT", a hash and a budget delta

  Scenario: A photo without a caption is dispatched normally
    Given the founder sends a photo with no caption
    When the gateway pre-dispatch hook runs
    Then the hook returns None

  Scenario: undo from the phone replies with the undo receipt line, not prose
    Given session "sb-deadbeef" has a receipt of kind "undo" in the chain
    When the founder sends "/sb-undo sb-deadbeef"
    Then sb was invoked with "undo sb-deadbeef --by telegram"
    And the reply is one line starting with the ok mark and "UNDO"

  Scenario: stop from the phone replies with the session's newest receipt
    Given session "sb-deadbeef" has a receipt of kind "stop" in the chain
    When the founder sends "/sb-stop sb-deadbeef"
    Then the reply is one line starting with the ok mark and "STOP"
