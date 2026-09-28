"""must-fail fixture: a code location that only loads as a package.

This is the 2026-08-25 break. definitions.py imported a sibling with `from
.describe import ...`, which is fine when something imports it as a package and
fails with "attempted relative import with no known parent package" when
workspace.yaml loads it by path -- which is how it actually runs. Every offline
check passed; the live code location went to PythonError on reload.
"""

from dagster import Definitions, job, op

from .describe import describe  # noqa: F401  -- the break, on purpose


@op
def _noop():
    pass


@job
def a_job():
    _noop()


defs = Definitions(jobs=[a_job])
