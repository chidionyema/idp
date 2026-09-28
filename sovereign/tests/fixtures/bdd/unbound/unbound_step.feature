Feature: A feature whose steps are not all bound
  The must-fail fixture for the bdd leg of bin/idp-ci. The second step below
  has no definition in test_unbound.py on purpose. If pytest reports this as a
  pass, the harness is not reading the feature files and every other cp
  scenario is decoration.

  Scenario: One step is bound and one is not
    Given a step that is bound
    Then a step that nobody defined runs
