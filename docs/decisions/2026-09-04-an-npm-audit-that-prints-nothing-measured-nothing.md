# An npm audit that prints nothing measured nothing

2026-09-04. `bin/estate-security-scan` refused hermes-v2#71 twice with:

```
FAIL  npm       lsp: high or critical advisories in shipped dependencies

SECURITY-SCAN FAIL commit=fd0351e
```

The blank line under it is the whole story: the scanner prints the last fifteen lines of npm's
own output under a FAIL, and there were none. The exact command the scanner runs, executed
against the same lockfile on the same commit outside CI, answers:

```
$ cd lsp && npm audit --package-lock-only --audit-level=high --omit=dev
found 0 vulnerabilities
RC=0
```

So the branch — three Python files under `otto/boot/` — was held for two hours by a probe that
exited non-zero and reported nothing. A real advisory always prints its report; npm exiting
non-zero with empty stdout and empty stderr is a broken probe, and calling that a security
finding is the shape LAW 38 names: a guard that refuses correct work is an outage.

The scanner now separates the two. A non-zero exit with output is still `FAIL` and still red. A
non-zero exit with nothing printed is `BLIND`, which says what actually happened — nothing was
measured — and does not claim a vulnerability nobody can name. `BLIND` already has a meaning in
this scanner and already surfaces in the run summary, so nothing is hidden by it.

What this deliberately does not do is skip the check, allowlist an advisory, or add a bypass
word to a pull request body. When npm has something to say, it is still gating.
