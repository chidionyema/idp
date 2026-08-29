# Otto, on your Mac

Otto is the one agent that acts for you from anywhere. Message it on Telegram; it answers with
what it did and a link. Since crew#516 CP5, it can also reach your Mac directly — your files, your
tools — over your own private network (Tailscale), with no key it holds and no browser step it
asks of you beyond the one below.

## Turn it on

1. Nothing to fill in: your Mac's short username and tailnet IP are measured into
   `clusters/oke/estate-config.yaml`, and your tailnet login is read from the tailnet's owner
   record. Keep "Remote Login" on (`docs/founder/mac-remote-desk/README.md`).
2. The apply run (`oke-check`, mode apply) mints Otto's key into the vault; then one command in a
   session on the Mac, `bin/idp-mac-adopt-otto`, authorises it — no value shown, nothing pasted
   (`platform/hermes-agent/README.md`). The proof is `oke-check` break-glass playbook
   `otto-parity`: it runs `mac-run hostname` from inside the pod and prints your Mac's name.

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
