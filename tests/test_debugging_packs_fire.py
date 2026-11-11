"""A debugging pack is only a pack if it FIRES. This file proves it, one defect at a time.

The founder's instruction (2026-11-10) was not "write down what went wrong", it was "all edge cases
and all known and reached failure modes must be addressed and used as debugging packs for any
future issues". A pack that cannot fire is a paragraph; a pack whose falsifier goes red when the
defect is reintroduced is an instrument. AGENTS.md section 9 P1: a gate that cannot fail is not a
gate -- applied to the index itself.

Each mutation test copies the repository's relevant parts to a throwaway root, reintroduces the
ORIGINAL defect there, and asserts the named falsifier goes red. The estate is never mutated, so a
failure here always means the pack is broken, never that the repository was damaged.
"""

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

IDP = Path(__file__).resolve().parents[1]
PACKS = json.loads((IDP / "docs" / "debugging-packs.json").read_text())["packs"]
COPIES = ("bin", "platform", "clusters", "tests", "conftest.py")


def pack(pid):
    for p in PACKS:
        if p["id"] == pid:
            return p
    raise AssertionError(f"no pack {pid}")


def clone_root(tmp_path: Path) -> Path:
    """A throwaway tree with enough of the repo for the door to import and the test to run."""
    root = tmp_path / "idp"
    root.mkdir()
    for name in COPIES:
        src = IDP / name
        if not src.exists():
            continue
        if src.is_dir():
            shutil.copytree(
                src,
                root / name,
                dirs_exist_ok=True,
                ignore=shutil.ignore_patterns("node_modules", "__pycache__"),
            )
        else:
            shutil.copy2(src, root / name)
    return root


def run_pytest(root: Path, target: str):
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            target,
            "-q",
            "--no-header",
            "-p",
            "no:cacheprovider",
        ],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=180,
    )


def sub1(body: str, pattern: str, repl: str):
    """Replace exactly once, and say so when the site has moved -- a silent no-op mutation would
    make every test below pass for the wrong reason."""
    out, n = re.subn(pattern, repl, body, count=1)
    assert n == 1, (
        "the defect site moved; update the pack rather than deleting the mutation"
    )
    return out


# ---- DBG-002: drop the OCI profile pin and the ordering falsifier must go red ---------------
def test_dbg_002_fires_when_the_profile_pin_is_removed(tmp_path):
    root = clone_root(tmp_path)
    door = root / "bin" / "idp-edge-cutover"
    mutated = sub1(
        door.read_text(),
        r'env\.setdefault\("OCI_CLI_PROFILE", "DEFAULT"\)',
        'env["OCI_CLI_PROFILE"] = os.environ.get("OCI_CLI_PROFILE", "")  # DEFECT',
    )
    door.write_text(mutated)
    out = run_pytest(
        root, "tests/test_edge_cutover.py::test_vault_get_pins_the_oci_profile"
    )
    assert out.returncode != 0, (
        "the pin's falsifier stayed green on the reintroduced defect"
    )


# ---- DBG-003: trust __file__ with no probe and the root falsifier must go red --------------
def test_dbg_003_fires_when_idp_root_trusts_file(tmp_path):
    root = clone_root(tmp_path)
    door = root / "bin" / "idp-edge-cutover"
    mutated = sub1(
        door.read_text(),
        r"    root = Path\(__file__\)\.resolve\(\)\.parent\.parent\n(?:.*\n)*?    return root\n",
        "    return Path(__file__).resolve().parent.parent  # DEFECT: never probed\n",
    )
    door.write_text(mutated)
    out = run_pytest(
        root,
        "tests/test_edge_cutover.py::test_idp_root_names_itself_when_it_is_not_in_a_checkout",
    )
    assert out.returncode != 0, (
        "the root probe's falsifier stayed green on the reintroduced defect"
    )


# ---- DBG-001: return "" for a non-JSON vault body and the bare-value falsifier must go red ---
# The measured defect, verbatim: a non-JSON body was treated as a missing value instead of as the
# bare value it is. That one line answered "the vault holds no cloudflare-api-token" for a token
# sitting right there in the vault, and sent the next step off to mint a duplicate credential.
def test_dbg_001_fires_when_vault_parsing_is_json_only(tmp_path):
    root = clone_root(tmp_path)
    door = root / "bin" / "idp-edge-cutover"
    mutated = sub1(
        door.read_text(),
        r"    except \(ValueError, AttributeError\):\n        return raw.*\n",
        '    except (ValueError, AttributeError):\n        return ""  # DEFECT: JSON-only\n',
    )
    door.write_text(mutated)
    out = run_pytest(
        root,
        "tests/test_edge_cutover.py::test_vault_get_returns_a_bare_value_not_only_json",
    )
    assert out.returncode != 0, (
        "the bare-value falsifier stayed green on a JSON-only vault reader, so DBG-001 is a "
        "paragraph rather than a pack"
    )


