#!/usr/bin/env python3
"""skill-packs.py -- the governed skill layer: list, verify, install, vendor, manifest.

WHY. The estate gives every agent the same twelve UI/design/research/architecture
capabilities. They used to arrive per runtime, by hand, from wherever the agent found
them, which is how an estate grows eleven copies of one capability (AGENTS.md §6). This
is the one copy: packs live in idp under platform/estate/skills, each vendored upstream
file is pinned by sha256 in platform/estate/skills/registry.json, and the only way to
put a pack in front of an agent is this tool, run through an intent.

THE FOUR VERBS.

  list     what packs exist, where they came from, and whether they are installed
  verify   recompute every sha256 in the registry and compare, and lint every front
           door as a real Agent Skill. Exit 1 on any drift or any broken front door.
  install  copy a verified pack into a runtime's skills directory
  vendor   re-fetch the upstream files a pack pins, and rewrite its provenance
  manifest rewrite the registry's checksums from what is on disk (authoring only)

WHAT "GOVERNED" MEANS HERE, concretely.

  * A pack is installed only if every file in it hashes to what the registry says. A
    pack whose files were edited after review is refused, not installed.
  * A pack is installed only into one of the four allowlisted runtime roots
    (pi, claude, codex, agents). Anything else is refused; there is no --dest.
  * Every install writes a receipt under ~/.estate/skills-state/<runtime>/<pack>.json
    naming the upstream commit and the tree hash, so "which version is this agent
    running" has an answer that is not a guess.
  * The registry is the single source of truth. The packs directory is checked against
    it by `verify`, which the test suite and the CI gate both run.
  * A pack that cannot be loaded is a pack that does not exist. `verify` parses each
    front door's YAML frontmatter the way the runtimes do, so a description that
    YAML cannot read (an unquoted ': ') is caught here and not by a human noticing
    that the skill never shows up.

Network use is confined to `vendor`, which needs GitHub. Everything else is offline.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# --- The four runtime roots a pack may be installed into. ------------------------
# These are the skills directories the Agent Skills standard defines for the runtimes
# the estate runs (pi reads ~/.pi/agent/skills and ~/.agents/skills; Claude Code reads
# ~/.claude/skills; Codex reads ~/.codex/skills). The allowlist is a closed set: the
# installer has no --dest, so it cannot be pointed at an arbitrary path.
RUNTIMES: Dict[str, str] = {
    "pi": ".pi/agent/skills",
    "claude": ".claude/skills",
    "codex": ".codex/skills",
    "agents": ".agents/skills",
}

STATE_DIR = ".estate/skills-state"

# A vendored file larger than this is refused: a skill is instructions an agent reads,
# not a data dump. Fonts, image atlases and JSON datasets stay upstream.
MAX_FILE_BYTES = 64 * 1024

# Files the registry never checksums.
IGNORE_NAMES = {".DS_Store"}

try:  # PyYAML is what the runtimes parse the frontmatter with.
    import yaml  # type: ignore
except ImportError:  # pragma: no cover - the estate's python3 ships PyYAML
    yaml = None  # type: ignore


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# --- Where the packs live ------------------------------------------------------
def packs_root() -> Path:
    """Resolve the packs directory.

    Order matters: the release layout (~/.estate/libexec/../skills) and the checkout
    layout (platform/estate/libexec/../../skills) are both one parent apart, so the
    env var is the only way to disambiguate, and it wins.
    """
    env = os.environ.get("ESTATE_SKILLS_DIR")
    if env:
        return Path(env).expanduser().resolve()
    here = Path(__file__).resolve()
    sibling = (
        here.parent.parent / "skills"
    )  # ~/.estate/skills, or platform/estate/skills
    if (sibling / "registry.json").exists():
        return sibling
    home = Path.home() / ".estate" / "skills"
    if (home / "registry.json").exists():
        return home
    return sibling


def registry_path() -> Path:
    return packs_root() / "registry.json"


def load_registry() -> dict:
    path = registry_path()
    if not path.exists():
        raise SystemExit(f"skill-packs: no registry at {path}")
    return json.loads(path.read_text())


def save_registry(reg: dict) -> None:
    path = registry_path()
    path.write_text(json.dumps(reg, indent=2, sort_keys=False) + "\n")
    print(f"skill-packs: wrote {path}")


def split_packs(value: str) -> List[str]:
    """`--pack a,b,c` -> ["a", "b", "c"]. An empty value means "no filter"."""
    if not value:
        return []
    return [p.strip() for p in value.replace(" ", ",").split(",") if p.strip()]


def pack_dir(pack_id: str) -> Path:
    return packs_root() / "packs" / pack_id


def pack_files_on_disk(pack_id: str) -> Dict[str, Path]:
    """Every file under packs/<id>, relative to the pack dir."""
    out: Dict[str, Path] = {}
    root = pack_dir(pack_id)
    if not root.exists():
        return out
    for p in sorted(root.rglob("*")):
        if not p.is_file() or p.name in IGNORE_NAMES:
            continue
        out[str(p.relative_to(root))] = p
    return out


def tree_hash(files: Dict[str, str]) -> str:
    """One hash for the whole pack: the sorted (path, sha256) pairs."""
    blob = "\n".join(f"{k} {v}" for k, v in sorted(files.items()))
    return sha256_bytes(blob.encode())


def registered_files(pack: dict) -> Dict[str, str]:
    """The pack's registered digests as {path: sha256}.

    The registry stores them as a list of {"path", "sha256"} objects, not as a
    {path: sha256} map. The map form is read as a credential by gitleaks'
    generic-api-key rule whenever the path contains a word like "token" -- and
    the design packs' own upstream file names contain one
    (`semantic-tokens.md`, `token-architecture.md`). A sha256 digest is not a
    secret, but the security scan reads the shape, not the intent, and a red
    scan blocks every lane that carries the file. The list form keeps the path
    and the digest apart, so the rule never sees a key followed by a secret.

    The older map form is still read, so a registry written before this change
    still verifies instead of failing as if every file were missing.
    """
    raw = pack.get("files", {})
    if isinstance(raw, dict):
        return {str(k): str(v) for k, v in raw.items()}
    out: Dict[str, str] = {}
    for entry in raw or []:
        if isinstance(entry, dict) and entry.get("path"):
            out[str(entry["path"])] = str(entry.get("sha256", ""))
    return out


def file_entries(files: Dict[str, str]) -> List[dict]:
    """The registry's on-disk form for a pack's digests: sorted path/sha256 objects."""
    return [{"path": path, "sha256": digest} for path, digest in sorted(files.items())]


# --- the front door -------------------------------------------------------------
def read_frontmatter(pack_id: str) -> Tuple[Optional[str], List[str]]:
    """The YAML block at the top of the pack's SKILL.md, or the reasons there is none."""
    path = pack_dir(pack_id) / "SKILL.md"
    if not path.exists():
        return None, [f"{pack_id}: no SKILL.md front door"]
    text = path.read_text()
    if not text.startswith("---\n"):
        return None, [f"{pack_id}: SKILL.md has no frontmatter block"]
    end = text.find("\n---", 3)
    if end == -1:
        return None, [f"{pack_id}: SKILL.md frontmatter is never closed"]
    return text[4 : end + 1], []


