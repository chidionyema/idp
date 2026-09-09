# Demo: the board tells you which repositories it is not showing you

The estate keeps one board, in Linear, and a person is supposed to be able to look at it and see
everything the estate owes. On 2026-09-09 that was not true, and nothing said so. One repository —
`chidionyema/crew` — had been connected to Linear's GitHub Issues Sync months earlier, and no
other repository ever was. So the board showed 396 open issues and the estate had 621. The missing
225 were not hidden by a filter or a permission; they were simply never mirrored, and the board had
no way to know they existed.

This is the demo of the check that ends that. Run it and it reads both sides — what the board is
actually carrying, and what the estate actually has open — and prints the difference.

```
bin/idp-linear-mirror
```

On a healthy estate every line is `ok` and the last one says every repository with an open issue is
on the board. On the estate as it stands today it prints something closer to this:

```
ok      linear-mirror  chidionyema/crew: 396 open issue(s), mirrored
info    linear-mirror  board holds 421 active issue(s); the free plan counts 250, so headroom is -171
FAIL    linear-mirror  chidionyema/prospector: 87 open issue(s), on no Linear board
FAIL    linear-mirror  chidionyema/idp: 69 open issue(s), on no Linear board
...

FOUNDER ACTION: connect 19 repositories to Linear, team MUM, two-way.
  1. Open https://linear.app/crewestate/settings/integrations/github
  ...
```

Two things in that output are worth looking at rather than skimming.

The first is that it names the repositories in order of how many issues each one is hiding. The
instruction was "all repos should just map the same way", and that is the right rule, but a person
doing it by hand at eleven at night should do `prospector` before `sentinel-loop`.

The second is the headroom line, and it is the reason this check is more useful than a list. Linear's
free plan counts *active* issues against a ceiling of 250, and Done and Canceled both count until
something archives them. Connecting every repository at once does not produce a fuller board — it
produces a board that refuses the overflow. So the check prints the ceiling next to the gap, and when
the gap is bigger than the headroom it says so in plain words and names the fix that already exists:
`platform/linear/setup.py` turns on auto-archive at one month, and that is what frees the room.

## What it will not do

It will not connect a repository for you. Linear's GraphQL schema has `issueImportCreateGithub` and
the integration's connect and commit mutations, and no mutation that maps one repository to one
team — the mapping is a row on a settings page that Linear owns. What this refuses to allow is for
that row to be forgotten: the gap is measured on every run, and the run hands over the exact URL and
the exact rows, so the ask is a minute of clicking rather than an investigation.

It will also not report a green when it could not measure. No token, no network, or an answer it
cannot parse all produce `BLIND` and exit 2, never `ok`. A check that reads nothing and says
everything is fine is how a board stays half empty for three days while everyone believes it is full.
