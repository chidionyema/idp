"""The Flux alarm opens one issue per fire, not one per Kustomization.

On 2026-09-08 a single broken namespace fence put 33 open P0 issues on the board. Every one was
true and every one described the same fire; the founder read 33 rows and could not see there was
one. The alarm deduped on the object, and the object is only where the fire was noticed.

These tests run the workflow's own jq normaliser -- read out of flux-events.yml, not copied here,
so the two cannot drift -- over the 33 real messages that were on the board that day, and fail if
it stops folding them.
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "flux-events.yml"
FIXTURE = ROOT / "tests" / "fixtures" / "flux-one-fire-2026-09-08.json"

pytestmark = pytest.mark.skipif(
    shutil.which("jq") is None, reason="jq is the alarm's runtime"
)


def _signature_program() -> str:
    return yaml.safe_load(WORKFLOW.read_text())["jobs"]["ledger"]["env"]["SIGNATURE_JQ"]


def _signature(message: str) -> str:
    out = subprocess.run(
        ["jq", "-r", _signature_program()],
        input=json.dumps({"message": message}),
        capture_output=True,
        text=True,
        check=True,
    )
    return out.stdout.strip()


def _board() -> list[dict]:
    return json.loads(FIXTURE.read_text())


def test_the_board_that_day_folds_to_fewer_than_half_its_rows():
    """33 rows to 15. Not to 1: the remaining 15 are genuinely different faults -- a missing CRD,
    an invalid hostname, six different unreachable webhooks -- and folding those together would
    hide fires, which is the opposite failure and the worse one."""
    board = _board()
    assert len(board) == 33, "the fixture is the board as it stood; it is not edited"
    fires = {_signature(row["message"]) for row in board}
    assert len(fires) <= len(board) // 2, (
        f"{len(fires)} rows for 33 events. The normaliser is leaving something in the message "
        "that identifies the Kustomization rather than the failure."
    )


def test_the_largest_fire_is_one_row_and_not_nine():
    """Nine Kustomizations could not download their artifact from the same unreachable source
    controller. That is one fire and it was nine rows on the board."""
    counts: dict[str, int] = {}
    for row in _board():
        counts[_signature(row["message"])] = (
            counts.get(_signature(row["message"]), 0) + 1
        )
    assert max(counts.values()) >= 9


def test_a_list_of_waiting_objects_is_one_fire_however_long_it_is():
    """`timeout waiting for: [A, B]` and `[A, B, C, D, E]` are the same stalled rollout. Grading
    them apart put three rows on the board for one health check."""
    two = _signature(
        "health check failed after 5m0s: timeout waiting for: "
        "[Deployment/a/b status: 'InProgress', Deployment/c/d status: 'InProgress']"
    )
    five = _signature(
        "health check failed after 9m1s: timeout waiting for: "
        "[Deployment/a/b status: 'InProgress', Deployment/c/d status: 'InProgress', "
        "Deployment/e/f status: 'InProgress', Deployment/g/h status: 'InProgress', "
        "Deployment/i/j status: 'InProgress']"
    )
    assert two == five


def test_one_webhook_down_reads_the_same_however_the_dial_failed():
    """The same unreachable webhook answers `context deadline exceeded` on one call and
    `TLS handshake timeout` on the next. Two rows, one fire."""
    a = _signature(
        'Issuer/x/y dry-run failed: failed calling webhook "webhook.cert-manager.io": '
        'failed to call webhook: Post "https://z/validate?timeout=30s": context deadline exceeded'
    )
    b = _signature(
        'Issuer/p/q dry-run failed: failed calling webhook "webhook.cert-manager.io": '
        'failed to call webhook: Post "https://z/validate?timeout=10s": net/http: TLS handshake timeout'
    )
    assert a == b


def test_the_same_failure_on_two_objects_is_one_fire():
    a = _signature(
        "Deployment/backstage/catalogue dry-run failed (InternalError): Internal error occurred: "
        'failed calling webhook "mutate.kyverno.svc-fail"'
    )
    b = _signature(
        "CronJob/staging/canary-scheduler dry-run failed (InternalError): Internal error occurred: "
        'failed calling webhook "mutate.kyverno.svc-fail"'
    )
    assert a == b


def test_two_different_failures_stay_two_fires():
    a = _signature(
        'Issuer/x/y dry-run failed: failed calling webhook "webhook.cert-manager.io"'
    )
    b = _signature(
        "health check failed after 5m0s: timeout waiting for: [Deployment/x status]"
    )
    assert a != b


def test_the_alarm_matches_the_marker_it_writes():
    """The body carries `flux-signature: <16 hex>` and the lookup greps for that same string. If
    one side changes shape the alarm silently opens a new issue every time -- which is the bug
    this change removes, wearing a different hat."""
    steps = yaml.safe_load(WORKFLOW.read_text())["jobs"]["ledger"]["steps"]
    scripts = [s["run"] for s in steps if "run" in s]
    writes = [s for s in scripts if "gh issue create" in s]
    assert writes, "no step opens an issue"
    for script in writes:
        assert 'marker="flux-signature: ' in script
        assert '"$marker"' in script, "the marker is written into the body"
        assert 'contains(\\"$marker\\")' in script, (
            "the lookup greps for the marker it wrote"
        )
