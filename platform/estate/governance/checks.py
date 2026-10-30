"""The law checks: every law is a machine decision, and every check can be made to fail.

THE FOUNDER'S RULE (2026-10-29): "my laws need to be gated", "a gate that cannot fail is not a
gate" (AGENTS.md section 9, R2), "any tiny flow where cosmetic or technical we not letting in",
"you touch any component, even existing ones, you need to find its original spec and ensure
it's doing what it's supposed to do".

So a law is not a sentence. A law is:

    id          GOV-001
    law         the sentence, quoted from the founder
    source      where the founder said it
    severity    block | warn
    check       the machine decision that decides the law
    falsifier   a known-bad fixture the check MUST reject, run in CI (R2: a gate that cannot
                fail is not a gate)

A check is a small, typed operation. Every check returns (ok: bool, detail: str). Every check
runs against a root directory, so the falsifier can run it against a fixture tree instead of
the repository -- that is how a gate proves it can fail.

CHECK TYPES
    file_exists {path}
    file_absent {path}
    grep_present {path, pattern}          regex, python syntax
    grep_absent {path, pattern}
    yaml_key {file, path, equals?}        dotted path, e.g. "router_settings.fallbacks"
    yaml_key_present {file, path}
    command {argv, cwd?}                  exit 0 means pass
    workflow_strict {workflow, allow[]}   no continue-on-error outside the allowlist
    diff_cosmetic {base, head}           a change with no behaviour in it
    diff_proof_required {base, head}     a change with no proof attached
    diff_spec_trace {base, head}         a change to a component with no spec behind it
"""

from __future__ import annotations

import fnmatch
import json
import os
import re
import subprocess
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))

# Files whose diff is pure behaviour-neutral by nature, so the cosmetic check does not
# accuse a formatter of changing nothing.
COSMETIC_EXEMPT_SUFFIX = (".md", ".txt", ".svg", ".lock")


def _rel(root: str, path: str) -> str:
    return path if os.path.isabs(path) else os.path.join(root, path)


def _read(root: str, path: str) -> Optional[str]:
    try:
        with open(_rel(root, path), encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return None


def _load_yaml(path: str) -> Any:
    try:
        import yaml  # type: ignore
    except ImportError:
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f)
    except (OSError, ValueError):
        return None


def _dig(data: Any, dotted: str) -> Tuple[bool, Any]:
    cur = data
    for part in dotted.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return False, None
    return True, cur


# --- the diff-based checks ---------------------------------------------------------------------


