# Siri Shortcuts on the kernel API (R14, master spec 2.6)

Siri Shortcuts is the mature tool: Apple ships it, it already does HTTP
and text-to-speech, and it runs on the phone and the watch. Nothing here
is a server. Each shortcut is three built-in actions against a cockpit
route that already exists, and `estate-status.json` is the machine-readable
record of that binding (the BDD test reads it and hits the same route).

## "Hey Siri, estate status"

1. Get Contents of URL: `<cockpit base url>/api/status`, method GET.
   The base URL is `ESTATE_PUBLIC_URL` (the cloudflared tunnel, see
   `bin/sb tunnel`) or `http://localhost:<cockpit.port>` on the Mac.
2. Get Dictionary Value: key `spoken`.
3. Speak Text.

The sentence is composed by `sovereign/presence/status.py` from the
`presence.speak_template` config key, so the shortcut holds no words of
its own. On the Mac, `bin/sb presence status` prints the same sentence.

## What is not here

"Authorize branch alpha" (spec 2.6) is a signed act and goes through
`bin/sb approve --sign`, which needs Touch ID on the Mac. It is not bound
to a shortcut in this workstream because no shortcut can present the
Secure Enclave, and a voice authorization that skipped it would be the
half-stitched path the spec forbids.
