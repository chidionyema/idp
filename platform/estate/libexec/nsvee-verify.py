#!/usr/bin/env python3
"""nsvee-verify -- the one door every estate runtime uses to verify an artifact.

WHAT THIS IS. The shared, harness- and model-independent integration point for NSVEE
(idp#7263 I-D, ADR 0046). Every agent runtime on this machine -- pi, otto, the fleet
page, claude, gemini, cursor -- already has exactly one governed way to act: an intent
in `~/.estate/intents`, run by the estate executor. So the door for "verify this artifact"
is an intent, not a library call that every runtime has to wire up itself. One door, one
receipt, every runtime.

WHAT IT DOES.

  1. loads NSVEE's engine (the same sandbox the pipeline uses) and asks it the one
     question a gate can answer: does this artifact pass its own tests?
  2. binds the verdict to a commit and to the paths it verified, as the receipt contract
     in `platform/estate/nsvee_enforcement.py` defines it (`estate.nsvee.receipt/1`).
     The binding is scoped to the artifact and its tests by default, because a whole-tree
     digest of the estate's own checkout costs ~60 s (measured: 6,425 files) and the door
     has a bounded budget. `--whole-tree` buys the stronger binding for a caller that has
     the time -- which is what the CI surfaces will use.
  3. exits 0 only when the verdict is VERIFIED. A failing artifact, a broken sandbox or
     a missing receipt is a FAILURE of the door, never a pass with a warning.

THE RECEIPT IS NOT INSIDE THE TREE. A receipt that names the commit it describes cannot
live inside that commit -- writing the file changes the tree, which changes the digest,
which invalidates the receipt. So it is written outside the repository (by default under
`~/.estate/receipts/nsvee/`), and a request to write it inside the tree is refused.

NO MODEL. The verdict comes from executing the artifact, not from asking anything. The
door therefore costs no tokens, does not depend on a router, and cannot be flattered by a
model that wants to agree.

EXIT STATUS. 0 the artifact is VERIFIED and the receipt is written; 1 the artifact is not
verified (the receipt is still written -- it is the evidence of the failure); 2 the door
could not run at all (no artifact, no engine, no commit, no place to write the receipt).
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

HOME = Path.home()
#: Where the estate's runtime keeps its own copy of the tree (bin/estate-runtime-sync).
RUNTIME_TREE = HOME / ".estate" / "runtime" / "idp"
RECEIPTS = HOME / ".estate" / "receipts" / "nsvee"


def _fail(message: str, code: int = 2) -> int:
    print(f"nsvee-verify: {message}", file=sys.stderr)
    return code


def _load_module(path: Path, name: str):
    """Load one module by FILE PATH.

    Not `import nsvee`: the door runs from `~/.estate/libexec`, and putting a checkout on
    `sys.path` puts a directory called `platform` in front of the standard library's
    `platform` module. A file path keeps the door's dependencies exactly the two files it
    names.
    """
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    # Register before executing: on Python 3.9 a dataclass with postponed annotations
    # resolves its field types through `sys.modules[cls.__module__]`, and a module that
    # was never registered is not there.
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _find(relative: str, repo: Path, engine_root: Path | None = None) -> Path | None:
    """The first of the checkout, the runtime tree, that carries this file.

    `engine_root` is where the ENGINE and the receipt contract come from; `repo` is the tree
    the receipt binds to. They are usually the same tree, but they do not have to be: an
    artifact can live in its own repository and still be verified by the estate's engine.
    """
    roots = [engine_root] if engine_root else []
    roots += [repo, RUNTIME_TREE]
    for root in roots:
        if root is None:
            continue
        candidate = root / relative
        if candidate.is_file():
            return candidate
    return None


def _docker_ready(engine) -> bool:
    """Docker with the image already on disk.

    The engine's own `DockerRunner.available()` asks the daemon whether it is up. This
    adds the second question that matters for a door with a bounded budget: is the image
    there? Pulling it would spend the caller's time on the network, and a pull that fails
    inside a sandbox run is an infrastructure failure masquerading as a code failure.
    """
    docker = shutil_which("docker")
    if not docker:
        return False
    try:
        info = subprocess.run(  # noqa: S603 -- constant argv, no shell
            [docker, "info"], capture_output=True, timeout=10, check=False
        )
        if info.returncode != 0:
            return False
        inspect = subprocess.run(  # noqa: S603 -- constant argv, no shell
            [docker, "image", "inspect", "python:3.11-slim"],
            capture_output=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return inspect.returncode == 0


def shutil_which(name: str) -> str | None:
    """`shutil.which`, plus the places this estate keeps its tools."""
    found = shutil.which(name)
    if found:
        return found
    for extra in (HOME / ".rd" / "bin", "/opt/homebrew/bin", "/usr/local/bin"):
        candidate = extra / name
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None


def _git_commit(repo: Path) -> str | None:
    try:
        out = subprocess.run(  # noqa: S603 -- constant argv, no shell
            ["git", "-C", str(repo), "rev-parse", "HEAD"],  # noqa: S607 -- PATH lookup is intended
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    sha = out.stdout.strip()
    return sha if out.returncode == 0 and len(sha) == 40 else None


def _runner(engine):
    """The sandbox the door runs in, and its name (for the receipt's evidence)."""
    docker = engine.DockerRunner()
    if _docker_ready(engine):
        return docker, "docker"
    return engine.RlimitsRunner(), "rlimits"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="verify an artifact with NSVEE and bind the verdict to a commit"
    )
    ap.add_argument("--artifact", required=True, help="the artifact to verify")
    ap.add_argument("--tests", default="", help="comma-separated test files")
    ap.add_argument("--repo", default="", help="repo root (default: cwd)")
    ap.add_argument(
        "--engine-root",
        default="",
        help="where the engine and the receipt contract live (default: the repo, then the runtime tree)",
    )
    ap.add_argument("--commit", default="", help="commit to bind to (default: HEAD)")
    ap.add_argument("--out", default="", help="where to write the receipt")
    ap.add_argument("--timeout", type=int, default=20, help="seconds per sandbox run")
    ap.add_argument("--confirm", type=int, default=1, help="confirmation runs on PASS")
    ap.add_argument(
        "--whole-tree",
        nargs="?",
        const="true",
        default="",
        help="digest the whole tree instead of the verified paths (slow on a large tree)",
    )
    ap.add_argument(
        "--print-receipt", action="store_true", help="print the receipt JSON on stdout"
    )
    args = ap.parse_args(argv)

    repo = Path(args.repo or os.getcwd()).resolve()
    if not repo.is_dir():
        return _fail(f"no such repo: {repo}")
    engine_root = (
        Path(args.engine_root).expanduser().resolve() if args.engine_root else None
    )

    artifact_path = Path(args.artifact).expanduser()
    if not artifact_path.is_absolute():
        artifact_path = (Path.cwd() / artifact_path).resolve()
    if not artifact_path.is_file():
        return _fail(f"no such artifact: {artifact_path}")

    test_paths = []
    for raw in (args.tests or "").split(","):
        raw = raw.strip()
        if not raw:
            continue
        candidate = Path(raw).expanduser()
        if not candidate.is_absolute():
            candidate = (Path.cwd() / candidate).resolve()
        if not candidate.is_file():
            return _fail(f"no such test file: {candidate}")
        test_paths.append(candidate)

    engine_path = _find("nsvee/engine.py", repo, engine_root)
    if engine_path is None:
        return _fail(
            "no NSVEE engine found (looked in the checkout and the runtime tree)"
        )
    engine = _load_module(engine_path, "nsvee_engine")
    if engine is None:
        return _fail(f"the NSVEE engine at {engine_path} could not be loaded")
    contract_path = _find("platform/estate/nsvee_enforcement.py", repo, engine_root)
    if contract_path is None:
        return _fail("no receipt contract found (platform/estate/nsvee_enforcement.py)")
    enforcement = _load_module(contract_path, "nsvee_enforcement")
    if enforcement is None:
        return _fail(f"the receipt contract at {contract_path} could not be loaded")

    try:
        artifact = artifact_path.read_text()
        tests = [p.read_text() for p in test_paths]
    except OSError as exc:
        return _fail(f"cannot read the artifact: {exc}")

    # The artifact lives inside the tree the receipt binds to. A receipt that names a file
    # outside its tree could not be re-checked against that tree, which would make it a
    # claim rather than a binding.
    covered = [artifact_path, *test_paths]
    try:
        paths = sorted(p.relative_to(repo).as_posix() for p in covered)
    except ValueError:
        return _fail(
            "the artifact and its tests must live inside the tree the receipt binds to "
            f"({repo})"
        )

    runner, kind = _runner(engine)
    try:
        report = engine.verify(
            artifact,
            tests,
            runner=runner,
            timeout_s=args.timeout,
            confirmation_runs=args.confirm,
        )
    except Exception as exc:  # noqa: BLE001 - the door must refuse, not crash
        return _fail(f"the sandbox did not return a verdict: {exc}")

    commit = args.commit.strip() or (_git_commit(repo) or "")
    if len(commit) != 40:
        return _fail("no commit to bind the receipt to (pass --commit)")

    # The digest binds what was verified. A whole-tree digest is the stronger form, but it
    # costs what the tree costs: measured on the idp checkout, hashing 6,425 files took
    # ~60 s (7 ms a file of open overhead, 288 MB) -- more than the executor's whole
    # budget. So the door binds the paths it verified by default, and the whole tree is
    # available to a caller with the time to pay for it (`--whole-tree`, which is what the
    # CI surfaces will use).
    whole_tree = str(args.whole_tree).strip().lower() in {"1", "true", "yes", "on"}
    digest = enforcement.tree_digest(repo, None if whole_tree else paths)

    receipt = {
        "schema": enforcement.SCHEMA,
        "commit": commit,
        "artifact_digest": digest,
        "verifier": "nsvee",
        "status": report.status,
        "paths": None if whole_tree else paths,
        "report": {
            "verdicts": report.verdicts,
            "runs": report.runs,
            "sandbox": kind,
            "artifact": str(artifact_path),
            "error": report.error,
        },
        "oracle": report.oracle,
        "tool_version": "nsvee-verify/1",
    }

    out = Path(args.out).expanduser() if args.out else RECEIPTS / f"{commit}.json"
    if not out.is_absolute():
        out = (Path.cwd() / out).resolve()
    try:
        out.relative_to(repo)
    except ValueError:
        pass
    else:
        return _fail(
            f"the receipt cannot be written inside the tree it describes: {out}"
        )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")

    if args.print_receipt:
        print(json.dumps(receipt, indent=2, sort_keys=True))

    print(
        f"nsvee-verify: status={report.status} verdicts={','.join(report.verdicts)} "
        f"commit={commit} digest={digest[:12]} receipt={out}"
    )
    if not report.ok:
        detail = report.error or "the artifact did not pass"
        print(f"nsvee-verify: REFUSED {artifact_path}: {detail}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
