# Demo: estate-state-grader

`bin/estate-state-grader` is slot 2 of the estate's local ops tier (crew#929).
It reads the estate snapshot (`STATE.md`, the markdown table that reports every
service and subsystem's state) and produces a clean, machine-readable ledger:
each row is graded GREEN / RED / NOT RUN / UNKNOWN, and the rows that need a
human are listed with their reason. No model is involved — grading is
deterministic, and a row that was not measured is reported NOT RUN, never
guessed PASS (LAW 2).

Grade the real daily snapshot:

```
$ bin/estate-state-grader
estate-state-grader: 9 GREEN, 3 RED, 31 NOT RUN ... rows in crew/STATE.md
rows needing a human (RED / NOT RUN / UNKNOWN):
  [RED    ] delivery: row reports RED/FAIL
  [RED    ] scienceplane:warehouse: row reports RED/FAIL
  [RED    ] scienceplane:forecastledger: row reports RED/FAIL
  [NOT RUN] revenue: not measured this cycle
```

The one-line roll-up tells you, at a glance and without reading fifty snapshot
rows, exactly what is down and what was never measured. The deterministic rubric
keeps a count that is not an explicit pass from being misread as green.

Feed any snapshot-shaped table, including straight from a command:

```
$ cat > /tmp/sn.md <<'EOF'
| what | state | measured by |
| api  | GREEN | 200 in 40 ms |
| db   | RED   | timeouts     |
EOF
$ bin/estate-state-grader /tmp/sn.md
```

A `RED` or `NOT RUN` row surfaces as needing a human; a real `GREEN` with a
measured probe does not. That is the whole contract: the grader reads state, it
never invents a PASS for a row that was not measured.
