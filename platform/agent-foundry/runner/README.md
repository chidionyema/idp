# agent-foundry self-hosted runner (ESO-mounted secrets from OCI Vault)

Backstage stays stateless. The runner pod holds nothing except the secrets ESO just
mounted, and only for the lifetime of the pod. No Bitwarden Web UI. No GitHub Web UI.
No developer laptop. No value typed into git (LAW 46, R52).

## Operator one-time setup (one CLI call)

The estate already runs `bin/idp-vault-put` (it backs `bin/idp-jit-grants`,
`bin/idp-pr-secrets`, and the LiteLLM model-key rotation path). For platform-owned
secrets like the runner's two credentials, the same CLI writes the entry to the
estate's OCI Vault under one JSON entry (`agent_foundry_runner`) holding two keys
(`hf_write_token`, `github_pat`). ESO syncs the entry into the cluster within 1
minute; nothing else is needed.

```bash
echo "HF_TOKEN=hf_xxxxxxxxxxxxxxxxxxxxxxxx"        >> ~/.estate/.env
echo "RUNNER_PAT=ghp_xxxxxxxxxxxxxxxxxxxxxxxx"     >> ~/.estate/.env
bin/idp-vault-put agent_foundry_runner \
    hf_write_token=HF_TOKEN github_pat=RUNNER_PAT
```

The CLI prints `vault   agent_foundry_runner ...` and exits 0. No value is printed.

To rotate a single key without disturbing the other, run `bin/idp-vault-put --merge`
with the new value in the env file. CLI is merge-safe (R52).

## What ends up in the cluster

- Namespace `agent-foundry` (Flux prune disabled, PSS restricted).
- Secret `agent-foundry-runner` (keys `hf_write_token`, `github_pat`) sourced from OCI
  Vault via the `estate-vault` ClusterSecretStore (the same one `platform/commerce/`
  and `platform/notify/` use).
- Deployment `agent-foundry-runner`: one pod, self-hosted GitHub Actions runner with
  labels `self-hosted, agent-foundry`. Its `_work` volume is `emptyDir` (nothing
  survives a restart). The secret is mounted read-only at `/etc/agent-foundry/`,
  mode `0400` per file; `HF_TOKEN_FILE` env points at the token file. The deploy
  script reads it from the file path; it never appears as an env value.

## From Backstage

The **Publish Agent Foundry trainer to HF Space** tile dispatches
`agent-foundry-space-deploy.yml` on the `agent-foundry` repo. The workflow's
`runs-on: [self-hosted, agent-foundry]` lands on this pod. The HF token is already
on disk; the workflow's `env:` block does not need to mention it.

## Audit

Every deploy is a row in either:
- the estate Postgres `task_executions` table (`$AF_DATABASE_URL`, also sourced from
  OCI Vault via the same `estate-vault` store -- extend the runner deployment's
  projected volume with one more file when this is wired up),
- or a JSONL sink (`$AF_DEPLOY_AUDIT_DIR` mounted via a `ConfigMap`).

The script refuses dark if neither is configured at workflow runtime (LAW 50).

## Upgrade path (Bridge to ARC)

Today the runner registers with a long-lived PAT. Production-grade uplift:

1. Create a GitHub App with `actions: read` + `administration: write` on the
   `agent-foundry` repo.
2. Drop the App's private key + id into OCI Vault under names
   `agent_foundry_gh_app_key` / `agent_foundry_gh_app_id`.
3. Switch the runner to `summerwind/actions-runner-controller` (ARC) so each pod
   mints an ephemeral registration token at startup. The PAT, the human paste
   step, and the `_work` emptyDir all go away.

Tracked as a follow-up; not blocking this milestone.
