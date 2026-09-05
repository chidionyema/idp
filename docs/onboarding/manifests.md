# Manifest-first execution: how an agent starts anything on this host

`bin/idp-apply MANIFEST` is crew#186 CP5 (R22 mechanism 5). An agent writes a
manifest into `catalog/manifests/<name>.yaml`; the runner validates, sandboxes,
health-checks and only then applies. Nothing else is a sanctioned way to start
a container, and `bin/idp-reconcile` removes what arrives any other way.

```yaml
action: up                      # or down
name: cp5-caddy                 # equals the file name
image: caddy:2.10-alpine        # pinned; :latest is refused by the schema
ports: [{host: 38080, container: 80}]   # host port must be declared for this
                                        # service in catalog/ports.yaml; always 127.0.0.1
health: {url: "http://127.0.0.1:38080/", timeout_s: 30}   # required
limits: {memory: 128m, cpus: 0.5}
caps: [NET_BIND_SERVICE]        # the only capabilities that may be added back
migration: ./migrate            # optional; must pass bin/migration-gate first
```

| Step | Refuses when | Mature tool |
|---|---|---|
| validate | schema fails: no health, `:latest`, non-loopback bind, unknown field | check-jsonschema, `catalog/manifests/schema.json` |
| ports | host port not declared for this service | `catalog/ports.yaml`, same source as `bin/port-gate` |
| migration | `bin/migration-gate` red | R19 verbs |
| sandbox | docker run fails | `--cap-drop ALL --security-opt no-new-privileges --pids-limit 256 --memory --cpus`, label `idp.manifest=<name>` |
| health | URL never answers in `timeout_s` | container removed, exit 1 |

Every step writes a row to `run/apply.jsonl`. `--dry-run` stops before docker.

Proof, 2026-08-24: `cp5-caddy` first failed health because caddy cannot bind
port 80 with every capability dropped (the container was removed, exit 1);
with `caps: [NET_BIND_SERVICE]` it answered 200, `docker inspect` showed
`CapDrop=[ALL] CapAdd=[CAP_NET_BIND_SERVICE] PidsLimit=256`, and the next
`idp-reconcile --fix` removed it because no `catalog/manifests/cp5-caddy.yaml`
exists. `bin/idp-ci` row `manifest` proves the refusals on every run.

Residual: `docker volume rm` and global `pip install` typed by hand are not
stopped by this runner; that guard lives in the agent hooks (claude-guards),
not in idp.
