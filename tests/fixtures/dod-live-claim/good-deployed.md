# Widget backend — actually deployed, for the gate's own fixtures

**Status:** built, smoke-tested, and doored, 2026-09-15. The BDD suite runs green against a real
daemon on a laptop.
**Opened:** 2026-09-15
**Door (from the UI):** `/ops`, "Widget" tile.

## What shipped

The widget backend (`platform/widget-good/`) mounts the widget routes and is proven against a
real daemon, and carries a Dockerfile plus a `kind: Deployment` manifest under `clusters/`
(graded here against a self-contained fixture root, not the real estate).
