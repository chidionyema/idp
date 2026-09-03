"""crew#639 CP9: the messaging demo is the estate's contract, not a sketch.

Founder, 2026-08-30: "can you put together a basic demo and an advanced one that uses more
advanced features, eg outbox etc". ADR 0012 locks four decisions (D1 grammar, D2 CloudEvents
binary mode, D3 the outbox is the only path, D8 the stream values). These tests pin the demo to
them so the demo cannot drift into something the platform will not do.

The offline pins read the Go source; the live pin runs the Go suite and both demos when Go is
present (the messaging-demo CI job always has it; the Mac does too). Without Go the live pin is
BLIND and says so, never green.
"""

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MOD = os.path.join(ROOT, "platform", "messaging")


def _read(*parts):
    with open(os.path.join(MOD, *parts), encoding="utf-8") as fh:
        return fh.read()


def _go_files():
    for base, _, files in os.walk(MOD):
        for f in files:
            if f.endswith(".go") and not f.endswith("_test.go"):
                yield (
                    os.path.relpath(os.path.join(base, f), MOD),
                    open(os.path.join(base, f), encoding="utf-8").read(),
                )


def test_the_stream_carries_the_locked_values():
    """D8 and the CP3 scenario: orders.event.>, file store, limits, 30 days, 15 minutes, deny delete and purge, R1."""
    src = _read("cmd", "demo", "main.go")
    cfg = src[src.index("func ordersStream()") : src.index("func main()")]
    for needle in [
        '"orders.event.>"',
        "FileStorage",
        "LimitsPolicy",
        "30 * 24 * time.Hour",
        "15 * time.Minute",
        "DenyDelete: true",
        "DenyPurge: true",
        "Replicas: 1",
    ]:
        assert needle in cfg, needle


def test_only_the_relay_and_the_dlq_processor_publish():
    """D3: the relay is the only writer of events; the DLQ processor the only writer of dlq subjects.
    The demo's own publishes are the seed of the basic demo and the poison message, both as the relay user,
    and the deliberate violation as the service user, which must be refused."""
    publishers = {
        path
        for path, src in _go_files()
        if re.search(r"\.PublishMsg\(|\.Publish\(", src)
    }
    assert publishers == {"outbox/outbox.go", "dlq/dlq.go", "cmd/demo/main.go"}, (
        publishers
    )
    main = _read("cmd", "demo", "main.go")
    assert "nats.ErrPermissionViolation" in main, (
        "the service user's publish around the outbox must be refused, and checked"
    )
    assert 'Deny: []string{"orders.>"' in _read("local", "local.go"), (
        "the app user is denied orders.> by the broker"
    )


def test_every_subject_the_demo_uses_passes_the_grammar():
    """D1 through the one parser: constants go through subject.MustParse, never a raw string on the wire."""
    main = _read("cmd", "demo", "main.go")
    assert 'subject.MustParse("orders.event.order.placed.v1")' in main
    # nats.Msg{Subject: "..."} is a wire subject; FilterSubject and stream Subjects are patterns and may hold >.
    raw = re.findall(r'(?<!Filter)Subject:\s*"([a-z.>]+)"', main)
    assert raw == [], f"raw subject strings on the wire: {raw}"


def test_no_path_is_hardcoded():
    """LAW 46: the cache directory comes from os.UserCacheDir, never a literal home."""
    for path, src in _go_files():
        assert "/Users/" not in src and "/home/" not in src, path
    assert "os.UserCacheDir()" in _read("local", "local.go")


def test_the_go_suite_and_both_demos_are_green():
    """The live pin: the subject fixtures of CP3 and the two demos end in `ok demo`."""
    if shutil.which("go") is None:
        pytest.fail(
            "BLIND: go is not on PATH, the demo cannot be graded here (the messaging-demo CI job grades it)"
        )
    r = subprocess.run(
        ["go", "test", "./..."], cwd=MOD, capture_output=True, text=True, timeout=600
    )
    assert r.returncode == 0, r.stdout + r.stderr
    r = subprocess.run(
        [os.path.join(ROOT, "bin", "idp-messaging-demo"), "all"],
        capture_output=True,
        text=True,
        timeout=900,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    assert (
        "ok demo basic trace=" in r.stdout and "ok demo advanced trace=" in r.stdout
    ), r.stdout
    assert "duplicate=1" in r.stdout and "failed_again=1 effects_in_db=3" in r.stdout, (
        r.stdout
    )


def test_checksum_manifests_are_not_scanned_for_secrets() -> None:
    """idp#901: a go.sum `h1:` hash was read as a generic-api-key and reddened the gate. The secret
    scan skips checksum manifests (gitleaks' own default does, in git mode); rego still reads every
    added line."""
    src = Path(ROOT, "bin", "pr-report").read_text()
    assert "go\\.sum" in src and "pr-added-scan.txt" in src
    assert 'idp-pr-secrets" "$REPORTS/pr-added-scan.txt"' in src
    assert '--rawfile a "$REPORTS/pr-added.txt"' in src
    prog = re.search(r"skip_sums='(.*)'\n", src).group(1)
    diff = "+++ b/platform/messaging/go.sum\n+github.com/x v1 h1:AAAA=\n+++ b/bin/x\n+echo kept\n"
    out = subprocess.run(
        ["awk", prog], input=diff, capture_output=True, text=True, check=True
    ).stdout
    assert out == "+echo kept\n"


def test_the_demo_is_a_catalogued_daily_drill() -> None:
    """drill_named: a platform/ change names a drill in drills/catalogue.yaml; the demo is its own."""
    cat = yaml.safe_load(Path(ROOT, "drills", "catalogue.yaml").read_text())
    row = next(d for d in cat["drills"] if d["name"] == "messaging-demo")
    text = Path(ROOT, ".github", "workflows", row["workflow"]).read_text()
    wf = yaml.safe_load(text)
    assert wf[True]["schedule"][0]["cron"] == row["schedule"]
    assert row["job"] in wf["jobs"]
    assert "bin/idp-messaging-demo all" in text
