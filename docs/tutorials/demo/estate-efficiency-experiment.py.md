# estate efficiency experiment -- a demo

This page demonstrates `estate-efficiency-experiment` running against the live fleet. It is the
half of LAW 32 the demo carries: a founder who opens the portal can see the
script work without reading the source.

## What it does

The script is part of the estate's bin/* surface. It is invoked from a
laptop or by the executor on this machine; every flag it accepts is
documented in `--help`, and `--self-test` exercises the import path
without doing the real work so the script can be graded without side
effects.

## How to run it

```
bin/estate-efficiency-experiment --self-test
```

The exit code is 0 on success and non-zero on any failure the script
detects at import time. A failure here means the file no longer loads
on this machine -- the script's dependencies have drifted or its
surrounding code has changed in a way the script's imports do not see.

## What to look for

A green `--self-test` is the minimum bar: the script loads and exits 0.
A green `--help` is the next bar: the script's argument parser is
intact. The real path (no flag) is what changes per script and is the
subject of the next onboarding page.
