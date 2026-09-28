# How to put a deliverable on the founder's board

`bin/board_serve.py` serves one page, `/look`, over loopback only (`127.0.0.1:8787`) — a
founder-only local tool, never a routing-path dependency (GOV-01 draws that line deliberately:
this board is allowed to run on the laptop precisely because nothing else depends on it being
up). It takes no configuration and needs no model.

## Publish a deliverable

```python
import sys
sys.path.insert(0, "bin")
import board_serve

board_serve.publish(
    {"id": "my-report", "title": "My Report", "generated_at": "2026-09-15T00:00:00Z",
     "source": "where this came from"},
    "the body text of the deliverable\n",
)
```

This writes `my-report.md` and `my-report.meta.json` into `BOARD_DIR` (default
`~/.estate/state/board`, overridable by the `BOARD_DIR` environment variable) — the same pair
`bin/idp-reports-render` already writes for the portal's Reports page.

## Serve the board

```bash
python3 bin/board_serve.py
```

Binds `127.0.0.1:8787` and serves `GET /look` (the rendered page) and `GET /healthz` (`ok`).
Everything else is a 404.

## External hosts require a reason on record

`publish()` refuses to write anything if the deliverable's title, body or metadata names an
external host (anything that is not `127.0.0.1`, `localhost`, or resolves inside the estate's own
`.svc.cluster.local` / `.internal` zones) unless the metadata carries a
`vendor-surface-intended` key naming the reason:

```python
board_serve.publish(
    {"id": "vendor-copy", "vendor-surface-intended": "founder asked for a copy on the vendor's own status page"},
    "see https://example.com/status\n",
)
```

Leave the key out and the same call raises `board_serve.ExternalPublishError` before anything is
written — the guard runs first, not after the fact.
