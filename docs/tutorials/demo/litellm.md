# Demo: litellm-up / litellm-down / litellm-status

`bin/litellm-status` shows whether the proxy is answering, what models it
serves, and container memory. Run against this estate's running proxy:

```
$ bin/litellm-status
PROXY      LOCAL                          HTTP   BASE URL FOR EVERY AGENT
litellm    127.0.0.1:4000                 200    http://127.0.0.1:4000/v1

MODELS IT SERVES
  proxy is not answering -- bin/litellm-up

CONTAINERS
litellm-db                        43.69MiB / 256MiB       0.00%
litellm-proxy                     755.8MiB / 2GiB         0.28%
  ---
  ceilings: litellm 512m + litellm-db 256m = 768m

WHAT STILL DOES NOT GO THROUGH THIS PROXY, ON PURPOSE
  claude_cli   local CLI on a subscription, not an API key -- prospector/claude_cli.py
  gemini_cli   same -- prospector/gemini_cli.py
```

The "MODELS IT SERVES" line above reads `proxy is not answering` even with
HTTP `200`, because printing the model list also needs a readable `llm/.env`
in the checkout the command runs from — `llm/.env` is gitignored and
per-checkout, and this run was from a fresh worktree that has never run
`bin/litellm-up` and so has no `.env` of its own, even though the shared
Docker containers are up. `HTTP` itself reads `down` when the proxy is not
answering, and the command exits non-zero only in that case — a running container that refuses its config is
the exact failure this is built to catch, which is why the check is `curl
.../health/liveliness` and not `docker ps | grep litellm`.

`bin/litellm-up` follows the same shape as `bin/langfuse-up`: it validates
`llm/config.yaml` as YAML before starting anything, pulls every upstream
provider key out of the age vault into `llm/.env` at mode 600 (never printed,
gitignored), and generates the proxy's own three secrets once — never again,
because rotating `LITELLM_SALT_KEY` after virtual keys exist makes them
unreadable. `bin/litellm-down` stops the containers and keeps the spend
ledger and virtual keys; `--wipe` deletes them, which cannot be undone.
