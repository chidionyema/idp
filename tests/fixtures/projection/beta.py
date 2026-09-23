"""beta: depends on gamma; nothing else."""

from gamma import gamma_function


def beta_function() -> str:
    return gamma_function()
