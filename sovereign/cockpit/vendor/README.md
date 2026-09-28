# Vendored assets

Vendored, not CDN-loaded (CP4, master spec §2.1): the cockpit must render
Spatial with no network dependency beyond the estate's own server.

| File | Library | Version | License | Source |
|---|---|---|---|---|
| `cytoscape.min.js` | [cytoscape.js](https://js.cytoscape.org/) | 3.34.2 | MIT (`LICENSE` in this directory) | `https://unpkg.com/cytoscape@3.34.2/dist/cytoscape.min.js` |

Cytoscape.js was chosen over hand-rolling a force-directed layout (LAW 43):
its core ships the `cose` force-directed layout, hover/tap events and
right-click (`cxttap`) out of the box, so the Spatial view (spec §2.1: nodes
= sessions, colour = health, size = burn, edges = capability invocations,
hover = Merkle root/budget/heartbeat, right-click = halt) needs no
additional plugin. d3-force was the alternative considered and rejected for
this checkpoint: it supplies only the simulation, not the picking, hover and
context-menu interaction the spec's hover/right-click requirements need, so
choosing it would mean hand-rolling exactly the event layer LAW 43 forbids
reinventing.

To update: fetch a newer pinned version from unpkg (never `latest`), replace
`cytoscape.min.js`, update this table's version, refresh `LICENSE` from
<https://github.com/cytoscape/cytoscape.js/blob/master/LICENSE>, and record the
change in the PR body's `## Options considered`.
