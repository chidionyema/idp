# wake-blocked: demo

A PR was closed on 2026-08-27 because it needed idp#400 first. Its body carries one line:

```
Blocked-by: idp#400
```

idp#400 merges. Within 30 minutes the `wake-blocked` workflow in that repo prints:

```
{"number": 412, "action": "wake", "landed": ["idp#400"], "note": "branch updated from base"}
wake-blocked: 3 sleeping, 1 woke, 0 capped, open=7 cap=10
```

and the PR is open again with the comment: `Blocked-by idp#400 landed; branch updated from base; reopened and re-queued for review (crew#504 CP7, idp-wake-blocked).` A branch GitHub could not update cleanly is reopened with the `needs-rebase` label and the comment says so. The other two sleeping PRs print `"action": "sleep"` with the keys they still wait on.

Offline, the same decision on a file:

```
$ bin/idp-wake-blocked --pulls pulls.json --open 3 --landed idp#400 --dry-run
{"number": 1, "action": "wake", "landed": ["idp#400"]}
{"number": 2, "action": "sleep", "waiting": ["crew#999"]}
{"number": 4, "action": "sleep", "waiting": ["secret signoz-root"]}
wake-blocked: 3 sleeping, 1 woke, 0 capped, open=3 cap=10
```