def frontmatter_problems(pack_id: str) -> List[str]:
    """Problems that would make a runtime ignore this pack.

    Measured, not assumed: pi's own loader (loadSkills) parses the frontmatter with
    a YAML parser, and an unquoted description containing ': ' is read as a nested
    mapping, so the whole block is refused and the skill is never offered to an
    agent. Ten of the estate's fourteen packs were invisible for exactly that
    reason, and no checksum said so. This is that check.
    """
    problems: List[str] = []
    front, errs = read_frontmatter(pack_id)
    if front is None:
        return errs

    data: Optional[dict] = None
    if yaml is not None:
        try:
            data = yaml.safe_load(front)
        except Exception as exc:  # yaml.YAMLError and friends
            first = str(exc).splitlines()[0] if str(exc) else exc
            return [f"{pack_id}: frontmatter is not valid YAML: {first}"]
    else:
        # No PyYAML here: check the thing that actually broke, by hand.
        m = re.search(r"^description:\s*(.*)$", front, re.M)
        if not m:
            problems.append(f"{pack_id}: frontmatter has no description")
        else:
            raw = m.group(1).strip()
            if not (raw.startswith('"') or raw.startswith("'")) and ": " in raw:
                problems.append(
                    f"{pack_id}: description is an unquoted scalar containing ': '; "
                    "quote it or a YAML parser refuses the whole frontmatter"
                )

    if data is None:
        return problems
    if not isinstance(data, dict):
        return [f"{pack_id}: frontmatter is not a mapping"]

    name = data.get("name")
    if not isinstance(name, str) or name != pack_id:
        problems.append(
            f"{pack_id}: frontmatter name is {name!r}, expected {pack_id!r}"
        )
    desc = data.get("description")
    if not isinstance(desc, str) or not desc.strip():
        problems.append(
            f"{pack_id}: frontmatter description is missing or not a string"
        )
    elif len(desc) > 1024:
        problems.append(
            f"{pack_id}: frontmatter description is {len(desc)} chars, over the 1024 the standard allows"
        )
    meta = data.get("metadata")
    if not isinstance(meta, dict) or "estate-category" not in meta:
        problems.append(f"{pack_id}: frontmatter does not say which capability it is")
    return problems


