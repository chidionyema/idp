# Demo: the circuit breaker

Three identical findings lock the primitive and name the fleet lever. Diagnosis stays free; only
proved repetition stops.

## Run it

```bash
bin/idp-circuit-breaker --finding "$(gh run view ... --log)" --target pr-3253
bin/idp-circuit-breaker --check --finding "$(gh run view ... --log)" --target pr-3254
```

## What you see

Fed three real failing build logs from three different pull requests, on 2026-09-12:

```
#3253  fp=cve:CVE-2026-13221,CVE-2026-42496,CVE-2026-8376  count=1  locked=False
#3258  fp=cve:CVE-2026-13221,CVE-2026-42496,CVE-2026-8376  count=2  locked=False
#3254  fp=cve:CVE-2026-13221,CVE-2026-42496,CVE-2026-8376  count=3  locked=True
```

Those three logs differ — different line positions, different stacks, two different Dockerfiles.
A hash of the raw output would never have matched them. The fingerprint is the CVE set, and it is
the same on all three, so the breaker knows the diagnosis is done.

The fourth target is refused:

```
423 Locked: proven pattern (N=3). 3 target(s) carry
cve:CVE-2026-13221,CVE-2026-42496,CVE-2026-8376; the cause is proved, so the linear
action is disabled. This is not a refusal of the target -- it is a refusal to repeat
the proof.
```

And the refusal carries the lever, because a wall with no door is an outage:

```
the finding is in the image or the base, so it is one fix for every target: fix it once
on main and refresh the fleet -- `gh workflow run merge-when-green.yml`
```

## Two rules that stop it being an outage

**A fingerprint, not a raw hash.** Same cause, different bytes. The CVE set is order-free: the
same three CVEs in a different order are one finding.

**Scoped to the finding, not the target or the tool.** A different finding on a locked target is
allowed. Nine pull requests with nine different causes never lock at all — which is the case that
would make a cruder breaker block correct work.
