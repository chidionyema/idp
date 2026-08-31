# Demo: The estate inventory

What the founder sees when the grader runs on a cluster dump, then on the Mac. Real output,
command above it, run 2026-08-31 on the first pull request's branch. In the portal the same
counts are the "Estate inventory" tile on the Ops page: one sentence, one line per plane, unread
planes named, and a link to the full table (`Ops.test.tsx` pins the tile's words).

```
$ bin/idp-inventory --fixture tests/fixtures/inventory-kube-dump.json --out /tmp/inv --strict
ok      inventory  kubernetes  MANAGED 4  DRIFTED 1  ORPHAN 2  GHOST 1
ok      inventory  table /tmp/inv/inventory.md  json /tmp/inv/inventory.json
FAIL    inventory  4 rows are not MANAGED (--strict)
$ echo $?
1
```

The same dump with the four red objects removed (`tests/fixtures/inventory-kube-dump-clean.json`),
so the gate is proved both ways:

```
$ bin/idp-inventory --fixture tests/fixtures/inventory-kube-dump-clean.json --out /tmp/inv-clean --strict
ok      inventory  kubernetes  MANAGED 4  DRIFTED 0  ORPHAN 0  GHOST 0
ok      inventory  table /tmp/inv-clean/inventory.md  json /tmp/inv-clean/inventory.json
$ echo $?
0
```

The Mac half, live on the founder's Mac:

```
$ bin/idp-inventory --plane mac --out /tmp/inv-mac
ok      inventory  mac  MANAGED 44  DRIFTED 0  ORPHAN 6  GHOST 0
```

The six orphans are third-party application jobs (ollama, ssh-agent, two Cisco AnyConnect,
sunshine, a ShipIt updater): loaded, and no repository holds their plist. Every estate job
(`ai.estate.*`, `com.estate.*`) and every hook in `~/.claude/settings.json` read MANAGED.

A plane that cannot be read is never a green zero. With no `steampipe` on the path the
plane is UNKNOWN, every cause is printed, and the exit code is 2:

```
$ PATH=/usr/bin:/bin bin/idp-inventory --planes github --no-drift --out /tmp/inv-blind
BLIND   inventory  github  UNKNOWN: nothing of this plane was read
BLIND   inventory  tofu is not installed; the declared side is unknown, not empty
BLIND   inventory  github: steampipe is not installed
ok      inventory  table /tmp/inv-blind/inventory.md  json /tmp/inv-blind/inventory.json
$ echo $?
2
```

A plane read in part (one kind timed out, the rest answered) prints `PARTIAL` with its counts,
never `ok`, and `--strict` refuses it: a plane the run cannot see cannot be called MANAGED.

On the runner the `estate-inventory` workflow reads all six planes and the table lands in the
run's step summary and at `oci://ghcr.io/chidionyema/idp/estate-inventory:latest`.