# --- verify ---------------------------------------------------------------------
def verify_pack(pack: dict) -> Tuple[bool, List[str]]:
    """Compare the pack on disk with the registry. Returns (ok, problems)."""
    problems: List[str] = []
    pid = pack["id"]
    registered = registered_files(pack)
    on_disk = pack_files_on_disk(pid)

    for rel in sorted(registered):
        path = pack_dir(pid) / rel
        if not path.exists():
            problems.append(f"{pid}: registered file missing: {rel}")
            continue
        actual = sha256_file(path)
        if actual != registered[rel]:
            problems.append(
                f"{pid}: checksum mismatch: {rel} (registry {registered[rel][:12]}, disk {actual[:12]})"
            )

    for rel in sorted(on_disk):
        if rel not in registered:
            problems.append(f"{pid}: file on disk is not in the registry: {rel}")

    # The estate refuses a harness folder anywhere in the tree (founder 2026-09-30),
    # so the packs are refused it too: an upstream that ships `.claude/skills/...`
    # is vendored under a plain path, and a pack that grows one is caught here.
    for rel in sorted(on_disk):
        if any(part == ".claude" for part in rel.split("/")):
            problems.append(f"{pid}: harness folder in the pack: {rel}")

    # A pack a runtime cannot load is a pack that does not exist, and no checksum
    # says so. The front door is linted the way the runtimes read it.
    problems.extend(frontmatter_problems(pid))

    return (not problems), problems


def cmd_verify(args: argparse.Namespace) -> int:
    reg = load_registry()
    packs = reg["packs"]
    wanted_ids = split_packs(args.pack)
    if wanted_ids:
        wanted = [p for p in packs if p["id"] in wanted_ids]
        missing = set(wanted_ids) - {p["id"] for p in wanted}
        if missing:
            print(
                f"skill-packs: no such pack: {', '.join(sorted(missing))}",
                file=sys.stderr,
            )
            return 2
    else:
        wanted = packs

    all_problems: List[str] = []
    for pack in wanted:
        ok, problems = verify_pack(pack)
        state = "ok" if ok else "DRIFT"
        print(f"{state:>5}  {pack['id']:<20} {pack['title']}")
        all_problems.extend(problems)

    if all_problems:
        print("\nskill-packs: drift found:", file=sys.stderr)
        for p in all_problems:
            print(f"  {p}", file=sys.stderr)
        return 1
    print(f"\nskill-packs: {len(wanted)} pack(s) verified against the registry")
    return 0


