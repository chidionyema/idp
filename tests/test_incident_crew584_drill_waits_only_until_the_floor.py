"""crew#584 CP-A (LAW 45): the portability drill waits only until the floor is met.

Incident 2026-08-29: both drill jobs ran `kubectl wait kustomization --all -A --timeout=600s`,
which always burned the full 600 s because OCI-only layers never come Ready off OCI. Measured
11 min on 9 of the last 10 runs. bin/idp-drill-wait polls the grader and exits at the floor.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WF = os.path.join(ROOT, ".github", "workflows", "portability-drill.yml")
WAIT = os.path.join(ROOT, "bin", "idp-drill-wait")
FLOOR = os.path.join(ROOT, "drills", "portability-floor.txt")


def test_no_job_sleeps_the_full_600s_on_kubectl_wait():
    text = open(WF, encoding="utf-8").read()
    assert not re.search(r"kubectl wait kustomization --all", text), "the fixed 600 s wait is back"
    assert text.count("run: bin/idp-drill-wait") == 2, "both hydrate and k3s must use the floor wait"


def test_wait_script_polls_the_grader_and_exits_at_the_floor():
    text = open(WAIT, encoding="utf-8").read()
    assert "bin/idp-portability-drill" in text
    assert 'DRILL_WAIT_MAX:-600' in text
    assert os.access(WAIT, os.X_OK)
    subprocess.run(["bash", "-n", WAIT], check=True)


def _floor() -> int:
    """The floor the wait script will actually read. Taken from the file rather than written into
    this test: the fake cluster below has to clear whatever the estate's floor is today, and a
    literal here would red the drill's own test every time crew#488 raises the number (it did, at
    2 -> 9, run 33223579672)."""
    for line in open(FLOOR, encoding="utf-8"):
        line = line.split("#", 1)[0].strip()
        if line:
            return int(line)
    raise AssertionError("no integer in %s" % FLOOR)


def test_wait_script_returns_the_moment_the_floor_is_met(tmp_path):
    """A fake kubectl reporting exactly floor-many Ready layers must end the wait on the first poll.

    Counted, not timed. The assertion used to be `floor met after [0-2] s`, which graded how long
    bin/idp-portability-drill takes to run rather than how many times the wait script polls: on the
    crew#488 CP5 drill, which names a cause and a cascade for every red row, one poll takes ~5 s and
    the timing assertion went red on a script that behaved perfectly. The fake counts its own calls,
    so what is graded is the poll count -- one -- on any machine at any speed.
    """
    n = _floor()
    items = ",".join(
        '{"metadata":{"namespace":"a","name":"k%d"},"status":{"conditions":[{"type":"Ready","status":"True"}]}}' % i
        for i in range(n))
    calls = tmp_path / "calls"
    fake = tmp_path / "kubectl"
    fake.write_text(
        "#!/usr/bin/env bash\necho call >> %s\ncat <<'JSON'\n{\"items\":[%s]}\nJSON\n" % (calls, items))
    fake.chmod(0o755)
    env = dict(os.environ, PATH=f"{tmp_path}:{os.environ['PATH']}", DRILL_WAIT_STEP="1", DRILL_WAIT_MAX="120")
    out = subprocess.run([WAIT], env=env, capture_output=True, text=True, timeout=180)
    assert out.returncode == 0, out.stderr
    assert re.search(r"floor met after \d+ s", out.stdout), out.stdout
    assert calls.read_text().count("call") == 1, "the wait polled more than once on a cluster already at the floor"


def test_wait_script_gives_up_at_the_ceiling_without_failing_the_job(tmp_path):
    fake = tmp_path / "kubectl"
    fake.write_text("#!/usr/bin/env bash\nprintf '{\"items\":[]}'\n")
    fake.chmod(0o755)
    env = dict(os.environ, PATH=f"{tmp_path}:{os.environ['PATH']}", DRILL_WAIT_STEP="1", DRILL_WAIT_MAX="2")
    out = subprocess.run([WAIT], env=env, capture_output=True, text=True, timeout=30)
    assert out.returncode == 0
    assert "floor not met after 2 s" in out.stdout, out.stdout


if __name__ == "__main__":
    sys.exit(subprocess.call([sys.executable, "-m", "pytest", "-q", __file__]))
