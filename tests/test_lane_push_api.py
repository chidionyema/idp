"""bin/lane-push-api judges an API push by the rules a git push meets in the hook.

The rules are proved with real tools: git merge-file, main's real bin/catalog-merge and the real
pinned ruff. Only GitHub is replaced -- by a `gh` shim over an in-memory repository -- so the
order of the writes (the claim is stamped BEFORE the commit is authored, and nothing is written
when a rule refuses) is read from the shim's log, not asserted from the code.
"""

# Pytest assertions are test checks, never runtime input validation.
# ruff: noqa: S101, S603, S607
from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOOR = ROOT / "bin" / "lane-push-api"
FORMATTED = "def add(a, b):\n    return a + b\n"
OPENS_ANY_URL = (
    "import urllib.request\n\n\ndef get(url):\n    return urllib.request.urlopen(url)\n"
)


def _load():
    loader = SourceFileLoader("lane_push_api", str(DOOR))
    module = module_from_spec(spec_from_loader("lane_push_api", loader))
    loader.exec_module(module)
    return module


door = _load()


def _metrics(names, unit="bool"):
    rows = [{"name": n, "unit": unit} for n in names]
    return (json.dumps({"version": 1, "metrics": rows}, indent=2) + "\n").encode()


# ------------------------------------------------------------------ pure rules


def test_the_newest_claim_wins():
    got = door.newest_claim(
        [
            "hello",
            "CLAIM agent=a paths=x heartbeat=2026-11-28T01:00:00Z",
            "CLAIM agent=b paths=y heartbeat=2026-11-28T02:00:00Z",
        ]
    )
    assert got == ("b", "y", "2026-11-28T02:00:00Z")
    assert door.newest_claim(["no claim here"]) is None


def test_new_python_outside_tests_needs_its_trailer():
    pushed = {"sovereign/engine/test_x.py": b"x = 1\n", "tests/test_y.py": b"y = 1\n"}
    assert door.language_problems(pushed, set(), "msg") == [
        "sovereign/engine/test_x.py"
    ]
    ok = "msg\n\nLanguage-Exception: sovereign/engine/test_x.py -- reason\n"
    assert door.language_problems(pushed, set(), ok) == []
    assert door.language_problems(pushed, {"sovereign/engine/test_x.py"}, "msg") == []


def test_an_extensionless_python_script_is_judged_by_its_shebang():
    pushed = {
        "bin/tool": b"#!/usr/bin/env python3\nprint(1)\n",
        "bin/sh": b"#!/bin/sh\n",
    }
    assert door.language_problems(pushed, set(), "m") == ["bin/tool"]


def test_a_line_conflict_is_a_conflict_and_disjoint_edits_merge():
    base = b"one\ntwo\nthree\nfour\nfive\nsix\nseven\n"
    assert not door.three_way(
        "f.txt",
        base,
        b"one\nLANE\nthree\nfour\nfive\nsix\nseven\n",
        b"one\nMAIN\nthree\nfour\nfive\nsix\nseven\n",
        None,
    )
    assert door.three_way(
        "f.txt",
        base,
        b"LANE\ntwo\nthree\nfour\nfive\nsix\nseven\n",
        b"one\ntwo\nthree\nfour\nfive\nsix\nMAIN\n",
        None,
    )


def test_two_added_files_with_different_bytes_conflict():
    assert not door.three_way("new.txt", None, b"a\n", b"b\n", None)
    assert door.three_way("new.txt", None, b"a\n", b"a\n", None)


def test_keyed_catalogs_merge_by_key_with_mains_driver_and_same_key_conflicts():
    driver = ROOT / "bin" / "catalog-merge"
    path = "catalog/optimus-metrics.json"
    base = _metrics(["seed"])
    assert door.three_way(
        path, base, _metrics(["seed", "mine"]), _metrics(["seed", "theirs"]), driver
    )
    assert not door.three_way(
        path, base, _metrics(["seed"], "ms"), _metrics(["seed"], "bytes"), driver
    )


# ------------------------------------------------------------------ the door end to end

