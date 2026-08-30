"""crew#678 CP2 (founder 2026-08-30): self-healing needs a circuit breaker.

The class of mistake, from the CP1 inventory on crew#678: four repair loops with no bound --
a browser bridge restarted every 60 s forever, a launchctl kickstart with no attempt count, and
`helm-retry` in bin/idp-oke-break-glass resetting every failed HelmRelease with no record of
prior tries. A repair loop without a breaker turns one failure into an unbounded one and hides
it behind a green run. Two guards close it: policy/operating_model.rego rule
`self_heal_has_breaker` refuses a pull request that adds a self-healing verb and names no
`Breaker:` line, and this file pins the helm-retry breaker itself (bounded attempts, a cool-off,
the open state on the object, loud when open).
Rung 4: conftest on a fixture; opens no socket.
"""

import json
import pathlib
import re
import shutil
import subprocess

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
POLICY = ROOT / "policy"
FIX = POLICY / "fixtures"
PLAYBOOK = ROOT / "bin/idp-oke-break-glass"

needs_conftest = pytest.mark.skipif(
    shutil.which("conftest") is None, reason="conftest not installed"
)


def _rules(path: pathlib.Path) -> set[str]:
    out = subprocess.run(
        [
            "conftest",
            "test",
            "--parser",
            "json",
            "-p",
            str(POLICY),
            "-o",
            "json",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=False,
    ).stdout
    return {
        f["msg"].split(" | ")[0]
        for r in json.loads(out)
        for f in (r.get("failures") or [])
    }


@needs_conftest
def test_a_self_healing_action_without_a_breaker_line_is_refused():
    assert "rule=self_heal_has_breaker" in _rules(
        FIX / "opmodel-self-heal-no-breaker.json"
    )


@needs_conftest
@pytest.mark.parametrize(
    "fixture", ["opmodel-self-heal-breaker.json", "opmodel-self-heal-alarm.json"]
)
def test_a_counted_breaker_or_a_reasoned_alarm_passes(fixture):
    assert "rule=self_heal_has_breaker" not in _rules(FIX / fixture)


@needs_conftest
def test_a_breaker_line_without_numbers_is_refused(tmp_path):
    d = json.loads((FIX / "opmodel-self-heal-no-breaker.json").read_text())
    d["pr"]["body"] += "Breaker: yes, it retries a few times\n"
    p = tmp_path / "pr.json"
    p.write_text(json.dumps(d))
    assert "rule=self_heal_has_breaker" in _rules(p)


@needs_conftest
def test_the_ok_fixture_still_passes():
    assert not _rules(FIX / "opmodel-ok.json")


def test_helm_retry_is_bounded_with_a_cool_off_and_an_open_state_a_person_can_see():
    src = PLAYBOOK.read_text()
    fn = src[src.index("pb_helm_retry() {") : src.index("pb_k8sgpt_analyze() {")]
    assert 'max_attempts="${HELM_RETRY_MAX:-3}"' in fn
    assert 'cooloff="${HELM_RETRY_COOLOFF_S:-21600}"' in fn
    # the record lives on the object, so the Mac and the workflow read one count
    assert "estate.idp/helm-retry-attempts" in fn and "estate.idp/helm-retry-last" in fn
    # open is loud: printed with its reset command and the playbook goes red
    assert "BREAKER OPEN helm-retry" in fn
    assert re.search(r'step "breaker-open-\$open-releases" sh -c "exit 1"', fn)
    # the reset command is the one a person types, quoted in the comment above the code
    assert (
        "kubectl annotate helmrelease <name> -n <ns> estate.idp/helm-retry-attempts-"
        in fn
    )
