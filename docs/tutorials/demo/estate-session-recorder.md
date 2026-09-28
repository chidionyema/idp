# Demo: estate-session-recorder

`bin/estate-session-recorder` is the knowledge-base backstop (R30) of the
estate's local ops tier (crew#929, slot 5). Given the claimed-work block at the
tail of a session, it emits the durable INVENTORY capsule — Built / Verified /
Not-proven — but it KEEPS only the claims that carry command-run proof and
reports the rest as not-proven. No model is involved: the grading is
deterministic, so a session can never claim "green" on a claim with no probe
(LAW 2).

Give it the capsule lines a session would normally write by hand:

```
$ cat > /tmp/session-end.md <<'EOF'
- **Built:** bin/estate-digest-keeper
- **Verified:** bin/estate-digest-keeper answered ALIVE
- **Evidence:** https://github.com/chidionyema/idp/pull/2749
- **Built:** bin/thing-that-never-landed
EOF
$ ESTATE_SESSION_REPO=/path/to/idp bin/estate-session-recorder /tmp/session-end.md
BUILT: bin/estate-digest-keeper
VERIFIED: bin/estate-digest-keeper answered ALIVE; https://github.com/chidionyema/idp/pull/2749
NOT-PROVEN:built: bin/thing-that-never-landed
```

The real file on disk and the real URL are kept; the fabricated path is dropped
and called out as not-proven, so nobody downstream treats a claim as shipped
when the file is not there. It also reads the block from stdin:

```
$ some-command-that-emits-capsule-lines | bin/estate-session-recorder
```

Point `ESTATE_SESSION_REPO` at whichever checkout the session's claims name —
the idp repo by default, or a product repo whose sessions you are recording.
