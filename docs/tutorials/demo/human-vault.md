# Human secret door

The estate has two doors for secrets. The machine door is the cloud vault: code mints a value
and code stores it, no person involved. The human door is this one: a value that is born in a
person's hands — a bot token from BotFather, an API key read off a vendor page — goes into
Bitwarden Secrets Manager from a phone browser, and the cluster pulls it in on its own. No
terminal, no file on disk, no chat message ever carries the value (decision 0017).

## Watch it work

The store and its bridge, from any machine with cluster access:

```
kubectl get clustersecretstore human-vault
kubectl -n external-secrets get deploy bitwarden-sdk-server
kubectl -n external-secrets get externalsecret bitwarden-access-token
```

A ready store shows `STATUS: Valid`. Then store any secret from a phone: open the Bitwarden web
vault in the phone's browser, add a secret to the estate's project, and reference it from an
`ExternalSecret` with `secretStoreRef.name: human-vault`. Within the refresh interval the value
is a Kubernetes Secret; the paste-into-a-terminal path it replaces no longer exists.

## What holds it up

Until the founder has created the Bitwarden organisation and seeded the machine token
(docs/how-to/bitwarden-human-vault.md), the `human-vault` Flux row is red on its own and holds
nothing else — that isolation is deliberate: the estate's sync rows are built so one broken
row never holds another.
