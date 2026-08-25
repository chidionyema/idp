"""A pending mark with owner "unclaimed". Do not claim it: the branch-policy
guard asserts this fails under SB_BDD_STRICT=1 and skips without it."""
import pytest
from pytest_bdd import scenarios

pytestmark = pytest.mark.pending("R0", owner="unclaimed")

scenarios("sovereign/tests/fixtures/bdd/pending_unclaimed/pending_unclaimed.feature")
