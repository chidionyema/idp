"""broken: syntactically invalid Python. The projection must skip it with a
log line, not raise. This proves TOT (totality): a SyntaxError is a logged
skip, never a silent drop or a crash."""

def broken( ->  # noqa: invalid syntax on purpose