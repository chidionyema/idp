# Demo: Open a layer's logs and traces from its catalogue page

Open the portal, go to the catalogue, and open any platform layer — Hermes is a good one.
On its overview card you now see links: **Live logs and metrics** opens the estate's log
store, and on layers that send model traces (Hermes, the model gateway) **Model traces**
opens the tracing service. One tap from "what is this thing" to "what is it doing right now."

Nothing on these links was typed by hand. The generator reads the observability layer's own
route manifests to learn the two hostnames, and it grants the traces link only to layers whose
manifests actually project tracing keys into their pods — so a link never points at traces
that were never sent. Regenerate with `bin/catalog-platform`; the check mode fails the build
when the committed file drifts from what the cluster manifests say.
