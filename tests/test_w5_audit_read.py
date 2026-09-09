import os
import subprocess
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "bin", "idp-audit-read")
FIXTURES = os.path.join(ROOT, "tests", "fixtures", "audit-read")


@pytest.fixture(autouse=True)
def create_fixture_dir():
    os.makedirs(FIXTURES, exist_ok=True)


def _invoke(audit_file_path=None, allowlist_file_path=None, stdin_content=None):
    cmd = ["python3", BIN]
    if audit_file_path:
        cmd.extend(["--file", audit_file_path])
    if allowlist_file_path:
        cmd.extend(["--allowlist", allowlist_file_path])

    if stdin_content:
        process = subprocess.run(
            cmd, input=stdin_content, capture_output=True, text=True, check=False
        )
    else:
        process = subprocess.run(cmd, capture_output=True, text=True, check=False)
    return process


def test_gate_binary_exists():
    assert os.path.exists(BIN), f"gate binary missing: {BIN}"


def test_empty_feed_is_fail_closed():
    # An empty file should be a FAIL
    empty_file = os.path.join(FIXTURES, "empty.log")
    # create an empty file (no content to write, so no handler binding needed)
    open(empty_file, "w").close()
    r = _invoke(audit_file_path=empty_file)
    assert r.returncode == 1
    assert "FAIL: Empty or absent audit feed." in r.stderr


def test_absent_feed_is_fail_closed():
    # An absent file should be a FAIL
    r = _invoke(audit_file_path=os.path.join(FIXTURES, "non_existent.log"))
    assert r.returncode == 1
    assert "FAIL: Audit log file not found" in r.stderr


def test_feed_with_only_allowed_flags_passes():
    allowed_flags_log = os.path.join(FIXTURES, "allowed_flags.log")
    allowlist_file = os.path.join(FIXTURES, "allowlist.txt")

    with open(allowed_flags_log, "w") as f:
        f.write(
            '{"annotations":{"audit.kyverno.io/policy-status":"would-deny", "audit.kyverno.io/policy-name":"expected-rule"}, "objectRef": {"name": "expected-resource"}}\n'
        )
        f.write(
            '{"annotations":{"audit.kyverno.io/policy-status":"would-deny", "audit.kyverno.io/policy-name":"another-expected-rule"}, "objectRef": {"name": "another-expected-resource"}}\n'
        )

    with open(allowlist_file, "w") as f:
        f.write("expected-rule\n")
        f.write("another-expected-rule\n")

    r = _invoke(audit_file_path=allowed_flags_log, allowlist_file_path=allowlist_file)
    assert r.returncode == 0
    assert "ok" in r.stdout


def test_feed_with_unintended_flag_fails():
    unintended_flag_log = os.path.join(FIXTURES, "unintended_flag.log")
    allowlist_file = os.path.join(FIXTURES, "allowlist.txt")

    with open(unintended_flag_log, "w") as f:
        f.write(
            '{"annotations":{"audit.kyverno.io/policy-status":"would-deny", "audit.kyverno.io/policy-name":"expected-rule"}, "objectRef": {"name": "expected-resource"}}\n'
        )
        f.write(
            '{"annotations":{"audit.kyverno.io/policy-status":"would-deny", "audit.kyverno.io/policy-name":"unintended-rule"}, "objectRef": {"name": "unintended-resource"}}\n'
        )

    with open(allowlist_file, "w") as f:
        f.write("expected-rule\n")

    r = _invoke(audit_file_path=unintended_flag_log, allowlist_file_path=allowlist_file)
    assert r.returncode == 1
    assert "FAIL: Unintended WOULD_DENY flags found:" in r.stdout
    assert "unintended-rule" in r.stdout
    assert "unintended-resource" in r.stdout


def test_stdin_with_allowed_flags_passes():
    allowlist_file = os.path.join(FIXTURES, "allowlist_stdin.txt")
    with open(allowlist_file, "w") as f:
        f.write("expected-rule-stdin\n")

    stdin_content = '{"annotations":{"audit.kyverno.io/policy-status":"would-deny", "audit.kyverno.io/policy-name":"expected-rule-stdin"}, "objectRef": {"name": "expected-resource-stdin"}}\n'
    r = _invoke(allowlist_file_path=allowlist_file, stdin_content=stdin_content)
    assert r.returncode == 0
    assert "ok" in r.stdout


def test_stdin_with_unintended_flag_fails():
    allowlist_file = os.path.join(FIXTURES, "allowlist_stdin_fail.txt")
    with open(allowlist_file, "w") as f:
        f.write("expected-rule-stdin-fail\n")

    stdin_content = (
        '{"annotations":{"audit.kyverno.io/policy-status":"would-deny", "audit.kyverno.io/policy-name":"expected-rule-stdin-fail"}, "objectRef": {"name": "expected-resource-stdin-fail"}}\n'
        '{"annotations":{"audit.kyverno.io/policy-status":"would-deny", "audit.kyverno.io/policy-name":"unintended-rule-stdin-fail"}, "objectRef": {"name": "unintended-resource-stdin-fail"}}\n'
    )

    r = _invoke(allowlist_file_path=allowlist_file, stdin_content=stdin_content)
    assert r.returncode == 1
    assert "FAIL: Unintended WOULD_DENY flags found:" in r.stdout
    assert "unintended-rule-stdin-fail" in r.stdout
    assert "unintended-resource-stdin-fail" in r.stdout


def test_malformed_json_with_would_deny_fails():
    malformed_log = os.path.join(FIXTURES, "malformed.log")
    with open(malformed_log, "w") as f:
        f.write(
            "this is not json but has WOULD_DENY rule=bad-rule, resource=bad-resource\n"
        )
        f.write(
            '{"annotations":{"audit.kyverno.io/policy-status":"would-deny", "audit.kyverno.io/policy-name":"unintended-rule"}, "objectRef": {"name": "unintended-resource"}}\n'
        )

    r = _invoke(audit_file_path=malformed_log)
    assert r.returncode == 1
    assert "FAIL: Unintended WOULD_DENY flags found:" in r.stdout
    assert "bad-rule" in r.stdout
    assert "unintended-rule" in r.stdout
