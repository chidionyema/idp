"""Ask helm again when the chart host hangs up, and only then.

2026-09-07, run 34122274707: bin/idp-ci's kyverno rung reported

    FAIL  render   platform/observability-collector: the render did not complete
    FAIL  render   platform/temporal: the render did not complete

and the cause under both was `read: connection reset by peer` fetching index.yaml from
charts.signoz.io and go.temporal.io -- two GitHub Pages hosts on the same address, in the same
second, for two platform directories nobody had touched. Main went red on that, and rule-guard
then correctly refused every merge onto a red main, so one remote hiccup stopped three
unrelated pull requests.

A render that fails because the far end hung up is not a verdict about this repository. It is
retried, three attempts with a widening pause. A chart that is genuinely wrong -- a version
that does not exist, values the chart rejects -- fails all three the same way and costs three
extra seconds, so nothing that should be red is turned green here.

This lives in its own module rather than inside bin/idp-kyverno-render's heredoc because the
script it came from spends minutes downloading policies and running the Kyverno CLI before it
reaches the first helm call, and a retry graded through all of that is a test nobody will run.
"""

import subprocess
import time

ATTEMPTS = 3


def template(cmd, env, attempts=ATTEMPTS, sleep=time.sleep, run=subprocess.run):
    """Run `cmd`, retrying a failure up to `attempts` times.

    Returns (CompletedProcess, [one-line reason per failed attempt]). The reasons are returned
    rather than swallowed so the caller can say "three attempts, all failed" instead of hiding
    a flaky host behind a single message (LAW 28).
    """
    tried = []
    for i in range(attempts):
        r = run(cmd, text=True, capture_output=True, env=env)
        if r.returncode == 0:
            return r, tried
        err = (r.stderr or "").strip()
        tried.append(err.splitlines()[-1] if err else f"exit {r.returncode}")
        if i < attempts - 1:
            sleep(1.5 * (i + 1))
    return r, tried
