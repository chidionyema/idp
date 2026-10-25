"""The estate's skill packs are one governed layer, and the layer can fail (idp#6987).

The founder asked for the twelve UI/design/research/architecture capabilities to reach
every estate agent. The tempting way to do that is to let each runtime install what it
likes: then the estate grows eleven copies of one capability, in eleven places, at
eleven versions (AGENTS.md §6). So the packs live in idp, once, and the only way to
put one in front of an agent is the installer -- which verifies every file against the
registry's sha256 before it writes a byte, and only writes into the four allowlisted
runtime roots.

That contract is only worth anything if it can fail. Each test below proves one way it
fails: a drifted pack, a tampered pack, a runtime outside the allowlist, a pack with a
broken front door, a pack with no licence, an intent that does not exist. The registry
is the contract; the tests are the gate that keeps the contract true.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SKILLS = REPO / "platform" / "estate" / "skills"
CLI = REPO / "platform" / "estate" / "libexec" / "skill-packs.py"

# The founder's twelve, each pinned to the repository it came from.
TWELVE = {
    "ui-ux-pro-max": "nextlevelbuilder/ui-ux-pro-max-skill",
    "awesome-design-md": "VoltAgent/awesome-design-md",
    "open-design": "nexu-io/open-design",
    "taste": "Leonxlnx/taste-skill",
    "impeccable": "pbakaus/impeccable",
    "react-bits": "DavidHDev/react-bits",
    "emil-design-skills": "emilkowalski/skills",
    "hallmark": "Nutlope/hallmark",
    "design-md": "google-labs-code/design.md",
    "gsap-skills": "greensock/gsap-skills",
    "scroll-world": "oso95/scroll-world",
    "canvas-ui": "DavidHDev/canvas-ui",
}

# The two the estate writes itself, because no upstream was named for them.
NATIVE = {"estate-research": "research", "estate-architecture": "architecture"}

# The runtime roots the installer may write into. A closed set, and the installer has no
# --dest, so there is no way to point it somewhere else.
RUNTIMES = {
    "pi": ".pi/agent/skills",
    "claude": ".claude/skills",
    "codex": ".codex/skills",
    "agents": ".agents/skills",
}


def run(*args: str, skills: Path = SKILLS, home: Path | None = None):
    env = dict(os.environ)
    env["ESTATE_SKILLS_DIR"] = str(skills)
    cmd = [sys.executable, str(CLI)]
    if home is not None:
        cmd += ["--home", str(home)]
    cmd += list(args)
    return subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=120)


def registry(skills: Path = SKILLS) -> dict:
    return json.loads((skills / "registry.json").read_text())


# --- the registry ---------------------------------------------------------------
def test_the_registry_holds_the_twelve_upstream_packs_and_the_two_estate_ones():
    packs = {p["id"]: p for p in registry()["packs"]}
    for pid, repo in TWELVE.items():
        assert pid in packs, f"{pid} is missing from the registry"
        assert packs[pid]["upstream"]["repo"] == repo, (
            f"{pid} must be pinned to {repo}, not {packs[pid]['upstream'].get('repo')}"
        )
        assert packs[pid]["upstream"]["commit"], f"{pid} has no pinned upstream commit"
        assert packs[pid]["upstream"]["stars"], f"{pid} has no measured star count"
    for pid, category in NATIVE.items():
        assert pid in packs, f"{pid} is missing from the registry"
        assert packs[pid]["category"] == category
        assert not packs[pid]["upstream"], (
            f"{pid} is estate-native and must claim no upstream"
        )


def test_every_pack_covers_one_of_the_catalogue_s_categories():
    """A pack is placed in a category the catalogue declares, and the catalogue
    declares every category a pack uses.

    The catalogue grew from four domains to nine as the layer grew; a test frozen
    on the old four would either fail forever or be widened until it proves
    nothing. What must hold is that the catalogue and the registry agree, in both
    directions, so an agent reading the catalogue finds every pack and no pack
    is filed under a category nobody wrote down.
    """
    categories = {p["category"] for p in registry()["packs"]}
    declared = set(
        re.findall(r"^### ([a-z][a-z0-9-]*) --", CATALOGUE.read_text(), re.M)
    )
    assert categories == declared, (
        "the catalogue's sections and the registry's categories disagree: "
        f"only in the registry {sorted(categories - declared)}, "
        f"only in the catalogue {sorted(declared - categories)}"
    )


# --- the gate that can fail -----------------------------------------------------
def test_every_pack_file_hashes_to_what_the_registry_says():
    result = run("verify")
    assert result.returncode == 0, (
        f"the packs drifted from the registry:\n{result.stdout}{result.stderr}"
    )


def test_a_drifted_pack_is_refused(tmp_path: Path):
    """Edit a byte in a pack and the registry says so."""
    skills = tmp_path / "skills"
    shutil.copytree(SKILLS, skills)
    victim = skills / "packs" / "taste" / "SKILL.md"
    victim.write_text(victim.read_text() + "\n<!-- edited -->\n")
    result = run("verify", skills=skills)
    assert result.returncode == 1, "verify must fail on a drifted pack"
    assert "checksum mismatch" in result.stderr


def test_an_unregistered_file_is_refused(tmp_path: Path):
    """A file nobody reviewed is a file nobody checked."""
    skills = tmp_path / "skills"
    shutil.copytree(SKILLS, skills)
    (skills / "packs" / "taste" / "extra.md").write_text("not reviewed\n")
    result = run("verify", skills=skills)
    assert result.returncode == 1
    assert "not in the registry" in result.stderr


def test_the_installer_refuses_a_drifted_pack(tmp_path: Path):
    skills = tmp_path / "skills"
    shutil.copytree(SKILLS, skills)
    victim = skills / "packs" / "taste" / "SKILL.md"
    victim.write_text(victim.read_text() + "\n<!-- edited -->\n")
    result = run(
        "install",
        "--pack",
        "taste",
        "--runtime",
        "pi",
        "--apply",
        skills=skills,
        home=tmp_path,
    )
    assert result.returncode == 1, "a drifted pack must never be installed"
    assert not (tmp_path / ".pi" / "agent" / "skills" / "taste").exists()


# --- the harness folder the estate refuses -------------------------------------
def test_no_pack_carries_a_harness_folder():
    """Founder 2026-09-30: no `.claude` anywhere in the tree.

    Several upstreams ship their skills under `.claude/skills/`. The estate
    vendors the bytes under a plain path instead, so the bytes are kept and the
    law is kept.
    """
    offenders = [
        str(p.relative_to(SKILLS))
        for p in SKILLS.rglob("*")
        if p.is_file()
        and any(part == ".claude" for part in p.relative_to(SKILLS).parts)
    ]
    assert not offenders, f"harness folder in the tree: {offenders}"


def test_a_harness_folder_in_a_pack_is_refused(tmp_path: Path):
    """A pack that grows one is caught by the gate, not by a human."""
    skills = tmp_path / "skills"
    shutil.copytree(SKILLS, skills)
    hidden = skills / "packs" / "taste" / ".claude" / "skills" / "x" / "SKILL.md"
    hidden.parent.mkdir(parents=True)
    hidden.write_text("---\nname: x\ndescription: x\n---\n")
    result = run("verify", skills=skills)
    assert result.returncode == 1, "a harness folder in a pack must be refused"
    assert "harness folder in the pack" in result.stderr


def test_every_moved_file_keeps_its_upstream_path():
    """Provenance survives the move: the upstream path is named in the registry."""
    for pack in registry()["packs"]:
        upstream = pack.get("upstream") or {}
        path_map = upstream.get("path_map") or {}
        for rel in upstream.get("vendored", []):
            assert rel in path_map, f"{pack['id']}: {rel} has no upstream path recorded"
            assert (SKILLS / "packs" / pack["id"] / "upstream" / rel).exists()
        for rel, upstream_rel in path_map.items():
            if rel != upstream_rel:
                assert ".claude" not in rel.split("/"), (
                    f"{pack['id']}: {rel} still carries a harness folder"
                )


def test_the_registry_keeps_its_digests_out_of_the_credential_shape():
    """The digests are objects, not a {path: sha256} map.

    gitleaks' generic-api-key rule reads `"<path>": "<64 hex>"` as a credential
    whenever the path holds a word like "token", and the design packs' own upstream
    file names do (`semantic-tokens.md`, `token-architecture.md`). The map form made
    every lane carrying the registry red on security-scan, and nothing landed
    (idp#6984). The shape is the gate's business, so it is a test now.
    """
    for pack in registry()["packs"]:
        files = pack["files"]
        assert isinstance(files, list), (
            f"{pack['id']}: digests must be a list of objects"
        )
        for entry in files:
            assert set(entry) == {"path", "sha256"}, f"{pack['id']}: {entry}"
            assert re.fullmatch(r"[a-f0-9]{64}", entry["sha256"]), (
                f"{pack['id']}: {entry['path']} is not a sha256"
            )


def test_a_registry_written_before_the_change_still_verifies(tmp_path: Path):
    """The reader takes both forms, so an older registry is not a broken registry."""
    skills = tmp_path / "skills"
    shutil.copytree(SKILLS, skills)
    reg = json.loads((skills / "registry.json").read_text())
    for pack in reg["packs"]:
        pack["files"] = {e["path"]: e["sha256"] for e in pack["files"]}
    (skills / "registry.json").write_text(json.dumps(reg, indent=2) + "\n")
    result = run("verify", skills=skills)
    assert result.returncode == 0, result.stderr


def test_no_front_door_points_at_a_file_that_is_not_there():
    """A front door that names a missing file sends the agent nowhere."""
    missing = []
    for front in sorted((SKILLS / "packs").glob("*/SKILL.md")):
        for ref in re.findall(r"`(upstream/[^`]+)`", front.read_text()):
            if not (front.parent / ref).exists():
                missing.append(f"{front.parent.name}: {ref}")
    assert not missing, f"front doors point at files that are not there: {missing}"


# --- the install ----------------------------------------------------------------
def test_install_writes_the_pack_and_a_receipt(tmp_path: Path):
    result = run(
        "install", "--pack", "taste", "--runtime", "pi", "--apply", home=tmp_path
    )
    assert result.returncode == 0, result.stderr
    installed = tmp_path / ".pi" / "agent" / "skills" / "taste"
    assert (installed / "SKILL.md").exists()
    assert (installed / "NOTICE.md").exists()
    assert list((installed / "upstream").rglob("*.md")), (
        "the vendored material must travel with the pack"
    )

    receipt = tmp_path / ".estate" / "skills-state" / "pi" / "taste.json"
    assert receipt.exists(), "an install without a receipt cannot be audited"
    data = json.loads(receipt.read_text())
    assert data["pack"] == "taste"
    assert data["tree_sha256"]
    assert data["upstream"]["commit"], (
        "the receipt must name the upstream commit it came from"
    )


def test_install_is_a_dry_run_by_default(tmp_path: Path):
    result = run("install", "--pack", "taste", "--runtime", "pi", home=tmp_path)
    assert result.returncode == 0
    assert "would install" in result.stdout
    assert not (tmp_path / ".pi" / "agent" / "skills" / "taste").exists()


def test_the_installer_refuses_a_runtime_outside_the_allowlist(tmp_path: Path):
    result = run(
        "install",
        "--pack",
        "taste",
        "--runtime",
        "somewhere-else",
        "--apply",
        home=tmp_path,
    )
    assert result.returncode != 0
    assert not list(tmp_path.rglob("taste/SKILL.md"))


def test_the_installer_writes_only_inside_the_allowlisted_roots(tmp_path: Path):
    run("install", "--pack", "taste", "--runtime", "all", "--apply", home=tmp_path)
    for runtime, rel in RUNTIMES.items():
        assert (tmp_path / rel / "taste" / "SKILL.md").exists(), runtime
    # Nothing landed anywhere else under the home directory.
    stray = [p for p in tmp_path.rglob("SKILL.md") if p.parts[-2] == "taste"]
    assert len(stray) == len(RUNTIMES), stray


def test_an_existing_install_is_not_silently_replaced(tmp_path: Path):
    run("install", "--pack", "taste", "--runtime", "pi", "--apply", home=tmp_path)
    target = tmp_path / ".pi" / "agent" / "skills" / "taste" / "SKILL.md"
    target.write_text("hand edited\n")
    result = run(
        "install", "--pack", "taste", "--runtime", "pi", "--apply", home=tmp_path
    )
    assert result.returncode == 1
    assert target.read_text() == "hand edited\n", (
        "a hand edit must survive a refused install"
    )
    forced = run(
        "install",
        "--pack",
        "taste",
        "--runtime",
        "pi",
        "--apply",
        "--force",
        home=tmp_path,
    )
    assert forced.returncode == 0
    assert target.read_text() != "hand edited\n"


# --- the front doors ------------------------------------------------------------
def test_every_pack_has_a_valid_skill_front_door():
    """The front door must load the way a runtime loads it.

    Regex proved the text was shaped right; it did not prove the frontmatter was
    readable. An unquoted description containing ': ' parses as a nested mapping, so
    the runtime refuses the whole block and never offers the skill to an agent --
    which is how ten of the fourteen packs were invisible while every checksum
    said they were fine. This test parses the YAML the way pi does.
    """
    import yaml

    for pack in registry()["packs"]:
        pid = pack["id"]
        path = SKILLS / "packs" / pid / "SKILL.md"
        assert path.exists(), f"{pid} has no SKILL.md"
        text = path.read_text()
        assert text.startswith("---\n"), f"{pid} has no frontmatter"
        front = text.split("---", 2)[1]
        try:
            data = yaml.safe_load(front)
        except yaml.YAMLError as exc:
            raise AssertionError(
                f"{pid}'s frontmatter is not valid YAML: {exc}"
            ) from exc
        assert isinstance(data, dict), f"{pid}'s frontmatter is not a mapping"
        assert data.get("name") == pid, "the skill's name must match its directory"
        assert re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", pid), (
            f"{pid} is not a legal skill name"
        )
        desc = data.get("description")
        assert isinstance(desc, str) and desc.strip(), (
            f"{pid} has no description a runtime can read"
        )
        assert len(desc) <= 1024, (
            f"{pid}'s description is longer than the standard allows"
        )
        assert "estate-category" in front, f"{pid} does not say which capability it is"


def test_a_front_door_a_runtime_cannot_read_is_refused(tmp_path: Path):
    """The gate catches it, not a human noticing the skill never appears."""
    skills = tmp_path / "skills"
    shutil.copytree(SKILLS, skills)
    victim = skills / "packs" / "taste" / "SKILL.md"
    text = victim.read_text()
    victim.write_text(text.replace('description: "', "description: Broken: ", 1))
    result = run("verify", skills=skills)
    assert result.returncode == 1, "a front door YAML cannot parse must be refused"
    assert "not valid YAML" in result.stderr


def test_the_manifest_cannot_bless_a_forked_upstream_file(tmp_path: Path):
    """A hand edit to vendored upstream is a fork, not a version."""
    skills = tmp_path / "skills"
    shutil.copytree(SKILLS, skills)
    forked = next((skills / "packs" / "taste" / "upstream").rglob("*.md"))
    forked.write_text(forked.read_text() + "\n<!-- forked -->\n")
    result = run("manifest", skills=skills)
    assert result.returncode == 1, "manifest must refuse a forked upstream file"
    assert "upstream bytes changed on disk" in result.stderr
    assert "vendor" in result.stderr, "the refusal must name the door that can do it"


def test_every_vendored_pack_carries_its_licence_and_provenance():
    for pack in registry()["packs"]:
        pid = pack["id"]
        assert (SKILLS / "packs" / pid / "NOTICE.md").exists(), (
            f"{pid} has no NOTICE.md"
        )
        if pack["upstream"]:
            licences = list((SKILLS / "packs" / pid / "upstream").glob("LICENSE*"))
            assert licences, f"{pid} vendored upstream material with no licence file"
            assert pack["upstream"]["license"], f"{pid} has no measured licence"


def test_the_front_doors_bind_the_estate_rules():
    """A pack that only knows upstream is a pack that can drift away from the estate.

    Every front door carries the estate rules that bind it -- proof not assertion,
    one of each layer, voice first, the claim is the contract. The packs that touch
    a surface carry two more: the tokens they must use, and `ui.review`, the gate
    that can fail the work. A gate is named by the work it grades, so a pack that
    does not touch a surface (the cluster checklist, the threat modeller) is not
    required to name a gate that does not apply to it.
    """
    surface = {"design", "ui", "architecture"}
    for pack in registry()["packs"]:
        text = (SKILLS / "packs" / pack["id"] / "SKILL.md").read_text()
        assert "## Estate rules" in text, (
            f"{pack['id']} does not carry the estate rules that bind it"
        )
        if pack["category"] in surface:
            assert "tokens.json" in text, (
                f"{pack['id']} touches a surface and does not point at the estate's tokens"
            )
            assert "ui.review" in text, (
                f"{pack['id']} touches a surface and does not name the gate that can fail"
            )


# --- the intents ----------------------------------------------------------------
def test_the_skill_intents_exist_and_are_wellformed():
    import yaml

    for name in ("skill.list", "skill.install", "skill.verify", "skill.vendor"):
        path = REPO / "platform" / "estate" / "intents" / f"{name}.yaml"
        assert path.exists(), f"{name} has no intent"
        data = yaml.safe_load(path.read_text())
        assert data["name"] == name
        assert data["description"].strip(), f"{name} has no description"
        assert data.get("steps"), f"{name} has no steps"
        cmd = " ".join(s.get("cmd", "") for s in data["steps"])
        assert "skill-packs.py" in cmd, f"{name} must go through the one installer"


def test_the_intents_only_reach_the_allowlisted_runtimes():
    import yaml

    data = yaml.safe_load(
        (REPO / "platform" / "estate" / "intents" / "skill.install.yaml").read_text()
    )
    cmd = " ".join(s.get("cmd", "") for s in data["steps"])
    for runtime in RUNTIMES:
        assert runtime in cmd or "runtime" in cmd, runtime
    assert "--dest" not in cmd, (
        "the intent must not offer a destination the tool does not have"
    )


# --- the catalogue ----------------------------------------------------------------
# A dotted name printed in the catalogue is a claim: an intent of that name exists and
# answers. The catalogue is where an agent looks to find the estate's own doors, so a
# name it prints that no intent answers is a dead end the agent walks into -- the exact
# failure this catalogue was written to prevent (idp#7044).
#
# The gate is deliberately narrow. Only a name shaped like an intent is read: two
# lowercase words around a dot. A file name (registry.json), a domain (agentskills.io),
# a path segment and a version (Apache-2.0) are not intent names, and a gate that
# flagged those would be a gate that cries wolf and gets ignored.
CATALOGUE = REPO / "docs" / "specs" / "2026-10-24-skill-catalogue.md"
INTENT_DIR = REPO / "platform" / "estate" / "intents"

INTENT_NAME = re.compile(r"(?<![\w./-])([a-z][a-z0-9-]*)\.([a-z][a-z0-9-]*)(?![\w-])")

# The suffixes a dotted name may carry and still be a file, not an intent.
NOT_AN_INTENT = {
    "json",
    "md",
    "py",
    "yaml",
    "yml",
    "ts",
    "tsx",
    "js",
    "jsx",
    "io",
    "sh",
    "txt",
    "html",
    "css",
    "toml",
    "svg",
    "png",
    "lock",
    "cfg",
    "ini",
    "sql",
    "env",
}


def intent_names(text: str) -> set[str]:
    """Every intent-shaped name the text prints, and nothing that is not one."""
    found = set()
    for match in INTENT_NAME.finditer(text):
        if match.group(2) in NOT_AN_INTENT:
            continue
        found.add(f"{match.group(1)}.{match.group(2)}")
    return found


def missing_intents(text: str) -> list[str]:
    return sorted(
        name
        for name in intent_names(text)
        if not (INTENT_DIR / f"{name}.yaml").exists()
    )


def test_the_catalogue_names_only_intents_that_exist():
    assert CATALOGUE.exists(), "the catalogue is gone"
    text = CATALOGUE.read_text()
    names = intent_names(text)
    assert names, "the gate read no intent-shaped name at all -- it is not reading"
    missing = missing_intents(text)
    assert not missing, (
        "the catalogue names intents that do not exist: "
        + ", ".join(missing)
        + " -- name the intent that exists, or add the one it promises"
    )


def test_the_catalogue_table_lists_every_pack_with_its_registry_category():
    """The catalogue's table is the estate's inventory; it cannot drift from the
    registry without an agent reading a pack list that is not the estate's."""
    text = CATALOGUE.read_text()
    table = dict(re.findall(r"^\| `([a-z0-9-]+)` \| ([a-z][a-z0-9-]*) \|", text, re.M))
    expected = {p["id"]: p["category"] for p in registry()["packs"]}
    assert table == expected, (
        "the catalogue's table and the registry disagree: "
        f"only in the table {sorted(set(table) - set(expected))}, "
        f"only in the registry {sorted(set(expected) - set(table))}, "
        f"filed differently {sorted(k for k in set(table) & set(expected) if table[k] != expected[k])}"
    )


def test_every_pack_is_placed_in_a_section_of_the_catalogue():
    """A pack in the table but in no section is a pack an agent cannot find."""
    text = CATALOGUE.read_text()
    placed = set(re.findall(r"^- \*\*`([a-z0-9-]+)`\*\*", text, re.M))
    expected = {p["id"] for p in registry()["packs"]}
    assert expected <= placed, (
        "the catalogue does not place these packs in any section: "
        + ", ".join(sorted(expected - placed))
    )


def test_the_pack_front_doors_name_only_intents_that_exist():
    doors = sorted((SKILLS / "packs").glob("*/SKILL.md"))
    assert doors, "no pack front doors to check"
    for door in doors:
        missing = missing_intents(door.read_text())
        assert not missing, (
            f"{door.parent.name}/SKILL.md names intents that do not exist: "
            + ", ".join(missing)
        )


def test_the_catalogue_names_the_doors_the_estate_actually_has():
    """The catalogue must keep naming the skill doors, or it stops being a map."""
    names = intent_names(CATALOGUE.read_text())
    for door in ("skill.list", "skill.install", "skill.verify"):
        assert door in names, f"the catalogue stopped naming {door}"
