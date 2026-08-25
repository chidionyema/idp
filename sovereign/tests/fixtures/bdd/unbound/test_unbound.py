"""The must-fail half of the bdd leg's both-ways proof. Do not bind the
missing step: `bin/idp-ci` asserts that pytest refuses this directory."""
from pytest_bdd import given, scenarios

scenarios("sovereign/tests/fixtures/bdd/unbound/unbound_step.feature")


@given("a step that is bound")
def _bound() -> None:
    return None


# "Then a step that nobody defined runs" is deliberately absent.