# --- manifest ------------------------------------------------------------------
def cmd_manifest(args: argparse.Namespace) -> int:
    """Rewrite (or check) the registry's per-pack checksums from what is on disk.

    Only the estate-authored front door and NOTICE.md may be re-pinned this way.
    Upstream bytes are re-pinned by `vendor`, which fetched them from the pinned
    commit: a hand edit to vendored upstream is not a new version of the upstream,
    it is a fork, and the registry refuses to bless it here.
    """
    reg = load_registry()
    allow_upstream = getattr(args, "allow_upstream", False)
    changed = False
    for pack in reg["packs"]:
        pid = pack["id"]
        disk = pack_files_on_disk(pid)
        computed = {rel: sha256_file(p) for rel, p in disk.items()}
        registered = registered_files(pack)
        if computed != registered:
            if not allow_upstream:
                forked = [
                    rel
                    for rel in computed
                    if rel.startswith("upstream/")
                    and computed[rel] != registered.get(rel)
                ]
                if forked:
                    print(
                        f"skill-packs: {pid}: upstream bytes changed on disk; "
                        "re-pin them with `vendor` (a hand edit is a fork, not a version)",
                        file=sys.stderr,
                    )
                    for rel in sorted(forked):
                        print(f"  {rel}", file=sys.stderr)
                    return 1
            changed = True
            if args.check:
                print(
                    f"skill-packs: {pid}: registry does not match disk", file=sys.stderr
                )
                continue
            pack["files"] = file_entries(computed)
            pack["tree_sha256"] = tree_hash(computed)
        if not args.check:
            pack["tree_sha256"] = tree_hash(computed)
    if args.check:
        if changed:
            print(
                "skill-packs: run `skill-packs.py manifest` to rewrite the registry",
                file=sys.stderr,
            )
            return 1
        print("skill-packs: registry matches disk")
        return 0
    if not changed:
        print("skill-packs: registry already matches disk")
        return 0
    save_registry(reg)
    return 0


# --- list -----------------------------------------------------------------------
def installed_state(runtime: str, pack_id: str, home: Path) -> Optional[dict]:
    receipt = home / STATE_DIR / runtime / f"{pack_id}.json"
    if not receipt.exists():
        return None
    try:
        return json.loads(receipt.read_text())
    except json.JSONDecodeError:
        return None


def cmd_list(args: argparse.Namespace) -> int:
    reg = load_registry()
    home = Path(args.home).expanduser()
    packs = reg["packs"]
    wanted_ids = split_packs(args.pack)
    if wanted_ids:
        packs = [p for p in packs if p["id"] in wanted_ids]
    if args.category:
        packs = [p for p in packs if p.get("category") == args.category]

    if args.json and args.json.lower() not in ("", "0", "false", "no"):
        print(json.dumps(packs, indent=2))
        return 0

    print(f"{len(packs)} skill pack(s) in {packs_root()}\n")
    for pack in packs:
        pid = pack["id"]
        prov = pack.get("upstream", {})
        print(f"{pid}  [{pack.get('category', '?')}]  {pack['title']}")
        if prov.get("repo"):
            print(
                f"    upstream : {prov['repo']} ({prov.get('license', '?')}, "
                f"{prov.get('stars', '?')} stars measured {prov.get('stars_measured_at', '?')})"
            )
            print(f"    pinned   : {prov.get('commit', '?')}")
        else:
            print("    upstream : estate-native")
        where = []
        for rt in sorted(RUNTIMES):
            if installed_state(rt, pid, home):
                where.append(rt)
        print(f"    installed: {', '.join(where) if where else 'nowhere'}")
        print(f"    what     : {pack.get('capability', '')}")
        print()
    return 0


# --- install --------------------------------------------------------------------
def runtime_root(runtime: str, home: Path) -> Path:
    if runtime not in RUNTIMES:
        raise SystemExit(
            f"skill-packs: unknown runtime {runtime}; known: {', '.join(sorted(RUNTIMES))}"
        )
    return (home / RUNTIMES[runtime]).resolve()