SHIM = r"""#!/usr/bin/env python3
import base64, hashlib, json, sys
state_path, log_path = sys.argv[0].rsplit("/", 1)[0] + "/state.json", sys.argv[0].rsplit("/", 1)[0] + "/log.txt"
st = json.load(open(state_path))
args = sys.argv[1:]
assert args[0] == "api"
args = args[1:]
method, raw, path, body = "GET", False, None, None
i = 0
while i < len(args):
    a = args[i]
    if a == "-X": method = args[i + 1]; i += 2
    elif a == "-H": raw = True; i += 2
    elif a == "--input": body = json.loads(sys.stdin.read()); method = "POST" if method == "GET" else method; i += 2
    else: path = a; i += 1
path = path.split("repos/chidionyema/idp/", 1)[-1]
def log(s): open(log_path, "a").write(s + "\n")
def out(o): print(json.dumps(o)); sys.exit(0)
def sha(data): return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()
def save(): json.dump(st, open(state_path, "w"))
q = path.split("?")[0]
if q.startswith("contents/"):
    sys.stdout.buffer.write(base64.b64decode(st["contents"][path[len("contents/") :]])); sys.exit(0)
if q == "git/ref/heads/main": out({"object": {"sha": "MAIN"}})
if q.startswith("git/ref/heads/lane/"):
    lane = q[len("git/ref/heads/"):]
    if lane in st["lanes"]: out({"object": {"sha": st["lanes"][lane]}})
    sys.stderr.write("HTTP 404"); sys.exit(1)
if q.startswith("git/commits/") and method == "GET":
    c = q.split("/")[-1]; out({"tree": {"sha": "T" + c}, "message": "m"})
if q.startswith("git/trees/") and method == "GET":
    t = q.split("/")[-1][1:]
    out({"truncated": False, "tree": [{"path": p, "sha": v[0], "mode": v[1], "type": "blob"} for p, v in st["trees"][t].items()]})
if q.startswith("compare/"):
    out({"merge_base_commit": {"sha": st.get("base", "MAIN")}, "commits": st.get("commits", [])})
if q.startswith("git/blobs/"):
    out({"content": base64.b64encode(base64.b64decode(st["blobs"][q.split("/")[-1]])).decode()})
if q.startswith("issues/") and method == "GET":
    out([{"body": b} for b in st["comments"]])
if q.startswith("issues/") and method == "POST":
    log("CLAIM " + body["body"]); st["comments"].append(body["body"]); save(); out({})
if q == "git/blobs": log("BLOB"); d = base64.b64decode(body["content"]); st["blobs"][sha(d)] = body["content"]; save(); out({"sha": sha(d)})
if q == "git/trees": log("TREE"); out({"sha": "NEWTREE"})
if q == "git/commits": log("COMMIT " + json.dumps(body["message"])); out({"sha": "NEWCOMMIT"})
if q == "git/refs": log("REF " + body["ref"]); out({})
if q.startswith("git/refs/heads/"): log("PATCH " + str(body["force"])); out({})
sys.stderr.write("shim: unhandled " + method + " " + path); sys.exit(1)
"""


def _ruff_version() -> str:
    ruff = shutil.which("ruff")
    assert ruff, "ruff is not installed: this proof never skips the formatter"
    got = subprocess.run(
        [ruff, "--version"], capture_output=True, text=True, check=True
    ).stdout
    return re.search(r"ruff (\d+\.\d+\.\d+)", got).group(1)


