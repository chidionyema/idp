#!/usr/bin/env python3
"""Run rederive-verdict with an import hook that fails the moment science_loop is reached for.

A comment claiming independence is not independence. This runs the tool for real, with every
import intercepted, and exits non-zero if the tool ever tries to load science_loop (or spawn a
process, which is the other way it could borrow the tool's arithmetic).
"""

import builtins
import os
import runpy
import subprocess
import sys

R = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "artifacts", "rederive-verdict"
)
DB = "/Users/roseonyema/.estate/science/science-proof.db"

real_import = builtins.__import__
touched = []


def guard(name, *a, **k):
    if "science_loop" in name:
        touched.append(name)
        raise ImportError(f"BLIND rederive-verdict tried to import {name}")
    return real_import(name, *a, **k)


builtins.__import__ = guard


def no_spawn(*a, **k):
    touched.append("subprocess")
    raise RuntimeError("BLIND rederive-verdict tried to spawn a process")


for attr in ("run", "call", "check_output", "check_call", "Popen"):
    setattr(subprocess, attr, no_spawn)
os.system = no_spawn  # type: ignore[assignment]

sys.argv = ["rederive-verdict", "--db", DB]
code = 0
try:
    runpy.run_path(R, run_name="__main__")
except SystemExit as e:
    code = e.code if isinstance(e.code, int) else 1
finally:
    builtins.__import__ = real_import

print()
if touched:
    print(f"FAIL isolation broken: {touched}")
    sys.exit(4)
print(
    f"PASS ran with science_loop imports poisoned and process spawning disabled; "
    f"exit was {code}, nothing was reached for"
)
sys.exit(0 if code == 0 else 4)
