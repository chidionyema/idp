# Demo: estate-security-scan

`bin/estate-security-scan` is the "Security passes" receipt named by the
Definition of Done v2.1 (`docs/policy/definition-of-done.md`, Gate 3 and
section 3.3). It answers three questions with three mature tools and prints
one receipt: the UTC timestamp, the commit hash, one line per check, and a
verdict line.

Run on this checkout (founder machine, 2026-08-25):

```
$ bin/estate-security-scan --quiet
SECURITY-SCAN 2026-08-25T18:50:49Z commit=d434e499843abd74ff672cdb1ac37da82b415dce tree=6-dirty-paths
ok    secrets   gitleaks 8.30.1: no leaks in git history
ok    deps      pip-audit over 2 requirements files: no known vulnerabilities
ok    policy    security-policy-gate: every control row has a proof
SECURITY-SCAN PASS commit=d434e49
```

To see a failure, commit a fake key on a throwaway branch and run it again:

```
$ git checkout -b scratch/leak
$ echo 'AWS_SECRET_ACCESS_KEY=AKIAIOSFODNN7EXAMPLEwJalrXUtnFEMI/K7MDENG' > leak.txt
$ git add leak.txt && git commit -qm leak
$ bin/estate-security-scan --quiet
SECURITY-SCAN ... commit=...
FAIL  secrets   gitleaks found leaks in git history
ok    deps      pip-audit over 2 requirements files: no known vulnerabilities
ok    policy    security-policy-gate: every control row has a proof
SECURITY-SCAN FAIL commit=...
$ git checkout - && git branch -D scratch/leak
```

Exit codes: 0 PASS, 1 FAIL, 3 BLIND. BLIND means a tool was missing so a
check could not run; a guard that loses its evidence reports BLIND, never a
verdict. In CI the `security-scan` job installs both tools, so BLIND there is
a broken job, and any non-zero exit blocks merge.

Untracked files such as `llm/.env` are not scanned: they are git-ignored and
never enter the codebase. `gitleaks protect --staged` is the fence for what is
about to.
