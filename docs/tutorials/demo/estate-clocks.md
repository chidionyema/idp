# The estate-clocks demo

The founder asked for one page naming every clock in the estate, after scheduled jobs ended up
scattered across the cluster, this machine and GitHub with no single place listing them. The
[scheduler move](https://github.com/chidionyema/crew/issues/716) made that page generated, so it
cannot drift from the sources it reads.

## The command

    cd ~/dev/code/idp && bin/estate-clocks

## What it printed (2026-09-01)

```
Wrote <checkout>/docs/scheduling/CLOCKS.md
```

## What the page holds

`docs/scheduling/CLOCKS.md` lists every clock as one row: its name, where it runs, its cron line,
the source file that defines it, and what it does in plain words. A description that starts with a
path is wrapped in backticks so the plain-words check reads it as code, not prose.

## Why it stays true

Running the command twice writes the same bytes, and `tests/test_clocks_table_matches_sources.py`
renders the table from the sources and fails when the file on disk differs — so a clock cannot be
added, moved or reworded without the page following in the same change.
