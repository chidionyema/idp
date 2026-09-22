"""relatives: relative imports resolve to the same projection's siblings."""

from .beta import beta_function


def relatives_function() -> str:
    return beta_function()