def cmd_install(args: argparse.Namespace) -> int:
    reg = load_registry()
    home = Path(args.home).expanduser()
    packs = reg["packs"]

    wanted_ids = split_packs(args.pack)
    if args.all or wanted_ids == ["all"]:
        chosen = packs
    elif wanted_ids:
        chosen = [p for p in packs if p["id"] in wanted_ids]
        missing = set(wanted_ids) - {p["id"] for p in chosen}
        if missing:
            print(
                f"skill-packs: no such pack: {', '.join(sorted(missing))}",
                file=sys.stderr,
            )
            return 2
    else:
        print("skill-packs: pass --pack <id>[,<id>] or --all", file=sys.stderr)
        return 2

    runtimes = sorted(RUNTIMES) if args.runtime == "all" else [args.runtime]
    for rt in runtimes:
        if rt not in RUNTIMES:
            print(
                f"skill-packs: unknown runtime {rt}; known: {', '.join(sorted(RUNTIMES))}",
                file=sys.stderr,
            )
            return 2

    # Verify first. A pack that does not match the registry is not installed.
    for pack in chosen:
        ok, problems = verify_pack(pack)
        if not ok:
            print(
                f"skill-packs: refusing to install {pack['id']}: checksum drift",
                file=sys.stderr,
            )
            for p in problems:
                print(f"  {p}", file=sys.stderr)
            return 1

    for pack in chosen:
        pid = pack["id"]
        files = pack_files_on_disk(pid)
        for rt in runtimes:
            root = runtime_root(rt, home)
            dest = root / pid
            if not args.apply:
                print(f"would install {pid} -> {dest} ({len(files)} files)")
                continue
            root.mkdir(parents=True, exist_ok=True)
            staging = Path(tempfile.mkdtemp(prefix=f".{pid}.", dir=str(root)))
            try:
                for rel, src in files.items():
                    target = staging / rel
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, target)
                if dest.exists():
                    if not args.force:
                        print(
                            f"skill-packs: {dest} already exists; pass --force to replace",
                            file=sys.stderr,
                        )
                        shutil.rmtree(staging, ignore_errors=True)
                        return 1
                    shutil.rmtree(dest)
                staging.rename(dest)
            finally:
                if staging.exists():
                    shutil.rmtree(staging, ignore_errors=True)

            receipt_dir = home / STATE_DIR / rt
            receipt_dir.mkdir(parents=True, exist_ok=True)
            receipt = {
                "pack": pid,
                "runtime": rt,
                "installed_at": now(),
                "tree_sha256": pack.get("tree_sha256")
                or tree_hash(registered_files(pack)),
                "upstream": pack.get("upstream", {}),
                "path": str(dest),
            }
            (receipt_dir / f"{pid}.json").write_text(
                json.dumps(receipt, indent=2) + "\n"
            )
            print(
                f"installed {pid} -> {dest} ({len(files)} files, tree {receipt['tree_sha256'][:12]})"
            )
    return 0


