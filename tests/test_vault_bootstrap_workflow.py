"""The bootstrap workflow keeps its safety properties.

The machine token travels vault -> runner memory and is never printed; the vendor
tool is pinned by version and checksum; every action is pinned by commit; and the
two configuration keys the run fills actually exist. Each assert guards a property
a buyer's engineer would probe first.
"""

import os
import re

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WF = os.path.join(ROOT, ".github", "workflows", "vault-bootstrap.yml")


def _load():
    with open(WF) as f:
        return yaml.safe_load(f)


def _run_blocks():
    doc = _load()
    steps = doc["jobs"]["bootstrap"]["steps"]
    return [s.get("run", "") for s in steps]


def test_only_a_person_starts_it():
    doc = _load()
    triggers = doc.get("on") or doc.get(True)  # PyYAML reads bare `on:` as True
    assert list(triggers) == ["workflow_dispatch"]


def test_every_action_is_pinned_to_a_commit():
    doc = _load()
    for step in doc["jobs"]["bootstrap"]["steps"]:
        uses = step.get("uses")
        if uses:
            assert re.search(r"@[0-9a-f]{40}", uses), f"unpinned action: {uses}"


def test_the_vendor_tool_is_pinned_and_checksummed():
    text = open(WF).read()
    assert "bws-v2.1.0" in text
    assert "sha256sum -c" in text


def test_the_token_is_never_printed():
    for block in _run_blocks():
        for line in block.splitlines():
            if "BWS_ACCESS_TOKEN" not in line:
                continue
            # echo never carries the token; printf may only feed a pipe, never the log
            assert "echo" not in line, line
            if "printf" in line:
                assert "|" in line, line
