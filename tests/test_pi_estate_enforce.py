"""pi-estate-enforce (idp#7006): pi agents get the estate's write-side gates, and the rules
stay in one place.

The claim write gate and the write-back stop gate are bin/estate-memory-enforce's decisions. pi
has no hooks, so it reaches that binary through an extension: the extension renders pi's session
into the transcript the binary reads and turns the binary's answer into pi's two refusals. The
seam is pure TypeScript with no pi import, so it runs under node's own test runner; this wrapper
makes it part of the python suite, which is the one the gates run. Skipped only when node itself
is absent or too old for --experimental-strip-types (22.6+), the same convention as the plan-lock
and kustomize tests.
"""

import json
import pathlib
import re
import shutil
import subprocess

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
EXT = ROOT / "extensions" / "pi-estate-enforce"
MANIFEST = ROOT / "platform" / "estate" / "memory" / "runtimes.json"


def _node_ok() -> bool:
    node = shutil.which("node")
    if not node:
        return False
    out = subprocess.run([node, "--version"], capture_output=True, text=True).stdout
    m = re.match(r"v(\d+)\.(\d+)", out.strip())
    return bool(m) and (int(m[1]), int(m[2])) >= (22, 6)


@pytest.mark.skipif(not _node_ok(), reason="node >= 22.6 is not installed")
def test_the_transport_rules_hold():
    r = subprocess.run(
        [
            "node",
            "--experimental-strip-types",
            "--no-warnings",
            "--test",
            str(EXT / "hook.test.ts"),
        ],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-1500:]
    assert re.search(r"# pass [1-9]", r.stdout), "node ran no tests: " + r.stdout[-500:]


def test_the_extension_calls_the_estate_binary_and_refuses_in_pis_own_terms():
    """The pure seam is only a gate if index.ts actually calls the binary and obeys it."""
    src = (EXT / "index.ts").read_text()
    for needle in (
        "estate-memory-enforce",
        '"pre"',
        '"stop"',
        "block: true",
        "sendUserMessage",
        "renderTranscript",
        "parseDeny",
        "parseBlock",
    ):
        assert needle in src, (
            f"index.ts never uses {needle}: the gate exists and nothing enforces it"
        )


def _code(src: str) -> str:
    """The source without its comments: prose may name the files that hold the rules."""
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    return "\n".join(line.split("//")[0] for line in src.splitlines())


def test_the_extension_decides_nothing_itself():
    """One rule decides for every runtime. A second copy in the extension is stitching."""
    src = _code((EXT / "index.ts").read_text()) + _code((EXT / "hook.ts").read_text())
    for forbidden in (
        "live_focus",
        "focus.py",
        "fnmatch",
        "claim_state",
        "FOCUS_CLAIM",
        "git_root_if_idp",
        "BRIEFED",
        "WROTE_BACK",
    ):
        assert forbidden not in src, (
            f"the extension contains {forbidden}: the decision belongs to "
            "bin/estate-memory-enforce, not to a second implementation"
        )
    # the binary is the one it asks, and the copy every runtime runs -- not a checkout
    assert "ESTATE_MEMORY_HOME" in src
    assert "Documents" not in src, "the extension must not read a checkout"


def test_the_manifest_points_pi_at_the_same_binary_through_the_extension():
    manifest = json.loads(MANIFEST.read_text())
    pi = manifest["runtimes"]["pi"]
    links = [e for e in pi.get("enforce", []) if e.get("kind") == "link"]
    assert links, "pi has no way to reach the write-side gates"
    assert links[0]["source"] == "extensions/pi-estate-enforce"
    assert links[0]["dest"] == "~/.pi/agent/extensions/pi-estate-enforce"
    # the same binary the other runtimes use
    assert manifest["enforce"]["bin"] == "bin/estate-memory-enforce"
    assert "pre" in {h["arg"] for h in manifest["enforce"]["hooks"]}
    assert "stop" in {h["arg"] for h in manifest["enforce"]["hooks"]}


def test_the_installer_copies_the_extension_into_the_home_and_links_it():
    src = (ROOT / "bin" / "estate-memory-install").read_text()
    assert 'rt.get("enforce", [])' in src, (
        "the installer never links the enforce transport"
    )
    assert "extensions/pi-estate-enforce" not in src, (
        "the installer must read the path from the manifest, not repeat it"
    )
