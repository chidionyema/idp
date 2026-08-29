"""crew#539 (2026-08-28 00:28Z, oke-check run 33129788480).

The recovery receipt after the Cilium outage (36 Flux rows, 40 pods each carrying its last log)
outgrew the kernel's per-argument limit and every grader that did `python3 - "$head" "$body"`
died with `Argument list too long` (exit 126) — the estate graded BLIND at the moment it most
needed reading. The class: a bucket receipt handed to a child process through argv. The guard
grades the thing itself: every grader that fetches a receipt hands it over as a file, and the
extracted grader still reads a body larger than ARG_MAX.
"""
from __future__ import annotations

import pathlib
import re
import os
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
BIN = ROOT / "bin"
RECEIPT_GRADERS = [
    "idp-chaos-drill", "idp-cluster-state", "idp-door-heartbeat",
    "idp-kini-state", "idp-science-facts", "idp-telemetry-coverage",
]


def test_no_grader_passes_the_receipt_body_through_argv():
    # A receipt body sits in `$body`; the child must be given a path, never the value.
    bad = []
    for name in RECEIPT_GRADERS:
        src = (BIN / name).read_text()
        if re.search(r'python3\s+-\s+"\$head"\s+"\$body"', src):
            bad.append(name)
        assert "bodyf=$(mktemp)" in src, f"{name} does not write the body to a file"
    assert not bad, f"receipt body still travels by argv in: {bad}"


def test_extracted_grader_reads_a_body_larger_than_arg_max(tmp_path):
    src = (BIN / "idp-cluster-state").read_text()
    py = src.split("<<'PY'\n", 1)[1].split("\nPY\n", 1)[0]
    # 1 MiB of padding inside a still-valid JSON body: far past MAX_ARG_STRLEN (128 KiB).
    body = 'ok cluster-state\n{"at": "2026-08-28T00:00:00Z", "nodes": [], "pods_not_ready": [], "flux_not_ready": [], "pad": "' + "x" * (1 << 20) + '"}'
    f = tmp_path / "receipt"
    f.write_text(body)
    r = subprocess.run([sys.executable, "-c", py, '{"last-modified": "Thu, 28 Aug 2026 00:00:00 GMT", "date": "Thu, 28 Aug 2026 00:00:01 GMT"}', str(f), "1000000", ""],
                       capture_output=True, text=True, check=False, env={**os.environ, "IDP_LIB": str(ROOT / "bin" / "lib")})
    assert r.returncode != 126, r.stderr
    assert "Argument list too long" not in r.stderr
    # The grader reached the body (it may FAIL on the toy receipt); it never went BLIND on transport.
    assert "BLIND" not in r.stdout, r.stdout
    assert r.stdout.split()[0] in ("ok", "FAIL"), r.stdout
