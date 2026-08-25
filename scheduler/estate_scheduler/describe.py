"""Where a scheduled job's description comes from.

A job's description is derived from the script it runs, not written by hand
here. Hand-written prose in schedule.yml would describe what the job did on the
day someone typed it; a module docstring is edited by whoever changes the
behaviour, so it stays true. schedule.yml may still carry an explicit
`description:`, which wins, for the few commands that are not a script we own.

A job whose script has no docstring gets a description saying so, naming the
file to fix. That is deliberate: the Dagster UI then shows the gap instead of
hiding it behind a command line.
"""

from __future__ import annotations

import ast
import os
import re
import shlex
from pathlib import Path

# argv[0] of a wrapped command is an interpreter, not the thing that documents
# the job: `hc-wrap.sh estate-idp $IDP/bin/idp-up` is documented by idp-up, and
# `python3 founder_board.py --html out.html` by founder_board.py and never by
# out.html. So: skip interpreters and wrappers, keep only files that are source
# we own, and take the last one.
INTERPRETERS = {"python", "python3", "python3.9", "python3.11", "python3.12",
                "python3.13", "bash", "sh", "zsh", "env", "node", "ruby",
                "perl", "uv", "uvx"}

# A wrapper's own docstring describes the wrapper. Attributing it to the job
# would put "run a scheduled job under Healthchecks monitoring" on six
# different jobs, which reads as documentation and is not.
WRAPPERS = {"hc-wrap.sh"}

SOURCE_SUFFIXES = {".py", ".sh", ".bash", ".zsh"}
# an output path is an argument too: --html board.html, --out report.json
NOT_SOURCE = {".html", ".json", ".jsonl", ".yml", ".yaml", ".md", ".txt", ".csv",
              ".log", ".db", ".sqlite", ".png", ".svg", ".xml", ".plist", ".toml"}

MAX_LEN = 400

# schedule.yml writes $IDP and $CODE; definitions.py seeds them at import. The
# guard imports this module without definitions.py, so seed them here too --
# same values, derived from this file's own location, never a literal path.
_IDP_ROOT = os.environ.get("IDP_ROOT") or str(Path(__file__).resolve().parents[2])
os.environ.setdefault("IDP", _IDP_ROOT)
os.environ.setdefault("CODE", os.environ.get("CODE_ROOT", str(Path(_IDP_ROOT).parent)))


def _expand(value) -> str:
    return os.path.expandvars(os.path.expanduser(str(value)))


def _is_source(p: Path) -> bool:
    if p.suffix in NOT_SOURCE:
        return False
    if p.suffix in SOURCE_SUFFIXES:
        return True
    # an extensionless bin/ script counts only if it is actually executable
    return p.suffix == "" and os.access(p, os.X_OK)


def target_script(command, cwd=None) -> Path | None:
    """The file in a command line that documents what the job does."""
    if isinstance(command, str):
        command = shlex.split(command)
    command = [str(a) for a in command]
    found = None
    for i, arg in enumerate(command):
        if arg.startswith("-"):
            # `python -m ops.automations.log_rotation` names a module, not a path
            if arg == "-m" and i + 1 < len(command):
                rel = command[i + 1].replace(".", os.sep) + ".py"
                bases = [_expand(cwd)] if cwd else []
                bases.append(os.getcwd())
                for base in bases:
                    cand = Path(base) / rel
                    if cand.is_file():
                        found = cand
                        break
            continue
        p = Path(_expand(arg))
        if p.name in INTERPRETERS or p.name in WRAPPERS:
            continue
        try:
            if p.is_file() and os.access(p, os.R_OK) and _is_source(p):
                found = p
        except OSError:
            continue
    return found


def _first_paragraph(text: str) -> str:
    text = (text or "").strip()
    if not text:
        return ""
    para = " ".join(re.split(r"\n\s*\n", text, maxsplit=1)[0].split())
    if len(para) > MAX_LEN:
        cut = para[:MAX_LEN].rsplit(". ", 1)[0]
        para = (cut + ".") if cut else para[:MAX_LEN].rstrip() + "..."
    return para


def _python_docstring(path: Path) -> str:
    try:
        tree = ast.parse(path.read_text(errors="replace"))
    except (SyntaxError, ValueError, OSError, RecursionError):
        return ""
    return _first_paragraph(ast.get_docstring(tree) or "")


