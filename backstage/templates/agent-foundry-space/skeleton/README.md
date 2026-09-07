# Publish Agent Foundry trainer Space

What this template does is documented in `template.yaml`.

## Operator setup (one-time)

1. Place your HF Write token in a file on the runner host:

   ```bash
   mkdir -p /etc/agent-foundry && umask 077 && nano /etc/agent-foundry/hf_write_token
   # paste hf_xxxxxxxxxxxxxxxxx, save
   chmod 600 /etc/agent-foundry/hf_write_token
   ```

2. Add `HF_TOKEN_FILE=/etc/agent-foundry/hf_write_token` as a repository
   Actions secret on `chidionyema/agent-foundry`.

3. Optionally, add `AF_DATABASE_URL` as a repository Actions secret pointing at
   the agent-foundry DB on the estate CNPG cluster. When set, the deploy row
   lands in the `task_executions` table; when unset, the script falls back to
   `$AF_DEPLOY_AUDIT_DIR` (set this as a workflow-level var if you want a JSONL
   sink).

## From the portal

Open the **Publish Agent Foundry trainer to HF Space** tile, fill in the form,
hit **Create**. The workflow run appears at:
<https://github.com/chidionyema/agent-foundry/actions/workflows/agent-foundry-space-deploy.yml>

The Space URL prints in the workflow summary.
