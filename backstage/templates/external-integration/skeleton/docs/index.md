# ${{ values.name }}

An external integration with **${{ values.provider }}**, running in namespace
`${{ values.namespace }}`.

## How this integration authenticates

${{ values.authMode }}.

That sentence is rendered from the provider you picked and is not editable prose. The estate
allows exactly three authentication shapes, and every integration is one of them:

1. **Workload identity federation (OIDC).** The workload presents its own Kubernetes
   ServiceAccount token or the GitHub Actions OIDC token, and the provider exchanges it for a
   short-lived session. Nothing long-lived exists to be handled. This is the OCI path the
   estate already runs.
2. **A one-tap install or login.** Where the provider has no federation, the credential is
   minted by the provider itself against the founder's SSO identity: a GitHub App
   installation, or an interactive login where the workload prints a URL and the tap happens
   on a phone. The line in the docs is the LAW 47 register shape --
   `FOUNDER ACTION:` followed by a URL or a single word -- and the tap is the whole of it.
3. **A CI-seeded vault entry.** Where a provider offers neither, the value is set once as a
   repository secret and travels `vault-seed.yml` -> vault -> ExternalSecret. It reaches the
   cluster without ever appearing in a terminal, a document or a chat message.

What is never allowed, and what `policy/no-manual-steps.rego` refuses at the pull request:
a value a person carries from one browser tab to another.

## Where the credential lives

- Vault entry: `${{ values.name }}`, written by `.github/workflows/vault-seed.yml`
  (`vault-seed-entry.yaml` beside this page is its stanza).
- Kubernetes: `external-secret.yaml` beside this page reads that entry through the estate's
  one `ClusterSecretStore` and creates the Secret `${{ values.name }}` in
  `${{ values.namespace }}`.
- Rotation: change the repository secret and re-run the workflow. The refreshInterval is one
  hour, so the cluster picks it up without a redeploy.

## Proving it

- `bin/idp-no-toil --files docs/index.md` -- the no-toil gate over this page.
- `kubectl -n ${{ values.namespace }} get externalsecret ${{ values.name }}` -- the status
  condition reads `SecretSynced` once the entry exists.
