# One door for every customer's messages

Otto's first door was built for one bot talking to one person. The route matched one exact
path, the pod held one bot's token, and the code that handled a message knew it was a
Telegram message. That works until the second customer arrives, and then every part of it
has to be copied: a new path, a new token, a new pod, a new release.

This page explains the door that replaced that arrangement, and the one idea it is built on.

## Onboarding is a row, not a release

A customer arrives with a channel: a chat account, a webhook, an inbox. What the platform
needs to know is small — which customer owns that channel, and which credential that
channel will present. Both of those are data, so both live in a table called
`channel_binding`, and adding a customer means adding a row to it.

Nothing about carrying a new customer, or a channel this platform has never carried, changes
a file in this repository. That is the whole point, and everything below serves it.

## What happens when a message arrives

An event arrives at `https://otto.<zone>/webhook/<channel>` — one path, whatever the channel
is. The door reads the credential the channel presented, looks it up in the table, and finds
the row that says which customer this is. It then resolves that row's secret reference to a
secret value, checks the credential properly against it, and turns the message into a task
that carries the customer's name from that point on.

An event whose credential matches no active row gets exactly the same answer as an event
whose credential is wrong. A stranger cannot use the door to discover which customers exist.

## Where the credential is checked, and why not at the edge

The old door had its check at the edge: the route itself required a header whose value came
from the vault, so an unauthorised request never reached a pod. That is the right shape for
one channel with one credential.

This door carries every channel, and each one presents a different credential in a different
header. There is no single header value an edge rule could match without going back to one
route per channel, which is the arrangement being removed. So the check moved one hop, into
the door's first step, where it reads the table. The route says so, in the annotation
`idp.estate/auth: channel-binding-registry`, so nobody has to guess where a door is locked.

## The two doors run side by side

The old exact path keeps working while the new one is proved. Two routes on one host, on
different paths, is what makes the change back a small one: nothing is removed until the new
door has carried real traffic, and removing it is a change of its own.

## What the pods hold, and what they do not

The table holds a reference to a credential — a pointer into the vault — and a one-way
fingerprint of it. It never holds the credential. A dump of the table gives an attacker the
customer list and nothing they can use to speak as a customer.

The credential values themselves reach the pod as files the platform's secret store writes,
never as environment values, because anything that can list a process can read its
environment. The operator's own chat identifier is read the same way, from the vault entry
the platform's alerting already reads, so it appears nowhere in this repository.

## What refuses to start

The door proves everything it needs before it opens its socket: the trace collector first,
then the binding table, then the event bus. A missing piece is a refusal with one line of
plain reason and a failed start.

That order is deliberate. A door that opened first and discovered its table was missing
would answer *unauthorised* to every real customer, which reads to an operator as a
credential problem and would send them looking in the wrong place for hours.

## Where it lives

The manifests are in `platform/otto-gateway`, run by the `otto-gateway` row in
`clusters/oke/platform.yaml`. The application code is `otto/ingress` in the `hermes-v2`
repository. The control that keeps the two in step is
`tests/test_otto_gateway_manifests_are_releasable.py`.