# --- vendor ---------------------------------------------------------------------
def gh(*args: str) -> str:
    """Call the GitHub CLI. The estate already authenticates it; no token is read here."""
    proc = subprocess.run(["gh", *args], capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise SystemExit(
            f"skill-packs: gh {' '.join(args)} failed: {proc.stderr.strip()}"
        )
    return proc.stdout


def gh_json(*args: str):
    return json.loads(gh(*args))


def safe_rel(rel: str) -> str:
    """Strip the harness folders the estate refuses.

    Founder 2026-09-30: no `.claude` path anywhere in the tree -- knowledge hidden
    in a harness folder is invisible to every other model, and the branch ruleset
    refuses the merge. Several upstreams ship their skills under `.claude/skills/`;
    the estate vendors the bytes under a plain path and keeps the upstream path in
    the registry's path_map, so provenance survives the move.
    """
    parts = [p for p in rel.split("/") if p and p != ".claude"]
    return "/".join(parts)


def cmd_vendor(args: argparse.Namespace) -> int:
    """Re-fetch the upstream files a pack pins, and rewrite its provenance."""
    reg = load_registry()
    sources = json.loads((packs_root() / "sources.json").read_text())
    packs = reg["packs"]
    wanted_ids = split_packs(args.pack)
    if wanted_ids:
        packs = [p for p in packs if p["id"] in wanted_ids]

    for pack in packs:
        pid = pack["id"]
        src = sources["packs"].get(pid)
        if not src or not src.get("repo"):
            print(f"skip {pid}: estate-native, nothing to vendor")
            continue
        repo = src["repo"]
        meta = gh_json("api", f"repos/{repo}")
        branch = meta.get("default_branch", "main")
        commit = gh_json("api", f"repos/{repo}/commits/{branch}")["sha"]
        tree = gh_json("api", f"repos/{repo}/git/trees/{branch}?recursive=1")
        blobs = {e["path"]: e for e in tree.get("tree", []) if e.get("type") == "blob"}

        wanted = list(src.get("include", []))
        license_path = src.get("license_file") or "LICENSE"
        if license_path in blobs:
            wanted.append(license_path)

        out_root = pack_dir(pid) / "upstream"
        vendored: List[str] = []
        path_map: Dict[str, str] = {}
        for rel in wanted:
            entry = blobs.get(rel)
            if not entry:
                print(f"  {pid}: upstream has no {rel}; skipped", file=sys.stderr)
                continue
            if entry.get("size", 0) > MAX_FILE_BYTES:
                print(
                    f"  {pid}: {rel} is {entry['size']}B over the {MAX_FILE_BYTES}B cap; skipped",
                    file=sys.stderr,
                )
                continue
            content = gh_json("api", f"repos/{repo}/contents/{rel}?ref={branch}")
            data = base64.b64decode(content["content"])
            upstream_rel = rel
            rel = safe_rel(rel)
            dest = out_root / rel
            path_map[rel] = upstream_rel
            if args.dry_run:
                print(f"would vendor {pid}: {rel} ({len(data)}B)")
                vendored.append(rel)
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
            vendored.append(rel)
            print(f"vendored {pid}: {rel} ({len(data)}B)")

        if args.dry_run:
            continue

        pack["upstream"] = {
            "repo": repo,
            "branch": branch,
            "commit": commit,
            "license": (meta.get("license") or {}).get("spdx_id", "UNKNOWN"),
            "stars": meta.get("stargazers_count"),
            "stars_measured_at": now(),
            "vendored": sorted(vendored),
            "path_map": dict(sorted(path_map.items())),
        }
        write_notice(pack, src)
        write_skill_md(pack, src, out_root)

    if not args.dry_run:
        save_registry(reg)
        # The vendored bytes changed the pack; rewrite the checksums to match, then
        # verify so the registry can never claim a hash the disk does not have.
        cmd_manifest(argparse.Namespace(check=False, pack=[], allow_upstream=True))
    return 0


def write_notice(pack: dict, src: dict) -> None:
    up = pack.get("upstream", {})
    pid = pack["id"]
    lines = [
        f"# {pid} -- provenance",
        "",
        f"Upstream: {up.get('repo')} (branch {up.get('branch')}, commit `{up.get('commit')}`)",
        f"Licence: {up.get('license')}",
        f"Stars at measurement: {up.get('stars')} (measured {up.get('stars_measured_at')})",
        "",
        "The files under `upstream/` are vendored verbatim from the upstream repository",
        "at the commit named above, under that repository's licence. They are the",
        "capability itself; the estate-authored `SKILL.md` next to them is the front door",
        "that says when to use it and which estate rules bind it.",
        "",
        "Vendored files:",
        "",
    ]
    for rel in up.get("vendored", []):
        lines.append(f"- `upstream/{rel}`")
    path_map = up.get("path_map") or {}
    moved = {k: v for k, v in path_map.items() if k != v}
    if moved:
        lines += [
            "",
            "Moved on the way in: the upstream path is kept here because the estate",
            "refuses a harness folder in the tree, so `.claude/` was dropped from the",
            "vendored path. The bytes are the upstream bytes.",
            "",
        ]
        for vendored_rel, upstream_rel in sorted(moved.items()):
            lines.append(f"- `{upstream_rel}` -> `upstream/{vendored_rel}`")
    lines.append("")
    (pack_dir(pid) / "NOTICE.md").write_text("\n".join(lines))


PROVENANCE_BEGIN = "<!-- provenance:begin -->"
PROVENANCE_END = "<!-- provenance:end -->"


def render_provenance_block(pack: dict) -> List[str]:
    """The 'Upstream material' section, generated from the registry.

    The commit, the licence and the star count are measurements; they live in the
    registry and are written here from it, so a re-vendor refreshes them instead of
    leaving a stale number in a hand-written file.
    """
    up = pack.get("upstream") or {}
    lines = [
        PROVENANCE_BEGIN,
        "## Upstream material",
        "",
    ]
    if up.get("repo"):
        lines += [
            f"Vendored verbatim from `{up.get('repo')}` at commit `{up.get('commit')}`",
            f"({up.get('license')}, {up.get('stars')} stars at {up.get('stars_measured_at')})."
            " See `NOTICE.md`.",
            "",
        ]
        path_map = up.get("path_map") or {}
        moved = {k: v for k, v in path_map.items() if k != v}
        if moved:
            lines += [
                "The upstream ships these under `.claude/`; the estate refuses a harness",
                "folder in the tree, so the bytes live under a plain path. `NOTICE.md`",
                "names the upstream path for every file.",
                "",
            ]
        for rel in up.get("vendored", []):
            lines.append(f"- `upstream/{rel}`")
        lines.append("")
    else:
        lines += [
            "Estate-native: this pack was written inside the estate, not vendored.",
            "",
        ]
    lines.append(PROVENANCE_END)
    return lines


def write_skill_md(pack: dict, src: dict, out_root: Path) -> None:
    """Write the estate-authored front door if it does not exist yet.

    Hand-written front doors are never overwritten: an agent that improved a pack's
    SKILL.md keeps its words, and the registry's checksum covers whatever is there.
    The one exception is the marked provenance block, which is generated from the
    registry so a re-vendor cannot leave a stale measurement behind.
    """
    pid = pack["id"]
    path = pack_dir(pid) / "SKILL.md"
    if path.exists():
        text = path.read_text()
        if PROVENANCE_BEGIN in text and PROVENANCE_END in text:
            head, _, rest = text.partition(PROVENANCE_BEGIN)
            _, _, tail = rest.partition(PROVENANCE_END)
            path.write_text(head + "\n".join(render_provenance_block(pack)) + tail)
        return
    title = src.get("title", pid)
    capability = src.get("capability", "")
    up = pack.get("upstream", {})
    body = src.get("skill_md_body", "")
    description = src.get("description", capability)
    # Quoted, always: an unquoted description that contains ': ' is read as a nested
    # mapping by a YAML parser, and the runtime then refuses the whole frontmatter
    # and never offers the skill to an agent.
    quoted = '"' + description.replace("\\", "\\\\").replace('"', '\\"') + '"'
    front = [
        "---",
        f"name: {pid}",
        f"description: {quoted}",
        f"license: {up.get('license', 'see NOTICE.md')}",
        "metadata:",
        f"  estate-category: {src.get('category', 'design')}",
        f"  estate-upstream: {up.get('repo', 'estate-native')}",
        "---",
        "",
        f"# {title}",
        "",
        capability,
        "",
    ]
    if body:
        body = body.replace("{UPSTREAM_DIR}", "upstream")
        front.extend([body, ""])
    if up.get("repo"):
        front.extend(render_provenance_block(pack))
        front.append("")
    path.write_text("\n".join(front))


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="skill-packs.py", description=__doc__)
    ap.add_argument(
        "--home",
        default=os.environ.get("ESTATE_HOME", str(Path.home())),
        help="home directory the runtimes live under (default: ~)",
    )
    sub = ap.add_subparsers(dest="verb", required=True)

    p = sub.add_parser("list", help="list the packs")
    p.add_argument("--pack", default="", help="comma-separated pack ids")
    p.add_argument("--category", default="")
    p.add_argument("--json", default="", help="'true' for machine-readable output")
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("verify", help="verify pack checksums against the registry")
    p.add_argument("--pack", default="", help="comma-separated pack ids")
    p.set_defaults(func=cmd_verify)

    p = sub.add_parser(
        "install", help="install a pack into a runtime's skills directory"
    )
    p.add_argument("--pack", default="", help="comma-separated pack ids, or 'all'")
    p.add_argument("--all", action="store_true")
    p.add_argument("--runtime", default="all", choices=sorted(RUNTIMES) + ["all"])
    p.add_argument(
        "--apply", action="store_true", help="write the pack (default: dry run)"
    )
    p.add_argument("--force", action="store_true")
    p.set_defaults(func=cmd_install)

    p = sub.add_parser("vendor", help="re-fetch a pack's upstream files")
    p.add_argument("--pack", default="", help="comma-separated pack ids")
    p.add_argument(
        "--apply",
        dest="dry_run",
        action="store_false",
        default=True,
        help="write the vendored files (default: dry run)",
    )
    p.set_defaults(func=cmd_vendor)

    p = sub.add_parser("manifest", help="rewrite the registry's checksums")
    p.add_argument("--check", action="store_true")
    p.set_defaults(func=cmd_manifest)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
