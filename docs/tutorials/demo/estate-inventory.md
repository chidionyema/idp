# Demo: the estate inventory (crew#740)

What the founder sees when the grader runs on a cluster dump, then on the Mac. Real output,
command above it, run 2026-08-31 on the PR 1 branch.

```
$ bin/idp-inventory --fixture tests/fixtures/inventory-kube-dump.json --out /tmp/inv --strict
ok      inventory  kubernetes  MANAGED 4  DRIFTED 1  ORPHAN 2  GHOST 1
ok      inventory  table /tmp/inv/inventory.md  json /tmp/inv/inventory.json
FAIL    inventory  4 rows are not MANAGED (--strict)
```

The same dump with the three red rows removed, so the gate is proved both ways:

```
ok      inventory  kubernetes  MANAGED 1  DRIFTED 0  ORPHAN 0  GHOST 0
exit 0
```

The Mac half, live on the founder's Mac:

```
$ bin/idp-inventory --plane mac --out /tmp/inv-mac
ok      inventory  mac  MANAGED 44  DRIFTED 0  ORPHAN 6  GHOST 0
```

The six orphans are third-party application jobs (ollama, ssh-agent, two Cisco AnyConnect,
sunshine, a ShipIt updater): loaded, and no repository holds their plist. Every estate job
(`ai.estate.*`, `com.estate.*`) and every hook in `~/.claude/settings.json` read MANAGED.

A plane that cannot be read is never a green zero:

```
$ bin/idp-inventory --planes oci --reuse --no-drift --out ~/.estate
BLIND   inventory  oci  UNKNOWN: oci: the discovery search did not answer: BLIND   audit  no tenancy identifier: set OCI_TENANCY_OCID or run bin/idp-oci-login
```

On the runner the `estate-inventory` workflow reads all six planes and the table lands in the
run's step summary and at `oci://ghcr.io/chidionyema/idp/estate-inventory:latest`.
