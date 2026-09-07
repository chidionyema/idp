# agent-foundry self-hosted runner (ESO-mounted HF token)

This is the platform side of the **Backstage \u00a7-publish Space** flow. Backstage stays
stateless; the runner pod holds nothing except the secret ESO just mounted. There is
no GitHub Secrets UI step anywhere.

## Operator one-time setup (zero UI clicks)

In Bitwarden Secrets Manager (the `human-vault` ESO store):

| Item name                       | Value                           | Notes                                     |
|---------------------------------|---------------------------------|-------------------------------------------|
| `AGENT_FOUNDRY_HF_WRITE_TOKEN`  | `hf_xxxxxxxxxxxxxxxxx`          | HF Write token (Hub Settings -> Tokens)   |
| `AGENT_FOUNDRY_RUNNER_PAT`      | `ghp_xxxxxxxxxxxxxxxxx`         | PAT scoped to the `agent-foundry` repo    |

Both sync into the cluster within 1\u20135 minutes (ESO `refreshInterval`). No portal
action, no `kubectl create secret`, no value typed into git (LAW 46).

## What ends up in the cluster

- Namespace `agent-foundry` (Flux prune disabled, PSS restricted).
- Secret `agent-foundry-hf-token` (key `hf_write_token`) sourced from Bitwarden.
- Secret `agent-foundry-runner-pat` (key `github_pat`) sourced from Bitwarden.
- Deployment `agent-foundry-runner`: one pod, self-hosted GitHub Actions runner with
  labels `self-hosted, agent-foundry`. Its `_work` volume is `emptyDir` (nothing
  survives a restart). The HF token is mounted read-only at `/etc/agent-foundry/hf_token`,
  mode `0400`, and `HF_TOKEN_FILE` env points at it. The deploy script reads it from
  the file path; it never appears as an env value.

## From Backstage

The **Publish Agent Foundry trainer to HF Space** tile dispatches
`agent-foundry-space-deploy.yml` on the `agent-foundry` repo. The workflow's
`runs-on: [self-hosted, agent-foundry]` lands on this pod. The HF token is already
on disk; the workflow's `env:` block does not need to mention it.

## Upgrade path (Bridge to ARC)

Today the runner registers with a long-lived PAT. Production-grade uplift:

1. Create a GitHub App with `actions: read` + `administration: write` on the
   `agent-foundry` repo.
2. Drop the App's private key + id into Bitwarden under names `AGENT_FOUNDRY_GH_APP_KEY`
   / `AGENT_FOUNDRY_GH_APP_ID`.
3. Switch the runner to `summerwind/actions-runner-controller` (ARC) so each pod mints
   an ephemeral registration token at startup. The PAT, the human paste step, and the
   `_work` emptyDir all go away.

Tracked as a follow-up; not blocking this milestone.

## Audit

Every deploy is a row in either:
- the estate Postgres `task_executions` table (`$AF_DATABASE_URL` ESO-synced secret),
- or a JSONL sink (`$AF_DEPLOY_AUDIT_DIR` mounted via a `ConfigMap`).

The script refuses dark if neither is configured at workflow runtime (LAW 50).