def _git(root: str, args: List[str]) -> Tuple[int, str]:
    try:
        proc = subprocess.run(  # noqa: S603 - argv is data
            ["git", *args],  # noqa: S607 - git resolves from PATH on purpose
            cwd=root,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 1, f"{type(exc).__name__}: {exc}"
    return proc.returncode, proc.stdout


def _changed_files(root: str, base: str, head: str) -> List[str]:
    """The files this change touches, including work that is not committed yet.

    `git diff <base>` compares the base tree with the working tree, so an uncommitted edit is
    judged too. A diff that only saw committed work would let anything uncommitted pass a gate
    that cannot see it, which is a gate that fails open.
    """
    code, out = _git(root, ["diff", "--name-only", base])
    if code != 0:
        code, out = _git(root, ["diff", "--name-only", f"{base}...{head}"])
    if code != 0:
        code, out = _git(root, ["diff", "--name-only", base, head])
    if code != 0:
        return []
    return [line.strip() for line in out.splitlines() if line.strip()]


def _diff(root: str, base: str, head: str) -> str:
    code, out = _git(root, ["diff", "--unified=0", base])
    if code != 0:
        code, out = _git(root, ["diff", "--unified=0", f"{base}...{head}"])
    if code != 0:
        code, out = _git(root, ["diff", "--unified=0", base, head])
    return out if code == 0 else ""


def _strip_noise(diff: str) -> Tuple[List[str], List[str]]:
    """The diff with the noise removed: blank lines, comment-only lines, and the moved-line
    markers. What is left is behaviour: the lines added and the lines removed.

    A change that only reformats is one whose added lines are the same as its removed lines
    once the noise is gone. That is the comparison the cosmetic law decides on.
    """
    added: List[str] = []
    removed: List[str] = []
    for line in diff.splitlines():
        if line.startswith(("+++", "---", "diff ", "index ")):
            continue
        if line.startswith("+"):
            body = line[1:].strip()
            if not body or body.startswith(("#", "//", "*", "/*")):
                continue
            added.append(body)
        elif line.startswith("-"):
            body = line[1:].strip()
            if not body or body.startswith(("#", "//", "*", "/*")):
                continue
            removed.append(body)
    return added, removed


def check_diff_cosmetic(root: str, spec: Dict[str, Any]) -> Tuple[bool, str]:
    """A change that alters no behaviour is refused: 'any tiny flow where cosmetic or
    technical we not letting in'."""
    base = spec.get("base", "origin/main")
    head = spec.get("head", "HEAD")
    files = _changed_files(root, base, head)
    if not files:
        return True, "no changed files"
    diff = _diff(root, base, head)
    if not diff:
        return True, "no diff available to judge (nothing to refuse)"
    added, removed = _strip_noise(diff)
    if sorted(added) != sorted(removed):
        return True, f"{len(files)} changed file(s) carry behaviour"
    return False, (
        f"{len(files)} changed file(s) carry no behaviour at all "
        f"({', '.join(files[:5])}): cosmetic or technical-only changes are not let in"
    )


def check_diff_proof_required(root: str, spec: Dict[str, Any]) -> Tuple[bool, str]:
    """Every change carries proof: a test that moved with it, or a Proof: trailer."""
    base = spec.get("base", "origin/main")
    head = spec.get("head", "HEAD")
    files = _changed_files(root, base, head)
    if not files:
        return True, "no changed files"
    has_test = any(
        f.startswith("tests/")
        or ".test." in f
        or f.startswith("test_")
        or "/test_" in f
        for f in files
    )
    code, message = _git(root, ["log", "--format=%B", f"{base}..{head}"])
    if code == 0 and re.search(r"^Proof:", message, re.MULTILINE):
        return True, "the change carries a Proof: trailer"
    if has_test:
        return True, "the change carries its test"
    return False, (
        "the change carries no proof: no test moved with it and no Proof: trailer names the "
        "command that shows the behaviour changed"
    )


def check_diff_spec_trace(root: str, spec: Dict[str, Any]) -> Tuple[bool, str]:
    """A changed component must map to a spec: 'you touch any component, even existing ones,
    you need to find its original spec and ensure it's doing what it's supposed to do'.

    `components` maps a path pattern to the spec id that governs it. A changed file that
    matches no pattern is unmapped; a pattern that names a spec nobody registered is a
    broken trace, and both are refused.
    """
    base = spec.get("base", "origin/main")
    head = spec.get("head", "HEAD")
    components = spec.get("components") or {}
    files = _changed_files(root, base, head)
    if not files:
        return True, "no changed files"
    known = set()
    specs_path = os.path.join(root, "platform", "estate", "governance", "specs.yaml")
    try:
        import yaml  # type: ignore

        with open(specs_path, encoding="utf-8") as f:
            known = {
                str(s.get("id")) for s in (yaml.safe_load(f) or {}).get("specs", [])
            }
    except Exception:  # noqa: BLE001 - an unreadable spec file means the trace is unprovable
        known = set()
    mapped = set()
    unknown_specs = []
    for pattern, spec_id in components.items():
        if known and spec_id not in known:
            unknown_specs.append(f"{pattern} -> {spec_id}")
        for f in files:
            if fnmatch.fnmatch(f, pattern):
                mapped.add(f)
    unmapped = [f for f in files if f not in mapped]
    if unknown_specs:
        return False, (
            "the trace names specs nobody registered: " + ", ".join(unknown_specs[:6])
        )
    if not unmapped:
        return (
            True,
            f"{len(files)} changed file(s) all trace to a component with a spec",
        )
    return False, (
        "changed files with no component spec behind them: "
        + ", ".join(unmapped[:8])
        + " (find the original spec, or ask the founder)"
    )


# --- the file and content checks ----------------------------------------------------------------


def check_file_exists(root: str, spec: Dict[str, Any]) -> Tuple[bool, str]:
    path = spec["path"]
    if os.path.exists(_rel(root, path)):
        return True, f"{path} exists"
    return False, f"{path} does not exist"


def check_file_absent(root: str, spec: Dict[str, Any]) -> Tuple[bool, str]:
    path = spec["path"]
    if not os.path.exists(_rel(root, path)):
        return True, f"{path} is absent"
    return False, f"{path} exists and must not"


def check_grep_present(root: str, spec: Dict[str, Any]) -> Tuple[bool, str]:
    text = _read(root, spec["path"])
    if text is None:
        return False, f"{spec['path']} cannot be read"
    if re.search(spec["pattern"], text, re.MULTILINE | re.DOTALL):
        return True, f"{spec['path']} carries the required enforcement"
    return False, f"{spec['path']} does not carry the required enforcement"


def check_grep_absent(root: str, spec: Dict[str, Any]) -> Tuple[bool, str]:
    text = _read(root, spec["path"])
    if text is None:
        return True, f"{spec['path']} is absent (nothing to refuse)"
    if re.search(spec["pattern"], text, re.MULTILINE | re.DOTALL):
        return False, f"{spec['path']} still carries the forbidden pattern"
    return True, f"{spec['path']} is clean"


def check_yaml_key(root: str, spec: Dict[str, Any]) -> Tuple[bool, str]:
    data = _load_yaml(_rel(root, spec["file"]))
    if data is None:
        return False, f"{spec['file']} cannot be parsed as yaml"
    found, value = _dig(data, spec["path"])
    if not found:
        return False, f"{spec['file']} has no key {spec['path']}"
    if "equals" in spec and value != spec["equals"]:
        return (
            False,
            f"{spec['file']} {spec['path']} is {value!r}, expected {spec['equals']!r}",
        )
    return True, f"{spec['file']} {spec['path']} = {value!r}"


def check_yaml_key_present(root: str, spec: Dict[str, Any]) -> Tuple[bool, str]:
    data = _load_yaml(_rel(root, spec["file"]))
    if data is None:
        return False, f"{spec['file']} cannot be parsed as yaml"
    found, _ = _dig(data, spec["path"])
    if found:
        return True, f"{spec['file']} carries {spec['path']}"
    return False, f"{spec['file']} has no key {spec['path']}"


def check_command(root: str, spec: Dict[str, Any]) -> Tuple[bool, str]:
    argv = list(spec.get("argv") or [])
    if not argv:
        return False, "no argv"
    cwd = spec.get("cwd") or root
    try:
        proc = subprocess.run(  # noqa: S603 - argv is data
            argv,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=spec.get("timeout", 120),
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, f"{' '.join(argv)}: {type(exc).__name__}: {exc}"
    tail = (proc.stdout or proc.stderr or "").strip().splitlines()
    line = tail[-1] if tail else ""
    if proc.returncode == 0:
        return True, f"{' '.join(argv)} exited 0: {line}"
    return False, f"{' '.join(argv)} exited {proc.returncode}: {line}"


def check_workflow_strict(root: str, spec: Dict[str, Any]) -> Tuple[bool, str]:
    """CI must not treat a required gate as advisory (R1: gates fail open).

    `jobs:` narrows the decision to the jobs the merge queue gates on; without it every job in
    the file is judged. `steps:` also judges a step's continue-on-error inside those jobs.
    """
    path = spec["workflow"]
    text = _read(root, path)
    if text is None:
        return False, f"{path} cannot be read"
    allow = list(spec.get("allow") or [])
    wanted = spec.get("jobs")
    offenders: List[str] = []
    data = _load_yaml(_rel(root, path))
    if isinstance(data, dict) and isinstance(data.get("jobs"), dict):
        for job_name, job in data["jobs"].items():
            if wanted and job_name not in wanted:
                continue
            if job_name in allow:
                continue
            if not isinstance(job, dict):
                continue
            if job.get("continue-on-error"):
                offenders.append(f"job {job_name} sets continue-on-error")
            if spec.get("steps"):
                for step in job.get("steps") or []:
                    if not isinstance(step, dict):
                        continue
                    if step.get("continue-on-error"):
                        label = str(step.get("name") or step.get("uses") or "step")
                        if any(a in label for a in allow):
                            continue
                        offenders.append(
                            f"job {job_name} step '{label}' sets continue-on-error"
                        )
    else:
        for i, line in enumerate(text.splitlines()):
            if "continue-on-error" not in line:
                continue
            if any(a in line for a in allow):
                continue
            offenders.append(f"{i + 1}: {line.strip()}")
    if offenders:
        return False, f"{path} has advisory gates: " + " | ".join(offenders[:5])
    return True, f"{path} has no advisory gates outside the allowlist"


def check_router_fallbacks(root: str, spec: Dict[str, Any]) -> Tuple[bool, str]:
    """Every model group the router serves must have a fallback chain.

    The defect this closes is measured: `minimax_m27` served requests with no fallback entry,
    so one vendor's bad minute became "No fallback model group found for original
    model_group=minimax_m27" and an HTTP 500 for the caller.
    """
    path = spec.get("file", "llm/config.yaml")
    data = _load_yaml(_rel(root, path))
    if not isinstance(data, dict):
        return False, f"{path} cannot be parsed as yaml"
    groups = []
    for row in data.get("model_list") or []:
        if isinstance(row, dict) and row.get("model_name"):
            groups.append(str(row["model_name"]))
    fallbacks = (data.get("router_settings") or {}).get("fallbacks") or []
    have = set()
    for row in fallbacks:
        if isinstance(row, dict):
            have.update(str(k) for k in row)
    excepts = spec.get("except") or []
    missing = [
        g
        for g in sorted(set(groups))
        if g not in have and not any(fnmatch.fnmatch(g, pat) for pat in excepts)
    ]
    if missing:
        return False, (
            f"{path}: model group(s) with no fallback chain: {', '.join(missing)}"
        )
    return True, f"{path}: every served model group has a fallback chain"


def _load_tree_module(root: str, name: str):
    """Load platform/estate/governance/<name>.py from the tree under test.

    The check must run the tree's own module, not the one already imported here: a law that
    is proved against a different copy of the code is not a law of the tree.
    """
    import importlib.util
    import sys
    import types

    pkg_dir = os.path.join(root, "platform", "estate", "governance")
    path = os.path.join(pkg_dir, name + ".py")
    if not os.path.isfile(path):
        return None
    pkg_name = "govprobe_" + name
    pkg = types.ModuleType(pkg_name)
    pkg.__path__ = [pkg_dir]
    sys.modules[pkg_name] = pkg
    spec = importlib.util.spec_from_file_location(pkg_name + "." + name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def check_executor_permission(root: str, spec: Dict[str, Any]) -> Tuple[bool, str]:
    """The direct-executor permission must be earned, and must be able to say no.

    A permission that only ever says yes is a promise, not a gate. So the check drives the
    decision function with a green and a red input and insists on both answers.
    """
    try:
        perm = _load_tree_module(root, "executor_permission")
    except Exception as exc:  # noqa: BLE001 - a module that cannot load cannot grant
        return (
            False,
            f"executor_permission.py did not load: {type(exc).__name__}: {exc}",
        )
    if perm is None:
        return False, "platform/estate/governance/executor_permission.py is missing"

    green = perm.evaluate(
        "check-session",
        root=root,
        claim="1",
        gate_report={"results": [{"id": "GOV-000", "verdict": "pass"}]},
        state={"locked": False},
        live_claims=["1"],
    )
    if not green["granted"]:
        return (
            False,
            f"a green gate, an unlocked session and a live claim were refused: {green['reasons']}",
        )

    red = perm.evaluate(
        "check-session",
        root=root,
        claim="1",
        gate_report={
            "results": [
                {"id": "GOV-001", "verdict": "fail", "detail": "the law is red"}
            ]
        },
        state={"locked": False},
        live_claims=["1"],
    )
    if red["granted"]:
        return False, "a red law gate still granted the direct executor"

    empty = perm.evaluate(
        "check-session",
        root=root,
        claim="1",
        gate_report={"results": []},
        state={"locked": False},
        live_claims=["1"],
    )
    if empty["granted"]:
        return False, "a gate that reported no laws still granted the direct executor"

    locked = perm.evaluate(
        "check-session",
        root=root,
        gate_report={"results": [{"id": "GOV-000", "verdict": "pass"}]},
        state={"locked": True},
        live_claims=["1"],
    )
    if locked["granted"]:
        return False, "a locked session was granted the direct executor"

    unclaimed = perm.evaluate(
        "check-session",
        root=root,
        gate_report={"results": [{"id": "GOV-000", "verdict": "pass"}]},
        state={"locked": False},
        live_claims=[],
    )
    if unclaimed["granted"]:
        return False, "a session with no live claim was granted the direct executor"

    return (
        True,
        "the direct executor is granted only on a green gate, an unlocked session and a live claim",
    )


CHECKS = {
    "file_exists": check_file_exists,
    "file_absent": check_file_absent,
    "grep_present": check_grep_present,
    "grep_absent": check_grep_absent,
    "yaml_key": check_yaml_key,
    "yaml_key_present": check_yaml_key_present,
    "command": check_command,
    "workflow_strict": check_workflow_strict,
    "diff_cosmetic": check_diff_cosmetic,
    "diff_proof_required": check_diff_proof_required,
    "diff_spec_trace": check_diff_spec_trace,
    "router_fallbacks": check_router_fallbacks,
    "executor_permission": check_executor_permission,
}


def advisory_gates_in(root: str, workflow: str) -> List[Dict[str, str]]:
    """Every continue-on-error in one workflow, with the job it sits in.

    A continue-on-error is only a fail-open gate when a failure there is ignored where it
    matters. Three cases, decided by the file itself:

      fail-open  another job depends on this one, so the tolerated failure decides nothing
      compensated a later step in the same job reads what this one produced and fails
                 closed when it is missing
      not-a-gate nothing depends on the job in this workflow: a notification, not a gate
    """
    out: List[Dict[str, str]] = []
    data = _load_yaml(_rel(root, workflow))
    if not isinstance(data, dict) or not isinstance(data.get("jobs"), dict):
        return out
    jobs = data["jobs"]
    dependents: Dict[str, List[str]] = {}
    for job_name, job in jobs.items():
        if not isinstance(job, dict):
            continue
        needs = job.get("needs") or []
        if isinstance(needs, str):
            needs = [needs]
        for need in needs:
            dependents.setdefault(str(need), []).append(job_name)

    for job_name, job in jobs.items():
        if not isinstance(job, dict):
            continue
        if job.get("continue-on-error"):
            out.append(
                {
                    "workflow": workflow,
                    "job": job_name,
                    "where": "job",
                    "class": "fail-open" if job_name in dependents else "not-a-gate",
                    "why": (
                        f"{', '.join(dependents.get(job_name, []))} depends on this job"
                        if job_name in dependents
                        else "nothing depends on this job in this workflow"
                    ),
                }
            )
        steps = job.get("steps") or []
        for index, step in enumerate(steps):
            if not isinstance(step, dict) or not step.get("continue-on-error"):
                continue
            label = str(step.get("name") or step.get("uses") or "step")
            later = json.dumps(steps[index + 1 :], default=str)
            produced = str((step.get("with") or {}).get("path") or "")
            consumed = bool(produced) and produced.split("/")[-1].split("*")[0] in later
            if consumed:
                klass = "compensated"
                why = "a later step in the same job fails closed when the artefact is missing"
            elif job_name in dependents:
                klass = "fail-open"
                why = f"{', '.join(dependents.get(job_name, []))} depends on this job"
            else:
                klass = "not-a-gate"
                why = "nothing depends on this job in this workflow"
            out.append(
                {
                    "workflow": workflow,
                    "job": job_name,
                    "where": f"step {label}",
                    "class": klass,
                    "why": why,
                }
            )
    return out


def run_check(root: str, spec: Dict[str, Any]) -> Tuple[bool, str]:
    kind = spec.get("type", "")
    fn = CHECKS.get(kind)
    if fn is None:
        return False, f"unknown check type '{kind}'"
    try:
        return fn(root, spec)
    except Exception as exc:  # noqa: BLE001 - a broken check fails the law, never passes it
        return False, f"check '{kind}' raised {type(exc).__name__}: {exc}"
