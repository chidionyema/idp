"""crew#307, 2026-08-28. A red that only means the VM was slow.

`kubectl wait --all` resolves its selector ONCE. An empty set is not "keep waiting", it is
`error: no matching resources found` and exit 1, and `--timeout` never enters into it. In
portability-drill run 33162838535 the k3s systemd unit had been up for eleven seconds and had not
yet registered its Node, so `kubectl wait node --all --for=condition=Ready --timeout=120s` failed
at 10:18:32Z on a perfectly healthy cluster and the second provider went unproved.

The cost is not the minute. A check that goes red on how fast a runner happens to be teaches every
session to press re-run without reading, which is how a real red eventually gets pressed through
too -- so this is graded, not tolerated.

The rule: a `kubectl wait ... --all` whose failure stops the job must first wait for at least one
of the resources to EXIST. A `|| true` line is exempt: it has already said it tolerates an empty
set. This walks every workflow, so the shape cannot be reintroduced in a new job.
"""
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
WORKFLOWS = sorted((ROOT / ".github" / "workflows").glob("*.y*ml"))
WAIT_ALL = re.compile(r"kubectl\s+wait\s+(\S+)\s+--all\b")
# `until kubectl get node -o name | grep -q .` and friends: any loop that blocks on the same kind
# appearing. The kind must match the kind being waited on, or the loop guards nothing.
EXISTS = "kubectl get {kind}"


def test_there_are_workflows_to_grade():
    """A sweep that finds no files is not a sweep (crew#539: BLIND is never a pass)."""
    assert WORKFLOWS, "no workflow files found to grade"


def test_no_wait_all_can_fail_on_a_resource_that_has_not_appeared_yet():
    offenders = []
    for wf in WORKFLOWS:
        lines = wf.read_text().splitlines()
        for i, line in enumerate(lines):
            m = WAIT_ALL.search(line)
            if not m or "|| true" in line:
                continue
            kind = m.group(1)
            preceding = "\n".join(lines[max(0, i - 12):i])
            if EXISTS.format(kind=kind) in preceding:
                continue
            offenders.append(f"{wf.relative_to(ROOT)}:{i + 1}: {line.strip()}")
    assert not offenders, (
        "`kubectl wait --all` fails immediately when nothing matches yet -- --timeout does not "
        "cover a resource that has not been created. Block on it existing first, e.g.\n"
        "    until kubectl get <kind> -o name 2>/dev/null | grep -q .; do sleep 2; done\n"
        "or append `|| true` if an empty set is genuinely acceptable here (crew#307).\n  "
        + "\n  ".join(offenders))