def _header_comment(path: Path) -> str:
    """The leading `#` comment block of a shell script, minus the shebang."""
    lines: list[str] = []
    try:
        with open(path, errors="replace") as f:
            for i, raw in enumerate(f):
                line = raw.rstrip("\n")
                if i == 0 and line.startswith("#!"):
                    continue
                if line.startswith("#"):
                    body = line.lstrip("#").strip()
                    # a divider of ---- or ==== is decoration, not prose
                    if body and not re.fullmatch(r"[-=*_# ]+", body):
                        lines.append(body)
                    elif lines:
                        break
                    continue
                if not line.strip() and not lines:
                    continue
                break
    except OSError:
        return ""
    return _first_paragraph(" ".join(lines))


def from_script(path: Path) -> str:
    if path.suffix == ".py":
        return _python_docstring(path)
    text = _header_comment(path)
    if text:
        return text
    # an extensionless bin/ file may still be python
    try:
        with open(path, errors="replace") as f:
            head = f.readline()
    except OSError:
        return ""
    return _python_docstring(path) if "python" in head else ""


def describe(label: str, spec: dict) -> tuple[str, str]:
    """Return (description, where it came from). Never returns an empty string."""
    explicit = (spec.get("description") or "").strip()
    if explicit:
        return _first_paragraph(explicit), "schedule.yml"
    script = target_script(spec.get("command") or [], spec.get("cwd"))
    if script is None:
        cmd = shlex.join(str(a) for a in (spec.get("command") or []))
        return (f"No description: {label} runs `{cmd}`, which names no readable "
                f"script this repo can quote. Add `description:` to its entry in "
                f"scheduler/schedule.yml."), ""
    return (from_script(script) or
            f"No description: {script} has no module docstring or header comment. "
            f"Write one there and this job documents itself."), str(script)


def is_documented(label: str, spec: dict) -> bool:
    return not describe(label, spec)[0].startswith("No description:")


def _audit(path) -> int:
    """Print one line per job and return 1 if any job would reach the UI opaque."""
    import yaml

    if not Path(path).is_file():
        # a gate that refuses because it could not find its input is not refusing
        # the rule; say so rather than returning a verdict (LAW 28)
        print(f"BLIND  no such schedule file: {path}")
        raise SystemExit(2)
    with open(path) as f:
        spec = (yaml.safe_load(f) or {}).get("jobs") or {}
    bad = 0
    for label in sorted(spec):
        text, source = describe(label, spec[label])
        ok = is_documented(label, spec[label])
        bad += 0 if ok else 1
        print(f"{'ok  ' if ok else 'FAIL'}  {label}\n        {text[:160]}\n"
              f"        from {source or '(no readable script)'}")
    print(f"\n{len(spec) - bad} of {len(spec)} jobs carry a description")
    return 1 if bad else 0


def _selftest() -> int:
    """Prove both ways in one run: the deriver finds a real description and
    refuses to invent one (LAW 38 -- a guard that only ever refuses has never
    been shown to permit)."""
    here = Path(__file__).resolve().parents[2] / "tests" / "fixtures"
    cases = [
        ("finds the docstring behind a wrapper and an interpreter",
         [str(Path.home() / ".claude/scripts/hc-wrap.sh"), "slug", "/usr/bin/python3",
          str(here / "describe" / "documented.py")], True),
        ("refuses a script with no docstring",
         ["/usr/bin/python3", str(here / "describe" / "undocumented.py")], False),
        ("does not mistake an output path for the script",
         ["/usr/bin/python3", "--html", str(here / "describe" / "out.html")], False),
    ]
    bad = 0
    for name, cmd, want in cases:
        got = is_documented("test.case", {"command": cmd})
        print(f"{'ok  ' if got == want else 'FAIL'}  describe {name}")
        bad += 0 if got == want else 1
    return 1 if bad else 0


if __name__ == "__main__":
    import sys

    if "--selftest" in sys.argv:
        raise SystemExit(_selftest())
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    raise SystemExit(_audit(args[0] if args else
                            Path(__file__).resolve().parents[1] / "schedule.yml"))
