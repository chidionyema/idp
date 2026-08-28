# Otto, on your Mac

Otto is the one agent that acts for you from anywhere. Message it on Telegram; it answers with
what it did and a link. Since crew#516 CP5, it can also reach your Mac directly — your files, your
tools — over your own private network (Tailscale), with no key it holds and no browser step it
asks of you beyond the one below.

## Turn it on

1. Fill in your Mac's tailnet name and login user in the estate config, and run
   `tailscale up --ssh --advertise-tags=tag:founder-mac` on the Mac once
   (`docs/founder/mac-remote-desk/README.md` — the same one-sitting checklist covers this).
2. Set two GitHub repository secrets from a Tailscale OAuth client scoped `auth_keys` and
   `policy_file`, tag `tag:k8s`, then dispatch the vault-seed workflow — the same one step every
   other integration in this estate uses (`platform/hermes-agent/README.md`).

That's it. Everything else — the sidecar joining the tailnet, the network policy, Otto's own
identity — is CI, not you.

## What you'll see

- Message Otto on Telegram: it acknowledges in seconds, then replies with what ran on the Mac and
  a link to the result.
- If the Mac is asleep or off the network, Otto says so in one sentence — never a stack trace,
  never silence.
- The Otto entity in the portal (Backstage) shows the pod's status, its Telegram link, its trace
  link, and the tracked item — complete on first load.

## If something's off

Ask Otto — it has read access to its own state and will tell you what it sees. The next line up
is the `#516` item on the crew board.
