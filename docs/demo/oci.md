# Demo: Oracle identity, from nothing to a receipt

The founder signs in once in a browser. Everything else is two commands and a drill row.

```
bin/idp-oci-bootstrap      # browser opens once; creates compartment, group, user, key, vault entries
bin/idp-oci-login          # renders ~/.oci/config from the vault, proves the identity, prints A1 capacity
bin/idp-verify | grep oci  # the same proof, every run, as a drill row
```

Expected last line of `idp-oci-login`:

```
ok    oci     identity estate-tofu answers in uk-london-1; A1 cores available in <AD>: <n>
```

Before bootstrap has run the drill row reads `BLIND oci  no API key in the vault yet` and does
not fail the run. After a key is revoked in the console it reads `FAIL oci identity refused`,
which is the rotation drill: run `bin/idp-oci-bootstrap --rotate`.
