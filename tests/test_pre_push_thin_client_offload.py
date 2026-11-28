#!/usr/bin/env python3
"""A lane push from a thin client must not need a checkout of the lane (idp#8725).

The hook's production-readiness block demanded `git rev-parse HEAD == pushed sha` and a clean
tree, while bin/estate-zero-worktree refuses the checkout that would make that true. This runs
the REAL block, cut out of .githooks/pre-push, inside a scratch repo whose HEAD is not the pushed
sha, and checks four outcomes. The falsifier runs the same cases against the pre-fix block and
expects the offload case to be refused: a test that cannot fail is not a test.

    python3 tests/test_pre_push_thin_client_offload.py [--optimus]
"""
import os, re, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOOK = os.path.join(ROOT, ".githooks", "pre-push")
SHA = "1" * 40
NEW_REMOTE = "0" * 40


def block(text):
    """The readiness block: from the offload marker (or _readiness_sha) to the Layer 0 line."""
    start = text.find("# idp#8725 thin-client offload")
    if start < 0:
        start = text.index('_readiness_sha=""')
    end = text.index("# Run Layer 0 inline")
    return text[start:end]


def run(code, ref, env_extra):
    with tempfile.TemporaryDirectory() as d:
        def g(*a):
            subprocess.run(["git", "-c", "core.hooksPath=/dev/null", "-c", "commit.gpgsign=false", "-C", d, *a], check=True, capture_output=True)
        g("init", "-q"); g("config", "user.email", "t@t"); g("config", "user.name", "t")
        g("commit", "-q", "--allow-empty", "-m", "base")
        script = f'push_refs="refs/heads/x {SHA} {ref} {NEW_REMOTE}"\n{code}\necho REACHED_END\n'
        env = {"PATH": os.environ["PATH"], "HOME": d, **env_extra}
        p = subprocess.run(["bash", "-c", script], cwd=d, env=env, capture_output=True, text=True, timeout=15)
        return p.returncode, p.stdout + p.stderr


CASES = [
    # name, remote ref, env, expect_pass
    ("thin client lane push offloads", "refs/heads/lane/x", {"IDP_THIN_CLIENT": "1"}, True),
    ("low disk lane push offloads", "refs/heads/lane/x", {"IDP_MIN_FREE_MB": "999999999"}, True),
    ("roomy host, no checkout: strict check refuses", "refs/heads/lane/x", {"IDP_MIN_FREE_MB": "1"}, False),
    ("release push is never offloaded", "refs/heads/release/x", {"IDP_THIN_CLIENT": "1"}, False),
]


def verdicts(code):
    out = []
    for name, ref, env, want in CASES:
        rc, txt = run(code, ref, env)
        passed = rc == 0 and "REACHED_END" in txt
        out.append((name, want, passed, rc, txt))
    return out


def main():
    new = block(open(HOOK).read())
    bad = 0
    for name, want, passed, rc, txt in verdicts(new):
        ok = want == passed
        bad += not ok
        print(("ok   " if ok else "FAIL ") + name + f"  (rc={rc})")
        if not ok:
            print("     " + txt.strip().replace("\n", "\n     ")[:400])
    # Falsifier: the pre-fix block must refuse the offload case, or this test proves nothing.
    old = re.sub(r"_thin_offload\(\) \{.*?\n\}\n", "_thin_offload() { return 1; }\n", new, flags=re.S)
    old = old.replace("if _thin_offload; then", "if false; then")
    fal = [v for v in verdicts(old) if v[0] == CASES[0][0]][0]
    fal_ok = fal[2] is False
    print(("ok   " if fal_ok else "FAIL ") + "falsifier: pre-fix block refuses the thin-client lane push")
    bad += not fal_ok
    if "--optimus" in sys.argv:
        offload_fails = 0 if (not bad) else 1
        print(f"optimus.thin_client.lane_push_needs_checkout={offload_fails}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
