"""crew#584 CP-A and crew#488: what the portability drill's wait exits ON.

Two incidents, one file, because the second is the first one's fix taken too far.

CP-A (2026-08-29): both drill jobs ran `kubectl wait kustomization --all -A --timeout=600s`, which
always burned the full 600 s -- the OCI-only layers never come Ready off OCI. 11 min on 9 of the
last 10 runs. bin/idp-drill-wait replaced it with a poll.

crew#488 (2026-08-29): the poll exited when `ready` reached drills/portability-floor.txt, so the
grade step read a cluster that had been stopped AT the floor and the count echoed the file it was
about to be graded against. #682's 60 s grace narrowed that without cutting it: across the per-job
lines of runs 33241407747 / 33240990075 / 33240774821 / 33239862769 / 33235017912, a floor of 9
graded 9-11 and a floor of 10 graded 10-11, and the two jobs of a single run disagreed by one.
The wait now never reads the floor: it leaves when the verdict stops changing.
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


def _floor() -> int:
    """The estate's floor today. Read, never written into a test: a literal here reds this file
    every time crew#488 ratchets the number (it did, at 2 -> 9, run 33223579672)."""
    for line in open(FLOOR, encoding="utf-8"):
        line = line.split("#", 1)[0].strip()
        if line:
            return int(line)
    raise AssertionError("no integer in %s" % FLOOR)


def _fake_kubectl(tmp_path, counts, calls_file):
    """A kubectl whose Nth call reports counts[N] Ready Kustomizations, holding the last value.

    The fake counts its own calls in `calls_file`, so every assertion below is on the number of
    polls rather than on elapsed seconds -- one poll runs the whole CP5 grader and takes ~5 s, and
    an earlier timing assertion here went red on a script that behaved perfectly.
    """
    arr = " ".join(str(c) for c in counts)
    fake = tmp_path / "kubectl"
    fake.write_text(
        "#!/usr/bin/env bash\n"
        "counts=(%s)\n"
        "c=$(cat %s 2>/dev/null || echo 0); c=$((c+1)); echo \"$c\" > %s\n"
        "i=$((c-1)); last=$(( ${#counts[@]} - 1 )); (( i > last )) && i=$last\n"
        "n=${counts[$i]}\n"
        "printf '{\"items\":['\n"
        "for ((k=0;k<n;k++)); do (( k )) && printf ','; "
        "printf '{\"metadata\":{\"namespace\":\"a\",\"name\":\"k%%d\"},"
        "\"status\":{\"conditions\":[{\"type\":\"Ready\",\"status\":\"True\"}]}}' \"$k\"; done\n"
        "printf ']}'\n" % (arr, calls_file, calls_file))
    fake.chmod(0o755)
    return fake


def _run(tmp_path, **env_over):
    env = dict(os.environ, PATH=f"{tmp_path}:{os.environ['PATH']}",
               DRILL_WAIT_STEP="1", DRILL_WAIT_MAX="120", DRILL_WAIT_STABLE="3")
    env.update(env_over)
    return subprocess.run([WAIT], env=env, capture_output=True, text=True, timeout=180)


# --- crew#584 CP-A: the fixed 600 s is gone and stays gone -------------------------------------

def test_no_job_sleeps_the_full_600s_on_kubectl_wait():
    text = open(WF, encoding="utf-8").read()
    assert not re.search(r"kubectl wait kustomization --all", text), "the fixed 600 s wait is back"
    assert text.count("run: bin/idp-drill-wait") == 2, "both hydrate and k3s must use the floor wait"


def test_wait_script_polls_the_grader_and_is_bounded():
    text = open(WAIT, encoding="utf-8").read()
    assert "bin/idp-portability-drill" in text
    assert 'DRILL_WAIT_MAX:-600' in text
    assert os.access(WAIT, os.X_OK)
    subprocess.run(["bash", "-n", WAIT], check=True)


def test_the_wait_gives_up_at_the_ceiling_without_failing_the_job(tmp_path):
    fake = tmp_path / "kubectl"
    fake.write_text("#!/usr/bin/env bash\nprintf '{\"items\":[]}'\n")
    fake.chmod(0o755)
    out = _run(tmp_path, DRILL_WAIT_MAX="2")
    assert out.returncode == 0
    assert "not settled after 2 s" in out.stdout, out.stdout


