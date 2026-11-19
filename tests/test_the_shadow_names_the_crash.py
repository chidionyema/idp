"""The refusal dump records the crash, not the restart that followed it.

MEASURED 2026-11-18: a base shadow run refused with
`container litellm is CrashLoopBackOff (restarts 3)` and the dump kept 50 log
lines, none of which carried the crash. Three root causes were argued out of
that gap -- a missing database stand-in, the CustomLogger callback, a stale base
-- and all three were wrong.

`dump_why` is a diagnostic, so it has no natural failure of its own: it fails by
printing a restart banner where the crash should be, and nothing notices.
A smoke test that only checks "it printed something" passes on exactly that bug,
so this test is a falsifier: the fake kubelet answers `logs` twice with two
different bodies -- the restart on the current attempt, the crash on the
previous one -- and the assertions are about which body reached the output.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

RESTART = "restart 3: litellm is up, waiting for the next probe"
CRASH = "CRASH litellm: ModuleNotFoundError: No module named 'estate_aei.observer'"
REASON = "Error exit=1 reason=ModuleNotFoundError"


def load_shadow():
    loader = importlib.machinery.SourceFileLoader(
        "idp_shadow_dump", str(REPO / "bin" / "idp-shadow")
    )
    spec = importlib.util.spec_from_loader("idp_shadow_dump", loader)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


class Result:
    def __init__(self, stdout):
        self.stdout = stdout
        self.returncode = 0


DESCRIBE = """Name: litellm-79977d7b44-jptlj
Namespace: llm
Containers:
  litellm:
    Image: ghcr.io/chidionyema/litellm:main-1-abc
    State: Waiting
      Reason: CrashLoopBackOff
    Last State: Terminated
      Reason: Error
      Exit Code: 1
Events:
  Warning BackOff kubelet Back-off restarting failed container
"""


def fake_kubelet(calls):
    def run(argv, **_kw):
        calls.append(list(argv))
        argv = list(argv)
        if "logs" in argv:
            return Result(CRASH if "--previous" in argv else RESTART)
        if "describe" in argv:
            return Result(DESCRIBE)
        if "-A" in argv:
            return Result("llm/litellm-79977d7b44-jptlj\n")
        if "get" in argv:
            return Result(REASON)
        return Result("")

    return run


def test_the_dump_prints_the_previous_containers_log_and_why_it_died(
    monkeypatch, capsys
):
    shadow = load_shadow()
    calls = []
    monkeypatch.setattr(shadow.subprocess, "run", fake_kubelet(calls))

    shadow.dump_why()

    out = capsys.readouterr().out
    current, _, previous = out.partition("--- logs (previous, the crash)")

    # the crash is in the previous section, and the restart did not stand in for it
    assert CRASH in previous, out
    assert CRASH not in current, "the restart was presented as the crash"
    assert RESTART in current, out

    # the state that only lastState carries, and the pod's own Events
    assert REASON in out, out
    assert "Back-off restarting failed container" in out, out

    # both logs were actually asked for, previous included
    logs = [c for c in calls if "logs" in c]
    assert logs and all("--previous" in c for c in logs[1:]), calls
    assert "--all-containers" in logs[0], calls


def test_a_dump_never_raises_when_kubectl_cannot_be_run(monkeypatch, capsys):
    shadow = load_shadow()

    def gone(argv, **_kw):
        raise FileNotFoundError(2, "No such file or directory", argv[0])

    monkeypatch.setattr(shadow.subprocess, "run", gone)
    shadow.dump_why()
    assert "dump failed" in capsys.readouterr().out
