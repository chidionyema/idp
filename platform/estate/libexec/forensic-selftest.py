#!/usr/bin/env python3
"""forensic-selftest.py - prove the forensic replay engines against the REAL runtimes.

The replay engine in forensic_replay.py reconstructs what Pi and Cline did to a
file. This script is its falsifier: it runs the same cases through the real
runtimes and compares byte for byte.

  Pi    the installed @earendil-works/pi-coding-agent edit engine, run by node
        through forensic-pi-oracle.mjs.
  Cline the upstream Cline editor and apply-patch executors, fetched at test time
        from a PINNED upstream commit into ~/.estate/cache/forensic-oracle/cline/
        and run by node --experimental-transform-types through
        forensic-cline-oracle.ts.

Upstream source is never vendored into this repository: it is fetched, pinned and
hashed at test time, so the oracle is the upstream implementation and its
provenance is checkable.

Exit codes:
  0  every suite that could run passed
  1  a suite ran and found a defect (the port disagrees with the runtime)
  3  a suite could not run (no node, no network, upstream moved): PENDING.
     A pending suite is never reported as a pass.

Usage: python3 forensic-selftest.py [--json]
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import forensic_replay as fr  # noqa: E402

CLINE_COMMIT = "a6507a62a147db4a35e27f4294589742ccac5060"
CLINE_RAW = (
    "https://raw.githubusercontent.com/cline/cline/"
    + CLINE_COMMIT
    + "/sdk/packages/core/src/extensions/tools/executors/"
)
CLINE_FILES = (
    "editor.ts",
    "apply-patch.ts",
    "apply-patch-parser.ts",
    "line-endings.ts",
)
CACHE = os.path.expanduser("~/.estate/cache/forensic-oracle/cline")
UPSTREAM_DIR = os.path.join(CACHE, "upstream")
PROVENANCE = os.path.join(CACHE, "provenance.json")
# A synthetic cwd for the oracle only: it is never created or written to, it only gives the
# oracle a stable path to print. noqa because the literal path is the point.
CWD = "/tmp/cline-fake-cwd"  # noqa: S108
# The Cline oracle runs in a fresh os.tmpdir(); the platform spells it differently, so both
# shapes are normalised away before the two engines are compared.
TMP_CASE_RE = r"(?:/var/folders/[^\"\\]+/T|/tmp)/clinecase-[A-Za-z0-9]+"  # noqa: S108
PI_ORACLE = os.path.join(HERE, "forensic-pi-oracle.mjs")
CLINE_ORACLE = os.path.join(HERE, "forensic-cline-oracle.ts")


# ---------------------------------------------------------------------------- node


def find_node():
    """The node binary, or None. Node is required: without it nothing can be proven."""
    found = shutil.which("node")
    if found:
        return found
    nvm = os.path.expanduser("~/.nvm/versions/node")
    if os.path.isdir(nvm):
        versions = sorted(os.listdir(nvm), reverse=True)
        for version in versions:
            candidate = os.path.join(nvm, version, "bin", "node")
            if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                return candidate
    return None


# --------------------------------------------------------------------------- cases


def pi_cases():
    out = []
    out.append(
        {
            "name": "single edit",
            "base": "hello\nworld\n",
            "edits": [{"oldText": "world", "newText": "there"}],
        }
    )
    out.append(
        {
            "name": "two edits matched against the original",
            "base": "aaa\nbbb\nccc\n",
            "edits": [
                {"oldText": "aaa", "newText": "AAA"},
                {"oldText": "ccc", "newText": "CCC"},
            ],
        }
    )
    out.append(
        {
            "name": "two edits, the second depends on the first's text",
            "base": "x\n",
            "edits": [
                {"oldText": "x", "newText": "y"},
                {"oldText": "y", "newText": "z"},
            ],
        }
    )
    out.append(
        {
            "name": "duplicate oldText",
            "base": "dup\ndup\n",
            "edits": [{"oldText": "dup", "newText": "D"}],
        }
    )
    out.append(
        {
            "name": "empty oldText",
            "base": "a\n",
            "edits": [{"oldText": "", "newText": "b"}],
        }
    )
    out.append(
        {
            "name": "oldText not found",
            "base": "a\n",
            "edits": [{"oldText": "zzz", "newText": "b"}],
        }
    )
    out.append(
        {
            "name": "identical replacement",
            "base": "a\n",
            "edits": [{"oldText": "a", "newText": "a"}],
        }
    )
    out.append(
        {
            "name": "fuzzy: trailing whitespace drift",
            "base": "line one   \nline two\n",
            "edits": [{"oldText": "line one", "newText": "line ONE"}],
        }
    )
    out.append(
        {
            "name": "fuzzy: smart quotes",
            "base": "he said \u201chello\u201d\n",
            "edits": [{"oldText": 'he said "hello"', "newText": 'he said "bye"'}],
        }
    )
    out.append(
        {
            "name": "fuzzy: unicode dash and nbsp",
            "base": "a\u2014b\u00a0c\n",
            "edits": [{"oldText": "a-b c", "newText": "z"}],
        }
    )
    out.append(
        {
            "name": "fuzzy mixed with exact",
            "base": "keep\ntrail   \nother\n",
            "edits": [
                {"oldText": "keep", "newText": "KEPT"},
                {"oldText": "trail", "newText": "TRAIL"},
            ],
        }
    )
    out.append(
        {
            "name": "overlapping edits",
            "base": "abcdef\n",
            "edits": [
                {"oldText": "abcd", "newText": "X"},
                {"oldText": "cdef", "newText": "Y"},
            ],
        }
    )
    out.append(
        {
            "name": "crlf file",
            "base": "one\r\ntwo\r\n",
            "edits": [{"oldText": "two", "newText": "2"}],
        }
    )
    out.append(
        {
            "name": "crlf file, multi-line edit",
            "base": "one\r\ntwo\r\nthree\r\n",
            "edits": [{"oldText": "one\ntwo", "newText": "ONE\nTWO"}],
        }
    )
    out.append(
        {
            "name": "bom file",
            "base": "\ufeff#!/bin/sh\necho hi\n",
            "edits": [{"oldText": "echo hi", "newText": "echo bye"}],
        }
    )
    out.append(
        {
            "name": "bom and crlf",
            "base": "\ufeffa\r\nb\r\n",
            "edits": [{"oldText": "a", "newText": "A"}],
        }
    )
    out.append(
        {
            "name": "no trailing newline in base",
            "base": "abc",
            "edits": [{"oldText": "abc", "newText": "abcd"}],
        }
    )
    out.append(
        {
            "name": "edit spanning to end of file",
            "base": "a\nb\nc\n",
            "edits": [{"oldText": "b\nc\n", "newText": "B\n"}],
        }
    )
    out.append(
        {
            "name": "multi-line exact edit",
            "base": "one\ntwo\nthree\nfour\n",
            "edits": [{"oldText": "two\nthree", "newText": "TWO\nTHREE\nEXTRA"}],
        }
    )
    out.append(
        {
            "name": "same oldText twice in one call",
            "base": "a\na\n",
            "edits": [
                {"oldText": "a", "newText": "b"},
                {"oldText": "a", "newText": "c"},
            ],
        }
    )
    out.append(
        {
            "name": "empty file base",
            "base": "",
            "edits": [{"oldText": "a", "newText": "b"}],
        }
    )
    out.append(
        {
            "name": "tabs and trailing spaces preserved",
            "base": "\tindented   \n\tother\n",
            "edits": [{"oldText": "\tother", "newText": "\tOTHER"}],
        }
    )
    return out


def cline_cases():
    return [
        # --- editor ---
        {
            "name": "editor replace",
            "tool": "editor",
            "path": "f.txt",
            "base": "hello\nworld\n",
            "input": {"path": "f.txt", "old_text": "world", "new_text": "there"},
        },
        {
            "name": "editor replace multiline",
            "tool": "editor",
            "path": "f.txt",
            "base": "one\ntwo\nthree\n",
            "input": {
                "path": "f.txt",
                "old_text": "two\nthree",
                "new_text": "TWO\nTHREE\nEXTRA",
            },
        },
        {
            "name": "editor replace not found",
            "tool": "editor",
            "path": "f.txt",
            "base": "hello\n",
            "input": {"path": "f.txt", "old_text": "zzz", "new_text": "x"},
        },
        {
            "name": "editor replace multiple occurrences",
            "tool": "editor",
            "path": "f.txt",
            "base": "dup\ndup\n",
            "input": {"path": "f.txt", "old_text": "dup", "new_text": "D"},
        },
        {
            "name": "editor create when missing",
            "tool": "editor",
            "path": "f.txt",
            "base": None,
            "input": {"path": "f.txt", "new_text": "created\n"},
        },
        {
            "name": "editor new_text only on existing file",
            "tool": "editor",
            "path": "f.txt",
            "base": "exists\n",
            "input": {"path": "f.txt", "new_text": "new\n"},
        },
        {
            "name": "editor old_text null on existing file",
            "tool": "editor",
            "path": "f.txt",
            "base": "exists\n",
            "input": {"path": "f.txt", "old_text": None, "new_text": "new\n"},
        },
        {
            "name": "editor insert_line middle",
            "tool": "editor",
            "path": "f.txt",
            "base": "one\ntwo\nthree\n",
            "input": {"path": "f.txt", "insert_line": 2, "new_text": "inserted\n"},
        },
        {
            "name": "editor insert_line at EOF",
            "tool": "editor",
            "path": "f.txt",
            "base": "one\ntwo\n",
            "input": {"path": "f.txt", "insert_line": 3, "new_text": "three\n"},
        },
        {
            "name": "editor insert_line out of range",
            "tool": "editor",
            "path": "f.txt",
            "base": "one\ntwo\n",
            "input": {"path": "f.txt", "insert_line": 9, "new_text": "x\n"},
        },
        {
            "name": "editor insert_line missing file",
            "tool": "editor",
            "path": "f.txt",
            "base": None,
            "input": {"path": "f.txt", "insert_line": 1, "new_text": "x\n"},
        },
        {
            "name": "editor crlf replacement",
            "tool": "editor",
            "path": "f.txt",
            "base": "one\r\ntwo\r\n",
            "input": {"path": "f.txt", "old_text": "two", "new_text": "TWO"},
        },
        {
            "name": "editor crlf insert_line keeps the file ending",
            "tool": "editor",
            "path": "f.txt",
            "base": "one\r\ntwo\r\n",
            "input": {"path": "f.txt", "insert_line": 2, "new_text": "inserted\n"},
        },
        {
            "name": "editor create keeps the new text ending",
            "tool": "editor",
            "path": "f.txt",
            "base": None,
            "input": {"path": "f.txt", "new_text": "created\r\nwith crlf\r\n"},
        },
        {
            "name": "editor dollar in new_text is literal",
            "tool": "editor",
            "path": "f.txt",
            "base": "value: X\n",
            "input": {"path": "f.txt", "old_text": "X", "new_text": "$& and $1 and $$"},
        },
        {
            "name": "editor absolute path",
            "tool": "editor",
            "path": "f.txt",
            "abs": True,
            "base": "hello\n",
            "input": {
                "path": None,
                "abs_path": True,
                "old_text": "hello",
                "new_text": "bye",
            },
        },
        {
            "name": "editor diff budget truncates",
            "tool": "editor",
            "path": "f.txt",
            "base": "".join("line %d\n" % i for i in range(1, 401)),
            "input": {
                "path": "f.txt",
                "old_text": "".join("line %d\n" % i for i in range(1, 351)),
                "new_text": "".join("new %d\n" % i for i in range(1, 351)),
            },
        },
        # --- apply_patch ---
        {
            "name": "patch add file",
            "tool": "apply_patch",
            "path": "new.txt",
            "base": None,
            "input": {
                "input": "*** Begin Patch\n*** Add File: new.txt\n+line one\n+line two\n*** End Patch"
            },
        },
        {
            "name": "patch add existing file",
            "tool": "apply_patch",
            "path": "f.txt",
            "base": "exists\n",
            "input": {
                "input": "*** Begin Patch\n*** Add File: f.txt\n+x\n*** End Patch"
            },
        },
        {
            "name": "patch update with context",
            "tool": "apply_patch",
            "path": "f.txt",
            "base": "alpha\nbeta\ngamma\n",
            "input": {
                "input": "*** Begin Patch\n*** Update File: f.txt\n@@\n beta\n-gamma\n+delta\n*** End Patch"
            },
        },
        {
            "name": "patch update missing file",
            "tool": "apply_patch",
            "path": "f.txt",
            "base": None,
            "input": {
                "input": "*** Begin Patch\n*** Update File: f.txt\n@@\n-x\n+y\n*** End Patch"
            },
        },
        {
            "name": "patch delete file",
            "tool": "apply_patch",
            "path": "f.txt",
            "base": "alpha\nbeta\n",
            "input": {
                "input": "*** Begin Patch\n*** Delete File: f.txt\n*** End Patch"
            },
        },
        {
            "name": "patch update with def_str anchor",
            "tool": "apply_patch",
            "path": "f.py",
            "base": "def foo():\n    return 1\n\ndef bar():\n    return 2\n",
            "input": {
                "input": "*** Begin Patch\n*** Update File: f.py\n@@ def foo():\n-    return 1\n+    return 42\n*** End Patch"
            },
        },
        {
            "name": "patch update with context drift",
            "tool": "apply_patch",
            "path": "f.txt",
            "base": "alpha\nbeta\ngamma\n",
            "input": {
                "input": "*** Begin Patch\n*** Update File: f.txt\n@@\n-beta\n+beta2\n*** End Patch"
            },
        },
        {
            "name": "patch update with no matching context",
            "tool": "apply_patch",
            "path": "f.txt",
            "base": "alpha\nbeta\n",
            "input": {
                "input": "*** Begin Patch\n*** Update File: f.txt\n@@\n-zzz\n+yyy\n*** End Patch"
            },
        },
        {
            "name": "patch update crlf file",
            "tool": "apply_patch",
            "path": "f.txt",
            "base": "alpha\r\nbeta\r\n",
            "input": {
                "input": "*** Begin Patch\n*** Update File: f.txt\n@@\n-beta\n+delta\n*** End Patch"
            },
        },
        {
            "name": "patch update appends lines",
            "tool": "apply_patch",
            "path": "f.txt",
            "base": "alpha\n",
            "input": {
                "input": "*** Begin Patch\n*** Update File: f.txt\n@@\n alpha\n+beta\n+gamma\n*** End Patch"
            },
        },
        {
            "name": "patch without sentinels",
            "tool": "apply_patch",
            "path": "f.txt",
            "base": "alpha\nbeta\n",
            "input": {"input": "*** Update File: f.txt\n@@\n-beta\n+delta\n"},
        },
        {
            "name": "patch with two hunks",
            "tool": "apply_patch",
            "path": "f.txt",
            "base": "one\ntwo\nthree\nfour\nfive\n",
            "input": {
                "input": "*** Begin Patch\n*** Update File: f.txt\n@@\n-one\n+ONE\n@@\n-five\n+FIVE\n*** End Patch"
            },
        },
    ]


# ------------------------------------------------------------------- cline oracle


def prepare_cline_oracle():
    """Fetch the pinned upstream executors into the estate cache.

    Returns (state, detail) where state is "ready", "pending" or "failed".
    A cache hit is reused; a cache miss needs the network. Either way the
    provenance (commit, url, sha256) is written next to the files.
    """
    try:
        os.makedirs(CACHE, exist_ok=True)
        os.makedirs(UPSTREAM_DIR, exist_ok=True)
    except OSError as err:
        return "failed", "cannot create %s: %s" % (CACHE, err)

    provenance = {}
    if os.path.exists(PROVENANCE):
        try:
            with open(PROVENANCE, encoding="utf-8") as handle:
                provenance = json.load(handle)
        except (OSError, ValueError):
            provenance = {}

    fetched = []
    for name in CLINE_FILES:
        upstream_path = os.path.join(UPSTREAM_DIR, name)
        want = ((provenance.get("files") or {}).get(name) or {}).get("upstream_sha256")
        cached = os.path.isfile(upstream_path) and os.path.getsize(upstream_path) > 0
        if cached and want:
            with open(upstream_path, "rb") as handle:
                got = hashlib.sha256(handle.read()).hexdigest()
            if got == want:
                continue
        fetched.append(name)

    errors = []
    for name in fetched:
        url = CLINE_RAW + name
        try:
            with urllib.request.urlopen(url, timeout=30) as response:  # noqa: S310
                body = response.read()
        except Exception as err:  # noqa: BLE001 - any transport failure is pending
            errors.append("%s: %s" % (name, err))
            continue
        with open(os.path.join(UPSTREAM_DIR, name), "wb") as handle:
            handle.write(body)

    missing = [
        n
        for n in CLINE_FILES
        if not (
            os.path.isfile(os.path.join(UPSTREAM_DIR, n))
            and os.path.getsize(os.path.join(UPSTREAM_DIR, n))
        )
    ]
    if missing:
        detail = "upstream fetch failed for %s" % ", ".join(missing)
        if errors:
            detail += ": %s" % "; ".join(errors)
        return "pending", detail
    if errors:
        return "pending", "upstream fetch failed for some files: %s" % "; ".join(errors)

    # Node's ESM resolver needs the extension on a relative specifier; upstream Cline is
    # built by a bundler and writes "./line-endings". The upstream bytes are kept
    # pristine in upstream/ and hashed; the runnable copy differs only by that one
    # mechanical rewrite, and both hashes are recorded.
    files_record = provenance.setdefault("files", {})
    for name in CLINE_FILES:
        upstream_path = os.path.join(UPSTREAM_DIR, name)
        with open(upstream_path, "rb") as handle:
            raw = handle.read()
        text = raw.decode("utf-8")
        rewrites = []

        def _rewrite(match, rewrites=rewrites):
            spec = match.group(1)
            base = os.path.basename(spec)
            if "." in base:
                return match.group(0)
            if base + ".ts" in CLINE_FILES:
                rewrites.append(spec + " -> " + spec + ".ts")
                return 'from "%s.ts"' % spec
            return match.group(0)

        patched = re.sub(r'from "(\./[^"]+)"', _rewrite, text)
        with open(os.path.join(CACHE, name), "w", encoding="utf-8") as handle:
            handle.write(patched)
        files_record[name] = {
            "upstream_sha256": hashlib.sha256(raw).hexdigest(),
            "runnable_sha256": hashlib.sha256(patched.encode("utf-8")).hexdigest(),
            "rewrites": rewrites,
        }

    # the harness imports the upstream files by relative path, so it lives beside them
    try:
        shutil.copyfile(CLINE_ORACLE, os.path.join(CACHE, "forensic-cline-oracle.ts"))
    except OSError as err:
        return "failed", "cannot stage the harness: %s" % err

    provenance.update(
        {
            "commit": CLINE_COMMIT,
            "url": CLINE_RAW,
            "generator": "forensic-selftest.py",
        }
    )
    try:
        with open(PROVENANCE, "w", encoding="utf-8") as handle:
            json.dump(provenance, handle, indent=2, sort_keys=True)
    except OSError:
        pass
    return "ready", "pinned upstream %s in %s" % (CLINE_COMMIT[:12], CACHE)


# ------------------------------------------------------------------------- suites


def run_pi_suite(node):
    cs = pi_cases()
    payload = [{"base": c["base"], "edits": c["edits"], "path": "f.txt"} for c in cs]
    cases_path = os.path.join(HERE, ".selftest-pi-cases.json")
    with open(cases_path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False)
    try:
        proc = subprocess.run(  # noqa: S603 -- a fixed argv: the discovered node and a local file
            [node, PI_ORACLE, cases_path], capture_output=True, text=True, timeout=120
        )
    except (OSError, subprocess.TimeoutExpired) as err:
        return "pending", "the Pi oracle could not run: %s" % err, 0, len(cs)
    finally:
        if os.path.exists(cases_path):
            os.remove(cases_path)
    if proc.returncode == 3:
        return (
            "pending",
            proc.stderr.strip() or "the Pi runtime was not found",
            0,
            len(cs),
        )
    if proc.returncode != 0:
        return (
            "failed",
            "the Pi oracle failed (%d): %s" % (proc.returncode, proc.stderr[-2000:]),
            0,
            len(cs),
        )
    try:
        expected = json.loads(proc.stdout)
    except ValueError as err:
        return "failed", "the Pi oracle printed no JSON: %s" % err, 0, len(cs)

    failures = 0
    lines = []
    for case, want in zip(cs, expected):  # noqa: B905 -- the oracle returns one case per input
        try:
            got = fr.pi_apply_edit(
                case["base"], {"path": "f.txt", "edits": case["edits"]}, "f.txt"
            )
            got = {"ok": True, "content": got["content"]}
        except fr.ReplayError as err:
            got = {"ok": False, "error": str(err)}
        except Exception as err:  # noqa: BLE001
            got = {"ok": False, "error": "%s: %s" % (type(err).__name__, err)}
        if got != want:
            failures += 1
            lines.append(
                "FAIL %s\n  want: %s\n  got : %s"
                % (
                    case["name"],
                    json.dumps(want, ensure_ascii=False),
                    json.dumps(got, ensure_ascii=False),
                )
            )
        else:
            lines.append("ok   %s" % case["name"])
    state = "fail" if failures else "pass"
    return state, "\n".join(lines), failures, len(cs)


def run_cline_suite(node):
    ready, detail = prepare_cline_oracle()
    if ready != "ready":
        return ready, detail, 0, 0

    cs = cline_cases()
    payload = []
    for case in cs:
        entry = {
            "tool": case["tool"],
            "path": case["path"],
            "base": case["base"],
            "input": dict(case["input"]),
            "abs": bool(case.get("abs")),
        }
        if case.get("abs"):
            entry["input"]["path"] = os.path.join(CWD, case["path"])
        payload.append(entry)
    cases_path = os.path.join(CACHE, ".selftest-cline-cases.json")
    with open(cases_path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False)
    oracle = os.path.join(CACHE, "forensic-cline-oracle.ts")
    try:
        proc = subprocess.run(  # noqa: S603 -- a fixed argv: the discovered node and a local file
            [node, "--experimental-transform-types", oracle, cases_path],
            capture_output=True,
            text=True,
            cwd=CACHE,
            timeout=180,
        )
    except (OSError, subprocess.TimeoutExpired) as err:
        return "pending", "the Cline oracle could not run: %s" % err, 0, len(cs)
    finally:
        if os.path.exists(cases_path):
            os.remove(cases_path)
    if proc.returncode != 0:
        return (
            "failed",
            "the Cline oracle failed (%d): %s" % (proc.returncode, proc.stderr[-2000:]),
            0,
            len(cs),
        )
    try:
        expected = json.loads(proc.stdout)
    except ValueError as err:
        return "failed", "the Cline oracle printed no JSON: %s" % err, 0, len(cs)

    failures = 0
    lines = []
    for case, want in zip(cs, expected):  # noqa: B905 -- the oracle returns one case per input
        files = {}
        if case["base"] is not None:
            files[os.path.join(CWD, case["path"])] = case["base"]

        def fs_read(abs_path, files=files):
            return files.get(abs_path)

        input_args = dict(case["input"])
        if case.get("abs"):
            input_args["path"] = os.path.join(CWD, case["path"])

        if case["tool"] == "editor":
            try:
                result = fr.cline_editor_apply(input_args, CWD, fs_read)
                got = {
                    "ok": True,
                    "message": result["message"],
                    "content": result["content"],
                }
            except fr.ReplayError as err:
                got = {"ok": False, "error": str(err)}
            except Exception as err:  # noqa: BLE001
                got = {"ok": False, "error": "%s: %s" % (type(err).__name__, err)}
        else:
            try:
                result = fr.cline_apply_patch_changes(input_args["input"], CWD, fs_read)
                message = ["Successfully applied patch to the following files:"]
                message.extend(result["touched"])
                got = {
                    "ok": True,
                    "message": "\n".join(message),
                    "content": {
                        p: c["new_content"] for p, c in result["changes"].items()
                    },
                }
            except fr.ReplayError as err:
                got = {"ok": False, "error": str(err)}
            except Exception as err:  # noqa: BLE001
                got = {"ok": False, "error": "%s: %s" % (type(err).__name__, err)}

        want_norm = json.loads(re.sub(TMP_CASE_RE, "<CWD>", json.dumps(want)))
        want_norm = json.loads(re.sub(re.escape(CWD), "<CWD>", json.dumps(want_norm)))
        got_norm = json.loads(re.sub(re.escape(CWD), "<CWD>", json.dumps(got)))

        if want_norm.get("ok") and got_norm.get("ok"):
            if want_norm.get("message") != got_norm.get("message"):
                failures += 1
                lines.append(
                    "FAIL %s (message)\n  want: %r\n  got : %r"
                    % (case["name"], want_norm.get("message"), got_norm.get("message"))
                )
                continue
            wc = want_norm.get("content")
            gc = got_norm.get("content")
            if isinstance(wc, dict):
                if not isinstance(gc, dict):
                    failures += 1
                    lines.append("FAIL %s (content shape)" % case["name"])
                    continue
                if wc != gc:
                    failures += 1
                    lines.append(
                        "FAIL %s (content)\n  want: %r\n  got : %r"
                        % (case["name"], wc, gc)
                    )
                    continue
            elif wc != gc:
                failures += 1
                lines.append(
                    "FAIL %s (content)\n  want: %r\n  got : %r" % (case["name"], wc, gc)
                )
                continue
            lines.append("ok   %s" % case["name"])
        else:
            if want_norm.get("error") != got_norm.get("error"):
                failures += 1
                lines.append(
                    "FAIL %s (error)\n  want: %r\n  got : %r"
                    % (case["name"], want_norm.get("error"), got_norm.get("error"))
                )
            else:
                lines.append("ok   %s" % case["name"])

    state = "fail" if failures else "pass"
    return state, "\n".join(lines), failures, len(cs)


# ---------------------------------------------------------------------------- main


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true", help="print the report as JSON")
    ap.add_argument("--verbose", action="store_true", help="print every case")
    args = ap.parse_args()

    node = find_node()
    report = {"node": node, "suites": []}
    exit_code = 0

    if node is None:
        for name in ("pi", "cline"):
            report["suites"].append(
                {
                    "name": name,
                    "state": "pending",
                    "detail": "node was not found on this machine",
                }
            )
        exit_code = 3
    else:
        for name, runner in (("pi", run_pi_suite), ("cline", run_cline_suite)):
            try:
                state, detail, failures, total = runner(node)
            except Exception as err:  # noqa: BLE001
                state, detail, failures, total = (
                    "failed",
                    "%s: %s" % (type(err).__name__, err),
                    0,
                    0,
                )
            report["suites"].append(
                {
                    "name": name,
                    "state": state,
                    "detail": detail,
                    "failures": failures,
                    "total": total,
                }
            )
            if state == "fail":
                exit_code = 1
            elif state == "pending" and exit_code == 0:
                exit_code = 3

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
        return exit_code

    print("forensic self-test")
    print("node: %s" % (node or "NOT FOUND"))
    for suite in report["suites"]:
        print("\n== %s: %s" % (suite["name"], suite["state"].upper()))
        if suite["state"] in ("pass", "fail"):
            if args.verbose:
                print(suite["detail"])
            else:
                failures = suite.get("failures", 0)
                total = suite.get("total", 0)
                print("%d/%d cases match the real runtime" % (total - failures, total))
                if failures:
                    for line in suite["detail"].splitlines():
                        if line.startswith("FAIL") or line.startswith("  "):
                            print(line)
        else:
            print(suite["detail"])
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
