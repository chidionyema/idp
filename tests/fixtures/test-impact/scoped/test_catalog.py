"""Fixture for bin/idp-test-impact --self-test: names a different real repo path, so it must
NOT be selected by a change under platform/alerts/."""

import subprocess

subprocess.run(
    ["bin/idp-catalog-gen", "catalog/estate.db"],  # noqa: S603,S607 -- fixture only
    check=False,
)