def test_a_cluster_that_never_stops_moving_is_bounded_by_the_ceiling(tmp_path):
    """Every poll reports a different count, so the verdict is never stable. The job must still
    end at the ceiling rather than polling forever."""
    calls = tmp_path / "calls"
    _fake_kubectl(tmp_path, list(range(1, 60)), calls)
    out = _run(tmp_path, DRILL_WAIT_MAX="4")
    assert out.returncode == 0
    assert "not settled after 4 s" in out.stdout, out.stdout


# --- crew#488: the exit condition is the cluster, never the floor -------------------------------

def test_the_wait_never_reads_the_floor_file():
    """The defect in one line. The wait may not open drills/portability-floor.txt, and may not
    branch on the grader's ok/FAIL verdict either -- ok IS "at or above the floor", so exiting on
    it is exiting on the floor by another name."""
    body = "\n".join(l for l in open(WAIT, encoding="utf-8").read().splitlines()
                     if not l.lstrip().startswith("#"))
    assert "portability-floor" not in body, "the wait reads the floor it is supposed to be independent of"
    assert "== ok" not in body and "ok*" not in body, "exiting on the ok verdict is exiting on the floor"


def test_a_run_reports_what_the_cluster_settled_on_not_the_floor(tmp_path):
    """The ratchet, restored. The cluster climbs past the floor and stops; the wait must report the
    number it stopped on. Under the old exit-at-the-floor rule this returned on poll 1 at the floor
    and the run could never beat it -- which is what drills/portability-floor.txt's own "raise it in
    the PR carrying the run URL that beat it" requires it to be able to do."""
    n = _floor()
    calls = tmp_path / "calls"
    _fake_kubectl(tmp_path, [n, n, n + 3], calls)
    out = _run(tmp_path)
    assert out.returncode == 0, out.stderr
    assert "settled after" in out.stdout, out.stdout
    m = re.search(r"ready (\d+)/", out.stdout)
    assert m and int(m.group(1)) == n + 3, (
        "reported %s; the wait stopped before the cluster did" % (m.group(0) if m else out.stdout))


def test_a_cluster_stable_below_the_floor_leaves_at_once_instead_of_burning_the_ceiling(tmp_path):
    """Floor-independence, proved by behaviour rather than by reading the source: a tree that has
    settled BELOW the floor is just as finished as one above it. The old wait had no way to know
    that and sat out the whole ceiling; the grade step FAILs it either way, so the ceiling bought
    nothing. Counted in polls: 3 stable polls and out."""
    n = _floor()
    assert n >= 2, "this case needs a floor with room below it"
    calls = tmp_path / "calls"
    _fake_kubectl(tmp_path, [n - 1], calls)
    out = _run(tmp_path, DRILL_WAIT_MAX="60")
    assert out.returncode == 0, out.stderr
    assert "settled after" in out.stdout, out.stdout
    assert calls.read_text().strip() == "3", (
        "polled %s times; the stability window is 3" % calls.read_text().strip())
    m = re.search(r"ready (\d+)/", out.stdout)
    assert m and int(m.group(1)) == n - 1, out.stdout


def test_a_flat_ready_count_over_a_moving_tree_is_not_settled(tmp_path):
    """`ready` alone is too coarse. Rows can be cascading and pending underneath a ready count that
    has not moved, and leaving then is the same early exit wearing different clothes. The whole
    verdict line is the stability key, so cascaded/pending churn keeps the wait in."""
    body = "\n".join(l for l in open(WAIT, encoding="utf-8").read().splitlines()
                     if not l.lstrip().startswith("#"))
    assert '"$verdict" == "$last"' in body, "the stability key is not the whole verdict line"


def test_an_empty_cluster_never_counts_as_settled(tmp_path):
    """A slow start must not settle at zero. Before Flux applies anything the grader says "no
    Kustomization was applied", which carries no `ready N/M`, so it can never be stable."""
    calls = tmp_path / "calls"
    fake = tmp_path / "kubectl"
    fake.write_text("#!/usr/bin/env bash\necho call >> %s\nprintf '{\"items\":[]}'\n" % calls)
    fake.chmod(0o755)
    out = _run(tmp_path, DRILL_WAIT_MAX="5")
    assert "not settled" in out.stdout, out.stdout
    assert calls.read_text().count("call") > 3, "it stopped polling an empty cluster"


if __name__ == "__main__":
    sys.exit(subprocess.call([sys.executable, "-m", "pytest", "-q", __file__]))
