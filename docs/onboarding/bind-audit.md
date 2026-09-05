# Onboarding: bind-audit

## What it is

`bin/bind-audit` reads back what is actually listening on this machine — every
process bound to an address other than loopback — and fails on anything not in
its allow-list. Plain `bind-audit` reads `lsof` and audits this machine now.
`bind-audit --table FILE` audits a saved `lsof` table instead, so CI can run
the same check on a Linux runner that has none of this laptop's real
listeners. `bind-audit --selftest` runs a synthetic table that must produce
one refusal and one permit, proving the check both ways.

## Why it exists

A Kubernetes cluster config missing one YAML key made k3d publish its API
server on `0.0.0.0` at a kernel-picked port. The config was reviewed, merged
and CI-green, and it stayed reachable from every interface for 40 minutes
because nothing ever read back what actually ended up listening — the config
was trusted to describe reality instead of being checked against it. This
script is that read-back. Founder ruling R20: the gateway is the only process
allowed a non-loopback bind; everything else stays on `127.0.0.1` or off the
network entirely.

## When it runs

By hand, or as part of a wider check that wants proof the machine matches R20.
Its allow-list is a fixed table of `COMMAND-prefix | port | reason` rows inside
the script itself — macOS system processes (`rapportd`, `ControlCenter`),
colima's DNS resolver, and the two ports the gateway itself publishes. Adding a
new process that legitimately needs a non-loopback bind means adding a row
here with the reason, not silencing the finding.

## Related files

```
bin/bind-audit                the check
docs/demo/bind-audit.md       the selftest run
```

osquery was considered and rejected as the enumeration tool: it is not
installed on this machine, needs a resident daemon on hardware the founder has
already called too slow to work on, and it supplies no policy of its own — the
allow-list still has to be written by hand either way.
