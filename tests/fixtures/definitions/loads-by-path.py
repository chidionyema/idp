"""must-pass fixture: a code location that loads however it is loaded."""

from dagster import Definitions, job, op


@op
def _noop():
    pass


@job(description="A job that carries a description, loaded by file path.")
def a_job():
    _noop()


defs = Definitions(jobs=[a_job])
