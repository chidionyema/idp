# Publish Agent Foundry trainer Space

What this template does is documented in `template.yaml`.

## Operator setup (one-time)

The runner pod lives in `platform/agent-foundry/runner/` on the `agent-foundry`
namespace. Two values live in the estate vault (Bitwarden / human-vault) and ESO
syncs them into the cluster within 1\u20135 minutes. **No GitHub Web UI clicks. No
developer-laptop secrets.**

In Bitwarden Secrets Manager, add:

| Item name                       | Value                       |
|---------------------------------|-----------------------------|
| `AGENT_FOUNDRY_HF_WRITE_TOKEN`  | `hf_xxxxxxxxxxxxxxxxxxxx`   |
| `AGENT_FOUNDRY_RUNNER_PAT`      | `ghp_xxxxxxxxxxxxxxxxxxxx`  |

(Optionally `AGENT_FOUNDRY_DATABASE_URL` if you want audit rows to land in the
estate Postgres `task_executions` table; otherwise leave the deploy script's
JSONL audit sink at `/tmp/af-audit/`.)

Flux applies the `platform/agent-foundry/runner/` Kustomization. The runner pod
comes up, registers with GitHub using the PAT, and starts polling for jobs.

## From the portal

Open the **Publish Agent Foundry trainer to HF Space** tile, fill in the form,
hit **Create**. The workflow run appears at:
<https://github.com/chidionyema/agent-foundry/actions/workflows/agent-foundry-space-deploy.yml>

The Space URL prints in the workflow summary.