# ---- DBG-005: a lane addressed by index is the defect; the test file must be clean of it ----
def test_dbg_005_fires_when_a_lane_is_addressed_by_index():
    path = IDP / "platform" / "lifeboat" / "test" / "lifeboat.test.mjs"
    offenders = [
        l.strip()
        for l in path.read_text().splitlines()
        if re.search(r"\bLANES\[\d\]", l) and not l.lstrip().startswith("//")
    ]
    assert not offenders, (
        "a lane is addressed by position again, so inserting a lane silently re-points the test "
        f"at a different lane: {offenders}"
    )


# ---- DBG-006: the preflight must tolerate Cloudflare's unauthenticated 403 -----------------
def test_dbg_006_tolerates_the_unauthenticated_answer_and_skips_the_console_on_road_a():
    body = (IDP / "bin" / "idp-bootstrap-cloudflare").read_text()
    assert re.search(r"200\|301\|302\|303\|403", body), (
        "the preflight no longer accepts 403 as the unauthenticated answer"
    )
    assert "not required" in body, (
        "road a no longer states that the dashboard console is not consulted"
    )


# ---- DBG-010: the executor's bound is genuine, not raised away -----------------------------
def test_dbg_010_the_ceiling_is_still_a_ceiling():
    body = (IDP / "platform" / "estate" / "bin" / "estate-execute").read_text()
    assert re.search(r"CEILING_\w*\s*=|ceiling", body, re.I), (
        "the executor no longer declares a ceiling; ETIMEDOUT/124 would have no bound to fire"
    )


# ---- DBG-011/012/017: the guard exists and its falsifiers are real -------------------------
def test_dbg_011_012_017_point_at_the_real_guard():
    assert (IDP / "platform" / "estate" / "governance" / "thin_client.py").exists()
    for pid in ("DBG-011", "DBG-012", "DBG-017"):
        target = pack(pid)["falsifier"].split("::")[0].split("#")[0]
        assert (IDP / target).exists(), (
            f"{pid} points at {target}, which does not exist"
        )


# ---- every pack, structurally: usable at 3am by an agent who was not here ------------------
def test_every_pack_is_usable_by_an_agent_who_was_not_here():
    """symptom greppable, cause a mechanism, remedy naming a concrete artefact.

    "Concrete" is deliberately wider than "a filename": a remedy that says `growmos context`,
    `lane-submit`, `road a`, `thin_client.applies()` or `test_the_door_parses_as_python` is one a
    reader can act on, and forcing every remedy to cite a path would push authors to pad prose
    with a filename that is not the thing to change. What is refused is a mood.
    """
    concrete = re.compile(
        r"[\w./-]+\.(py|js|mjs|json|toml|yaml|yml|sql|sh)"  # a file
        r"|\bbin/"  # a repo script
        r"|\bgh \w+"  # a gh subcommand
        r"|--\w+"  # a flag
        r"|`[^`]+`"  # a quoted artefact
        r"|\b[a-z_]+\.[a-z_]+\.[a-z_]+\b"  # dotted: thin_client.applies
        r"|\b[a-z_]+\.[a-z_]+\(\)"  # a call: env.setdefault()
        r"|\btest_\w+"  # a named falsifier
        r"|[A-Z][A-Z0-9_]{4,}\b"  # a constant/lane/env name
    )
    for p in PACKS:
        assert len(p["symptom"]) > 10, f"{p['id']}: symptom too thin to grep"
        assert len(p["cause"]) > 40, f"{p['id']}: cause is not a mechanism"
        assert concrete.search(p["remedy"]), (
            f"{p['id']}: remedy names no concrete artefact a reader can act on: {p['remedy']!r}"
        )


def test_pack_status_vocabulary_is_closed():
    allowed = {"fixed", "external", "diagnosed", "open"}
    bad = {p["id"]: p["status"] for p in PACKS if p["status"] not in allowed}
    assert not bad, f"packs with an unknown status: {bad}"


def test_the_index_is_loadable_as_data_by_any_runtime():
    """The pack must be consumable by a door, not only read by a human."""
    raw = (IDP / "docs" / "debugging-packs.json").read_text()
    data = json.loads(raw)
    assert data["version"] >= 1
    assert isinstance(data["packs"], list) and len(data["packs"]) >= 18
