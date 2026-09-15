"""Fixture for bin/idp-test-impact --self-test: names one real repo path, so a change to
that path (and only that path) selects this test file."""

import subprocess

subprocess.run(
    ["bin/idp-alert-rows", "platform/alerts/alert.yaml"],  # noqa: S603,S607 -- fixture only
    check=False,
)
