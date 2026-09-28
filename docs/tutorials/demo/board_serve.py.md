# Demo: the founder's board renders a deliverable at 127.0.0.1:8787 /look

OBS-02 (idp#3525 CP8, spec section 6): "Founder-facing deliverables SHALL render on the local
board (127.0.0.1:8787 /look) or a permanent collector page, or be pushed directly as a file."
`bin/board_serve.py` is that board — a stdlib-only `http.server` (LAW 43) that reads a small
local directory of report pairs and renders them.

## Run it

```bash
cd ~/dev/code/idp
export BOARD_DIR=/tmp/board-demo
python3 - <<'PY'
import sys
sys.path.insert(0, "bin")
import board_serve as bs
bs.publish(
    {"id": "cp8-demo", "title": "CP8 evidence draft", "generated_at": "2026-09-15T18:00:00Z",
     "source": "manual demo run"},
    "OBS-01 catalog entities landed; GOV-01 routing-path scan is clean.\n",
)
PY
python3 bin/board_serve.py
```

Then, from another terminal:

```bash
curl -s http://127.0.0.1:8787/look
```

## What you see

The page lists every deliverable currently on the board, newest first — its title, when it was
generated, its source, and the body text `publish()` wrote — with no external request in the
trace. An empty board says "No deliverables on the board yet" rather than rendering a blank page
that would read as green with nothing on it.

## Why this is the point

The estate already writes founder reports for the portal's Reports page
(`bin/idp-reports-render`, crew#684) as one `<id>.md` + `<id>.meta.json` pair. `board_serve.py`
reads that same pair locally, so a deliverable produced anywhere in the estate has one shape and
two places it can land — the portal, or the founder's own machine — never a third, bespoke
format invented just for CP8.
