# LATEST

## RESUME HERE — cyrus delivery door, 2026-09-06 13:45 GMT+1

Founder ask: ", ensure cyruus is working properly lso"
(`~/.claude/docs/founder/2026-09-06T0248Z-deepseek-agent-appeas-stucj-a9476b49.md`)
and the Live Proof Protocol in
`~/.claude/docs/founder/2026-09-06T0310Z-to-ensure-pr-1954-fully-resolves-these-failure-79fbe16e.md`.

Cyrus is UP: `cyrus-78fbc48cc8-hmq9v 1/1 Running`, 0 restarts, 4h44m, image
main-5324-778422de, "📦 Managing 3 repositories". Eight walls found and merged:
#1949, #1954, #1957, #1967, #1971, #1979.

Live proof passed: all three checkouts clean (`## main...origin/main`),
`/var/lib/cyrus/.cyrus` writable with mcp-configs present, no credential in the pod
manifest (0 secret values in `kubectl describe`), unsigned POST refused on every door
(/linear-webhook 401, /github-webhook 403, /webhook 401).

Open, wall 9: the Linear transport is still in **proxy mode**. EdgeWorker.js:477 reads
`LINEAR_DIRECT_WEBHOOKS`, not CYRUS_HOST_EXTERNAL:
    const useDirectWebhooks = process.env.LINEAR_DIRECT_WEBHOOKS?.toLowerCase() === "true";
    const secret = useDirectWebhooks ? process.env.LINEAR_WEBHOOK_SECRET || ""
                                     : process.env.CYRUS_API_KEY || "";
So Linear is verified against a hosted-service bearer token that this estate does not
have, instead of the Linear HMAC. GitHub is already `signature mode`. Fix: add
`LINEAR_DIRECT_WEBHOOKS: "true"` to platform/cyrus/deployment.yaml. All four secret
files are readable in the main container (0 "not readable" lines), so the secret is there.

Also open: one pod Pending on a newer ReplicaSet (cyrus-5574899496-h448b), reason not yet
read — the cluster API was timing out at 13:40.

Then: move the Linear webhook registration (id 5c755f6e-c32e-477e-9382-be9eab8921a8) from
/webhook to /linear-webhook, and drop the deprecated alias from httproute.yaml and from
open_paths in sovereign/tests/bdd/test_gate_front_door_login.py.
