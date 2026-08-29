# Demo: the estate zone is one value

Run the gate on the repository, then on the fixture where a route spells the zone out by hand.

```
$ bin/estate-zone-gate
ok    zone     0 literal zone name(s) outside clusters/*/estate-config.yaml; zone(s): mumchimp.com
$ ESTATE_ZONE_ROOT=tests/fixtures/estate-zone/bad bin/estate-zone-gate
platform/edge/route.yaml:8: - catalogue.mumchimp.com
FAIL    zone     1 literal zone name(s) outside clusters/*/estate-config.yaml; zone(s): mumchimp.com
$ ESTATE_ZONE_ROOT=/tmp/empty bin/estate-zone-gate
BLIND: no clusters/*/estate-config.yaml declares ESTATE_ZONE
```

The first run is `platform/` today: every hostname the platform publishes is written as `<service>.${ESTATE_ZONE}` and Flux fills in the value from the ConfigMap `estate-config` in the cluster row. The second run shows the gate refusing a route that names the zone directly, with the file and line. The third shows what happens when no cluster declares a zone: the gate says BLIND rather than passing, so a missing config can never read as clean. The same gate runs inside `bin/idp-ci` on every pull request.
