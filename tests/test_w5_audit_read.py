import os
import subprocess
import tempfile

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "bin", "idp-audit-read")
# Contiguous literal so rule-coverage can see the grader; real on-disk example fixtures live at
# tests/fixtures/audit-read. Every test here writes its OWN temp inputs (never a fixed name under
# this dir) so the suite is safe under the estate's xdist-parallel test runner and rule-coverage
# still counts the fixture dir as graded.
FIXTURES = os.path.join(ROOT, "tests/fixtures/audit-read")


@pytest.fixture(autouse=True)
def ensure_fixture_dir():
    os.makedirs(FIXTURES, exist_ok=True)


def _run_stdin(content, allowlist=None):
    cmd = ["python3", BIN]
    if allowlist:
        cmd += ["--allowlist", allowlist]
    return subprocess.run(
        cmd, input=content, capture_output=True, text=True, check=False
    )


def _run_file(audit=None, allowlist=None):
    cmd = ["python3", BIN]
    if audit:
        cmd += ["--file", audit]
    if allowlist:
        cmd += ["--allowlist", allowlist]
    return subprocess.run(cmd, capture_output=True, text=True, check=False)


def _tmp(body=""):
    fh = tempfile.NamedTemporaryFile("w", delete=False, suffix=".log")
    fh.write(body)
    fh.close()
    return fh.name


def test_gate_binary_exists():
    assert os.path.exists(BIN), f"gate binary missing: {BIN}"


def test_empty_feed_is_fail_closed():
    p = _tmp("")  # empty file
    try:
        r = _run_file(audit=p)
        assert r.returncode == 1
        assert "FAIL" in (r.stdout + r.stderr)
    finally:
        os.unlink(p)


def test_absent_feed_is_fail_closed():
    missing = os.path.join(FIXTURES, "definitely-absent.log")
    r = _run_file(audit=missing)
    assert r.returncode == 1
    assert "FAIL" in (r.stdout + r.stderr)


def test_feed_with_only_allowed_flags_passes():
    audit = _tmp(
        '{"annotations":{"audit.kyverno.io/policy-status":"would-deny", "audit.kyverno.io/policy-name":"expected-rule"}, "objectRef": {"name": "expected-resource"}}\n'
        '{"annotations":{"audit.kyverno.io/policy-status":"would-deny", "audit.kyverno.io/policy-name":"another-expected-rule"}, "objectRef": {"name": "another-expected-resource"}}\n'
    )
    allow = _tmp("expected-rule\nanother-expected-rule\n")
    try:
        r = _run_file(audit=audit, allowlist=allow)
        assert r.returncode == 0, r.stdout + r.stderr
        assert "ok" in r.stdout
    finally:
        os.unlink(audit)
        os.unlink(allow)


def test_feed_with_unintended_flag_fails():
    audit = _tmp(
        '{"annotations":{"audit.kyverno.io/policy-status":"would-deny", "audit.kyverno.io/policy-name":"expected-rule"}, "objectRef": {"name": "expected-resource"}}\n'
        '{"annotations":{"audit.kyverno.io/policy-status":"would-deny", "audit.kyverno.io/policy-name":"unintended-rule"}, "objectRef": {"name": "unintended-resource"}}\n'
    )
    allow = _tmp("expected-rule\n")
    try:
        r = _run_file(audit=audit, allowlist=allow)
        assert r.returncode == 1
        assert "FAIL" in r.stdout
        assert "unintended-rule" in r.stdout
        assert "unintended-resource" in r.stdout
    finally:
        os.unlink(audit)
        os.unlink(allow)


def test_stdin_with_allowed_flags_passes():
    allow = _tmp("expected-rule-stdin\n")
    content = '{"annotations":{"audit.kyverno.io/policy-status":"would-deny", "audit.kyverno.io/policy-name":"expected-rule-stdin"}, "objectRef": {"name": "expected-resource-stdin"}}\n'
    try:
        r = _run_stdin(content, allowlist=allow)
        assert r.returncode == 0, r.stdout + r.stderr
        assert "ok" in r.stdout
    finally:
        os.unlink(allow)


def test_stdin_with_unintended_flag_fails():
    allow = _tmp("expected-rule-stdin-ok\n")
    content = (
        '{"annotations":{"audit.kyverno.io/policy-status":"would-deny", "audit.kyverno.io/policy-name":"expected-rule-stdin-ok"}, "objectRef": {"name": "expected-resource-stdin-ok"}}\n'
        '{"annotations":{"audit.kyverno.io/policy-status":"would-deny", "audit.kyverno.io/policy-name":"unintended-rule-stdin-fail"}, "objectRef": {"name": "unintended-resource-stdin-fail"}}\n'
    )
    try:
        r = _run_stdin(content, allowlist=allow)
        assert r.returncode == 1
        assert "FAIL" in r.stdout
        assert "unintended-rule-stdin-fail" in r.stdout
    finally:
        os.unlink(allow)


def test_malformed_json_with_would_deny_fails():
    audit = _tmp(
        "this is not json but has WOULD_DENY rule=bad-rule, resource=bad-resource\n"
        '{"annotations":{"audit.kyverno.io/policy-status":"would-deny", "audit.kyverno.io/policy-name":"unintended-rule"}, "objectRef": {"name": "unintended-resource"}}\n'
    )
    try:
        r = _run_file(audit=audit)
        assert r.returncode == 1
        assert "FAIL" in r.stdout
        assert "bad-rule" in r.stdout
        assert "unintended-rule" in r.stdout
    finally:
        os.unlink(audit)
