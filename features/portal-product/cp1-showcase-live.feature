@cp1
Feature: the showcase page reads live state, never a markdown file
  docs/specs/backstage-as-a-product.md CP1. Founder, 2026-09-05: "showcase needs to wow and
  impress". Today docs/SHOWCASE.md is a generated file read through GitHub; a buyer's engineer
  reads a report, not a room. Bound to R53: this grades what is returned and drawn from, never
  a selector or a layout word.

  Scenario: the showcase page answers with data read on this load, not a stored file
    Given the portal is signed in
    When a visitor opens the showcase page
    Then the entity counts shown match a fresh catalogue query made for that page load
    And no field on the page is copied from a committed markdown file

  Scenario: every system on the showcase page carries a live health value
    Given the catalogue lists ten systems under estate/group
    When the showcase page reads cluster state through the Kubernetes proxy
    Then every one of the ten systems has a health value newer than the page's own load time

  Scenario: the five Otto capabilities are read from their proof file, not retyped
    Given docs/specs/otto-capability-inventory.md marks five capabilities LIVE
    When the showcase page renders its Otto section
    Then it lists exactly the capabilities marked LIVE in that file
    And each one carries the file path the inventory names as its proof