def _blob(data: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()  # noqa: S324


def _world(tmp_path, comments=None, lane=None, main_extra=None):
    shim_dir = tmp_path / "shim"
    shim_dir.mkdir()
    gh = shim_dir / "gh"
    gh.write_text(SHIM)
    gh.chmod(0o755)
    b64 = lambda data: base64.b64encode(data).decode()  # noqa: E731
    pyproject = b"[tool.ruff]\nline-length = 88\n"
    ferrari = f'TRUSTED_RUFF_VERSION = "{_ruff_version()}"\n'.encode()
    main_tree = {"README.md": (_blob(b"hi\n"), "100644")}
    blobs = {_blob(b"hi\n"): b64(b"hi\n")}
    for name, data in (main_extra or {}).items():
        main_tree[name] = (_blob(data), "100644")
        blobs[_blob(data)] = b64(data)
    state = {
        "contents": {
            "greenlane/ferrari.py?ref=main": b64(ferrari),
            "pyproject.toml?ref=main": b64(pyproject),
            "bin/catalog-merge?ref=main": b64(
                (ROOT / "bin" / "catalog-merge").read_bytes()
            ),
        },
        "lanes": {"lane/x": "LANE"} if lane else {},
        "trees": {"MAIN": main_tree, "LANE": lane or main_tree},
        "blobs": blobs,
        "comments": comments
        if comments is not None
        else ["CLAIM agent=me paths=a,b heartbeat=2026-11-28T00:00:00Z"],
    }
    (shim_dir / "state.json").write_text(json.dumps(state))
    return shim_dir


def _push(tmp_path, shim_dir, files, message="work\n", agent="me", dry=False):
    work = tmp_path / "work"
    work.mkdir(exist_ok=True)
    for rel, text in files.items():
        (work / rel).parent.mkdir(parents=True, exist_ok=True)
        (work / rel).write_text(text)
    msg = tmp_path / "msg.txt"
    msg.write_text(message)
    env = {**os.environ, "PATH": f"{shim_dir}:{os.environ['PATH']}"}
    if dry:
        env["PUSH_DRY_RUN"] = "1"
    proc = subprocess.run(
        [
            sys.executable,
            str(DOOR),
            "--lane",
            "lane/x",
            "--claim",
            "chidionyema/idp#1",
            "--agent",
            agent,
            "--message-file",
            str(msg),
            "--dir",
            str(work),
            *files,
        ],
        capture_output=True,
        text=True,
        env=env,
        timeout=120,
        check=False,
    )
    log = (
        (shim_dir / "log.txt").read_text().splitlines()
        if (shim_dir / "log.txt").exists()
        else []
    )
    return proc, log


def test_a_clean_push_stamps_the_claim_before_it_authors_the_commit(tmp_path):
    shim = _world(tmp_path)
    proc, log = _push(tmp_path, shim, {"docs/note.md": "hello\n"})
    assert proc.returncode == 0, proc.stdout + proc.stderr
    kinds = [line.split()[0] for line in log]
    assert kinds.index("CLAIM") < kinds.index("COMMIT") < kinds.index("REF")
    assert "CLAIM agent=me paths=a,b heartbeat=" in log[0]


def test_unformatted_python_is_refused_and_nothing_is_written(tmp_path):
    shim = _world(tmp_path)
    proc, log = _push(tmp_path, shim, {"tests/test_f.py": "def f( a ):\n  return a\n"})
    assert proc.returncode == 1
    assert "not formatted by ruff" in proc.stderr
    assert log == []


def test_a_python_strict_finding_is_refused_and_nothing_is_written(tmp_path):
    # 2026-11-28: lane 76dd398e passed ruff format and went red on fast-gate's py-strict rung.
    shim = _world(tmp_path)
    proc, log = _push(tmp_path, shim, {"tests/net_probe.py": OPENS_ANY_URL})
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert "python-strict" in proc.stderr
    assert "tests/net_probe.py" in proc.stderr
    assert "S310" in proc.stderr
    assert log == []


def test_a_justified_noqa_passes_python_strict(tmp_path):
    shim = _world(tmp_path)
    ok = OPENS_ANY_URL.replace(
        "urlopen(url)", "urlopen(url)  # noqa: S310 -- https enforced by the caller"
    )
    proc, _ = _push(tmp_path, shim, {"tests/net_probe.py": ok})
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "ok    python-strict" in proc.stdout


def test_strict_problems_ratchets_a_file_already_off_standard_at_its_base(tmp_path):
    door = _load()
    ruff, _ = door.pinned_ruff(f'TRUSTED_RUFF_VERSION = "{_ruff_version()}"\n')
    cfg = tmp_path / "pyproject.toml"
    cfg.write_text("[tool.ruff]\nline-length = 88\n")
    bad = OPENS_ANY_URL.encode()
    refused, notes = door.strict_problems(ruff, cfg, {"tests/a.py": bad}, {})
    assert [r.split(" ")[0] for r in refused] == ["tests/a.py"] and not notes
    refused, notes = door.strict_problems(
        ruff, cfg, {"tests/a.py": bad}, {"tests/a.py": bad}
    )
    assert not refused and notes == ["tests/a.py"]


def test_new_colocated_python_without_the_trailer_is_refused_with_the_line_to_add(
    tmp_path,
):
    shim = _world(tmp_path)
    proc, log = _push(tmp_path, shim, {"sovereign/engine/test_t.py": FORMATTED})
    assert proc.returncode == 1
    assert "Language-Exception: sovereign/engine/test_t.py" in proc.stderr
    assert log == []
    ok, _ = _push(
        tmp_path,
        shim,
        {"sovereign/engine/test_t.py": FORMATTED},
        "w\n\nLanguage-Exception: sovereign/engine/test_t.py -- covered\n",
    )
    assert ok.returncode == 0, ok.stdout + ok.stderr


def test_a_rival_claim_refuses_before_any_write(tmp_path):
    shim = _world(
        tmp_path,
        comments=[
            "CLAIM agent=me paths=a heartbeat=2026-11-28T00:00:00Z",
            "CLAIM agent=rival paths=a heartbeat=2026-11-28T00:10:00Z",
        ],
    )
    proc, log = _push(tmp_path, shim, {"docs/note.md": "x\n"})
    assert proc.returncode == 1
    assert "rival" in proc.stderr
    assert not any(line.startswith(("BLOB", "TREE", "COMMIT", "REF")) for line in log)


def test_a_lane_that_conflicts_with_a_moved_main_is_refused(tmp_path):
    base = b"one\ntwo\nthree\nfour\nfive\nsix\nseven\n"
    lane_tree = {
        "README.md": (_blob(b"hi\n"), "100644"),
        "f.txt": (_blob(base), "100644"),
    }
    shim = _world(
        tmp_path,
        lane=lane_tree,
        main_extra={"f.txt": b"one\nMAIN\nthree\nfour\nfive\nsix\nseven\n"},
    )
    state = json.loads((shim / "state.json").read_text())
    state["trees"]["BASE"] = lane_tree
    state["base"] = "BASE"
    state["blobs"][_blob(base)] = base64.b64encode(base).decode()
    (shim / "state.json").write_text(json.dumps(state))
    proc, log = _push(
        tmp_path, shim, {"f.txt": "one\nLANE\nthree\nfour\nfive\nsix\nseven\n"}
    )
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert "does not merge onto main" in proc.stderr and "f.txt" in proc.stderr
    assert log == []


def test_dry_run_judges_and_writes_nothing_not_even_the_claim(tmp_path):
    shim = _world(tmp_path)
    proc, log = _push(tmp_path, shim, {"docs/note.md": "hello\n"}, dry=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "dry run" in proc.stdout
    assert log == []


def test_the_ref_update_is_never_forced(tmp_path):
    lane_tree = {"README.md": (_blob(b"hi\n"), "100644")}
    shim = _world(tmp_path, lane=lane_tree)
    proc, log = _push(tmp_path, shim, {"docs/note.md": "hello\n"})
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "PATCH False" in log


def test_the_commit_carries_the_claim_and_agent_lines_claim_gate_reads(tmp_path):
    """Measured 2026-11-28: lanes went red at Greenlane with `no live claim: no Claim line`."""
    shim = _world(tmp_path)
    proc, log = _push(tmp_path, shim, {"docs/note.md": "hello\n"}, message="work\n")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    message = json.loads(
        next(x for x in log if x.startswith("COMMIT ")).split(" ", 1)[1]
    )
    assert "\nClaim: chidionyema/idp#1\n" in message
    assert "\nAgent: me\n" in message


def test_a_message_that_already_has_the_lines_is_not_given_a_second_pair(tmp_path):
    shim = _world(tmp_path)
    own = "work\n\nClaim: chidionyema/idp#1\nAgent: me\n"
    proc, log = _push(tmp_path, shim, {"docs/note.md": "hello\n"}, message=own)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    message = json.loads(
        next(x for x in log if x.startswith("COMMIT ")).split(" ", 1)[1]
    )
    assert message.count("Claim:") == 1
    assert message.count("Agent:") == 1
