#!/usr/bin/env python3
"""Falsifier for estate-protocol verify: known-bad must be REFUSED, known-good ACCEPTED."""
import json
import os
import subprocess
import sys
import tempfile
import time

BIN = os.path.expanduser("~/.estate/bin/estate-protocol")
base = {"protocol": "YIELD/1", "agent": "falsifier",
        "action": {"kind": "probe", "target": "falsifier"}}


def run(args):
    p = subprocess.run([sys.executable, BIN] + args, capture_output=True, text=True)
    return p.returncode, (p.stdout + p.stderr).strip().splitlines()[-1:]


def write(doc):
    fd, path = tempfile.mkstemp(suffix=".json")
    with os.fdopen(fd, "w") as fh:
        json.dump(doc, fh)
    return path


def case(name, doc, want_code, want_word):
    rc, out = run(["verify", write(doc)])
    line = out[0] if out else ""
    ok = (rc == want_code) and (want_word in line)
    print(("PASS " if ok else "FAIL ") + name + " rc=" + str(rc) + " :: " + line)
    return ok


results = []

# 1. printed hash that no command produced -> FALSE-EVIDENCE
results.append(case("fake-sha256-refused",
    dict(base, numbers={"duration_ms": 1, "tokens_in": 0, "tokens_out": 0, "cost_usd": 0.0,
                        "disk_free_mb": 9999, "tests_pass": 7, "tests_fail": 0},
         evidence=["a" * 64], verdict="E3", cmd=["echo", "1 passed"], exit=0),
    1, "REFUSED"))

# 2. numbers typed, not measured -> FAKE-NUMBERS
gen = subprocess.run([sys.executable, BIN, "run", "--agent", "falsifier", "--kind", "probe",
                      "--target", "falsifier", "--operating",
                      "echo 'probe: service answering 200'", "--", "sh", "-c",
                      "echo '5 passed'; echo '0 failed'"], capture_output=True, text=True)
good = json.load(open(os.path.expanduser("~/.estate/protocol/last.json")))
forged = json.loads(json.dumps(good))
forged["numbers"]["tests_pass"] = 500
results.append(case("typed-numbers-refused", forged, 1, "REFUSED"))

# 3. declared, not operating -> NOT-OPERATING
declared = json.loads(json.dumps(good))
declared["operating"] = {"capability": "probe", "status": "declared", "command": "echo ok",
                         "line": "claimed ok", "observed": "claimed ok", "exit": 0,
                         "observed_at": int(time.time()), "proof_sha256": "b" * 64}
results.append(case("declared-receipt-refused", declared, 1, "REFUSED"))

# 4. no cmd -> UNPROVEN (this is what prose YIELD/1 was)
nocmd = {k: v for k, v in good.items() if k != "cmd"}
results.append(case("prose-yield-unproven", nocmd, 1, "REFUSED"))

# 4. genuine record -> VERIFIED
results.append(case("genuine-verified", good, 0, "VERIFIED"))

print("PROTOCOL FALSIFIER " + ("PASS" if all(results) else "FAIL") + " " + str(sum(results)) + "/" + str(len(results)))
sys.exit(0 if all(results) else 1)
