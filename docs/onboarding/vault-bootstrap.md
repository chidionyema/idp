# Connecting the estate to Bitwarden Secrets Manager

One person does three small things once. Everything else is the machine's job.

## What you do

1. In the Bitwarden web vault (the European site if your account lives there), open
   **Billing → Subscription** and tick **Subscribe to Secrets Manager**. The tier in use is free.
2. Open **Secrets Manager → Machine accounts**, create a machine account named `estate`,
   then on its **Access tokens** tab choose **Create access token**. The token is shown once
   and cannot be retrieved later.
3. Hand the token to the machine: put it in a file only your user can read
   (`umask 077` first), run `bin/idp-cloud secret put bitwarden-machine --file <that file>`,
   and delete the file in the same breath. The token never appears in chat, in a command
   line, or in anything that persists. The write targets the vault by identifier from the
   platform's own state, so there is no console form — and no vault picker — to get wrong.

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
