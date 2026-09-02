# Connecting the estate to Bitwarden Secrets Manager

One person does three small things once. Everything else is the machine's job.

## What you do

1. In the Bitwarden web vault (the European site if your account lives there), open
   **Billing → Subscription** and tick **Subscribe to Secrets Manager**. The tier in use is free.
2. Open **Secrets Manager → Machine accounts**, create a machine account named `estate`,
   then on its **Access tokens** tab choose **Create access token**. The token is shown once
   and cannot be retrieved later.
3. Put that token into the estate vault as an entry named `bitwarden-machine`.
   The token is never pasted into chat, a terminal, or a file.

## What the machine does

Run the bootstrap from any device:

```
gh workflow run vault-bootstrap.yml
```

The run signs into the cloud with the repository's own identity, reads the machine token from
the vault into memory, creates the `estate` project (or finds it), and opens a pull request
filling `BITWARDEN_ORG_ID` and `BITWARDEN_PROJECT_ID` in `clusters/oke/estate-config.yaml`.
Both are public names, not secrets. Merging that pull request is the last step: the cluster's
secret store then reaches Bitwarden through the machine account.

Running it twice is safe: an existing project is reused, and an unchanged configuration opens
nothing.
