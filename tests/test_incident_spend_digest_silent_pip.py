"""2026-09-03: the spend digest never ran once since it landed (idp#1117, 2026-09-02 00:15).

The init container ran `pip install psycopg2-binary >/dev/null 2>&1` with no `set -e` as
uid 10001: pip cannot write /usr/local/lib as non-root, the error was swallowed, and `cp`
then shipped site-packages without psycopg2. The main container died on ModuleNotFoundError
on every scheduled run while the init step read green -- the estate's silent-green class.

The fix installs with --target straight into the writable shared emptyDir, keeps output
visible, and fails the init container loudly if pip fails. This test pins all three.
"""

import yaml


def _pod_specs(node):
    if isinstance(node, dict):
        if "initContainers" in node:
            yield node
        for v in node.values():
            yield from _pod_specs(v)
    elif isinstance(node, list):
        for v in node:
            yield from _pod_specs(v)


def _load():
    with open("platform/llm/spend-breaker-digest.yaml") as f:
        docs = [d for d in yaml.safe_load_all(f) if d]
    return [p for d in docs for p in _pod_specs(d)]


def test_init_installs_loudly_into_the_shared_volume():
    inits = [
        c
        for p in _load()
        for c in p["initContainers"]
        if c["name"] == "setup-python-deps"
    ]
    assert inits, "setup-python-deps init container missing"
    for c in inits:
        script = "\n".join(c["args"])
        assert "set -e" in script, "a failed pip must fail the init container"
        assert "--target /shared/site-packages" in script, (
            "install must target the writable shared volume; uid 10001 cannot "
            "write /usr/local/lib"
        )
        assert "/dev/null" not in script, "the install's output stays visible"


def test_digest_container_reads_the_shared_volume():
    mains = [
        c for p in _load() for c in p.get("containers", []) if c["name"] == "digest"
    ]
    assert mains, "digest container missing"
    assert any(
        e.get("name") == "PYTHONPATH" and e.get("value") == "/shared/site-packages"
        for c in mains
        for e in c.get("env", [])
    )
