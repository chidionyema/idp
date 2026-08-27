# Demo: the trace matrix

    bin/trace-matrix --check

Prints one line: `FAIL  trace-matrix  113 features, 65 unbound (192 scenarios nothing runs)` and
writes `docs/TRACE-MATRIX.md`, requirement -> scenario -> test, unbound rows first, each row with
the PR and ticket that added it. Nothing on the page is typed; delete it and the next render
brings it back. The scheduled `catalog-render` renders it onto `state/live-diagram` beside
`docs/SHOWCASE.md`.
