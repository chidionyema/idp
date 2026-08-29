# Demo: bind-audit

`bin/bind-audit` lists every process on this machine bound to a non-loopback
address and fails if one is not on the allow-list in the script. It exists
because a Kubernetes cluster once published its API server on `0.0.0.0` at a
random port for 40 minutes, config-reviewed and CI-green, and nothing on the
machine noticed. Founder ruling R20: the gateway is the only process allowed a
non-loopback bind. Everything else is `127.0.0.1` or nothing.

The built-in selftest proves the check both ways without touching this
machine's real listeners:

```
$ bin/bind-audit --selftest
== selftest: the check must REFUSE an unknown bind ==
OK       rapportd     *:49248                macOS Continuity/Handoff. ...
UNKNOWN  k3d-proxy    *:53145                not on the allow-list. Bind it to 127.0.0.1, or add a row to bin/bind-audit saying why it may face the network.
refused 1 of 2 rows, as required

== selftest: the check must PERMIT a known bind ==
OK       rapportd     *:49248                macOS Continuity/Handoff. ...
permitted 1 of 1 rows, as required

SELFTEST PASS -- the check refuses and permits
```

Run without arguments, it audits this machine right now with `lsof` and exits 1
on the first unknown listener. `bin/bind-audit --table FILE` grades a saved
`lsof` table instead, which is how CI runs it on a Linux runner that has none
of this laptop's processes. If `lsof` cannot be read at all, the check prints
`BLIND` and exits 2 rather than reporting a false pass.
