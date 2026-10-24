"""Load the task suite, prove each verifier can tell good from bad, and say whether it is a suite.

Three things this module refuses to be vague about (spec G1, edge cases):

1. A verifier is accepted only if it passes `fixtures/known-good/run.json` and fails
   `fixtures/known-bad/run.json`. If it cannot, the gate aborts before any agent run  -  a verifier
   that cannot tell them apart measures nothing.
2. The suite has a sha. A report names it, and `check_report` refuses a report whose sha is not the
   one on main now.
3. The suite has minimum counts per category. A suite under them does **not** certify G1, and the
   report says so with the missing counts instead of printing a pass rate as if it meant something.
"""

from __future__ import annotations

import hashlib
import importlib.util
import pathlib
import subprocess
from dataclasses import dataclass
from typing import Any, Callable

from gate_schema import Run, Verdict

HERE = pathlib.Path(__file__).resolve().parent
TASKS = HERE / "tasks"
REPO = HERE.parents[1]

# Spec: "Categories and minimum counts: web read 5, form fill 5, calendar 4, email 4, research 4,
# file and canary 3, handoff 3, multi-step 2." Total 30.
MINIMUMS = {
    "web-read": 5,
    "form-fill": 5,
    "calendar": 4,
    "email": 4,
    "research": 4,
    "file-canary": 3,
    "handoff": 3,
    "multi-step": 2,
}

SUITES = TASKS


@dataclass
class Task:
    id: str
    category: str
    surface: str
    prompt: str
    path: pathlib.Path
    verify: Callable[[Run], Verdict]
    cap_usd: float = 0.40  # spec G10: a per-task cap of 40 cents and 40 steps
    step_budget: int = 40
    timeout_s: float = 300.0

    def fixture(self, kind: str) -> pathlib.Path:
        return self.path / "fixtures" / kind / "run.json"


def _load_verify(path: pathlib.Path) -> Callable[[Run], Verdict]:
    spec = importlib.util.spec_from_file_location(f"verify_{path.parent.name}", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load verifier at {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    fn = getattr(mod, "verify", None)
    if not callable(fn):
        raise RuntimeError(f"{path} has no verify(run) function")
    return fn


def load_tasks(only: list[str] | None = None) -> list[Task]:
    if not SUITES.is_dir():
        return []
    found: list[Task] = []
    for d in sorted(SUITES.iterdir()):
        if not d.is_dir():
            continue
        meta_path = d / "task.yaml"
        verify_path = d / "verify.py"
        if not meta_path.exists() or not verify_path.exists():
            raise RuntimeError(f"{d.name}: a task needs task.yaml and verify.py")
        meta = _read_meta(meta_path)
        if only and meta["id"] not in only and d.name not in only:
            continue
        found.append(
            Task(
                id=meta["id"],
                category=meta["category"],
                surface=meta.get("surface", "telegram"),
                prompt=meta["prompt"],
                path=d,
                verify=_load_verify(verify_path),
                cap_usd=float(meta.get("cap_usd", 0.40)),
                step_budget=int(meta.get("step_budget", 40)),
                timeout_s=float(meta.get("timeout_s", 300.0)),
            )
        )
    return found


def _read_meta(path: pathlib.Path) -> dict[str, Any]:
    """A deliberately small reader: `key: value` lines, no dependency, no YAML escapes to get wrong."""
    meta: dict[str, Any] = {}
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            raise RuntimeError(f"{path}: cannot read line {raw!r}")
        k, v = line.split(":", 1)
        meta[k.strip()] = v.strip().strip("\"'")
    for required in ("id", "category", "prompt"):
        if required not in meta:
            raise RuntimeError(f"{path}: missing {required}")
    return meta


def certificate(tasks: list[Task]) -> dict[str, Any]:
    """Does this suite meet the spec's minimums? A report may not claim G1 without this."""
    counts: dict[str, int] = {c: 0 for c in MINIMUMS}
    for t in tasks:
        counts[t.category] = counts.get(t.category, 0) + 1
    missing = {
        c: n - counts.get(c, 0) for c, n in MINIMUMS.items() if counts.get(c, 0) < n
    }
    return {
        "count": len(tasks),
        "counts": counts,
        "minimums": MINIMUMS,
        "missing": missing,
        "certifies_g1": not missing and len(tasks) >= sum(MINIMUMS.values()),
    }


def suite_sha(paths: list[pathlib.Path] | None = None) -> str:
    """The suite's identity: the sha of its files, so a report can be tied to what ran."""
    h = hashlib.sha256()
    roots = paths or [TASKS]
    for root in roots:
        for p in sorted(pathlib.Path(root).rglob("*")):
            if p.is_file():
                h.update(str(p.relative_to(HERE)).encode())
                h.update(p.read_bytes())
    return h.hexdigest()[:16]


def main_suite_sha() -> str | None:
    """The suite sha recorded on main right now, or None when this checkout has no main."""
    try:
        # Read-only, fixed argv, no shell: it reads the sha of origin/main in this checkout.
        out = subprocess.run(  # noqa: S603
            ["/usr/bin/env", "git", "-C", str(REPO), "rev-parse", "origin/main"],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    return out.stdout.strip()


def self_test(tasks: list[Task]) -> tuple[bool, list[dict[str, Any]]]:
    """Every verifier must pass its known-good run and fail its known-bad run (spec G1)."""
    rows: list[dict[str, Any]] = []
    ok = True
    for t in tasks:
        good_p, bad_p = t.fixture("known-good"), t.fixture("known-bad")
        row: dict[str, Any] = {"task": t.id}
        if not good_p.exists() or not bad_p.exists():
            row.update(ok=False, why="missing known-good/known-bad fixture")
            ok = False
            rows.append(row)
            continue
        good = t.verify(Run.load(good_p))
        bad = t.verify(Run.load(bad_p))
        row.update(
            known_good=good.to_dict(),
            known_bad=bad.to_dict(),
            ok=bool(good.ok) and not bad.ok,
        )
        if not row["ok"]:
            ok = False
            if good.ok and bad.ok:
                row["why"] = "verifier passes both: it cannot tell them apart"
            elif not good.ok:
                row["why"] = "verifier fails the known-good run"
            else:
                row["why"] = "verifier passes the known-bad run"
        rows.append(row)
    return ok, rows


def check_report(report: dict[str, Any], tasks: list[Task]) -> tuple[bool, str]:
    """Does a stored report still describe this suite? (spec G1: "the gate refuses a report whose
    suite sha is not the one on main at the time")."""
    cert = certificate(tasks)
    if not report.get("suite_sha"):
        return False, "report carries no suite sha"
    now = suite_sha()
    if report["suite_sha"] != now:
        return False, f"report ran suite {report['suite_sha']}, this checkout has {now}"
    if report.get("pass_rate") is not None and not cert["certifies_g1"]:
        return False, (
            "report claims a pass rate for a suite that does not meet the spec minimums: "
            f"missing {cert['missing']}"
        )
    return True, "report matches this suite"


def leak_check(task_ids: list[str], roots: list[pathlib.Path]) -> list[str]:
    """G1 edge case: task text must not be in the agent's prompt, skills or memory."""
    hits: list[str] = []
    for root in roots:
        p = pathlib.Path(root)
        if not p.exists():
            continue
        for f in p.rglob("*"):
            if not f.is_file() or f.stat().st_size > 2_000_000:
                continue
            try:
                text = f.read_text(errors="ignore")
            except OSError:
                continue
            for tid in task_ids:
                if tid in text:
                    hits.append(f"{f}: {tid}")
    return hits
