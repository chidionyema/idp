"""alpha: depends on beta and gamma; references an external (os)."""

import os

from beta import beta_function
from gamma import gamma_function


def alpha_function() -> str:
    return beta_function() + gamma_function() + os.sep
