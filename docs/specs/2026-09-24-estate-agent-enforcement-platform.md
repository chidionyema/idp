# Estate Agent Enforcement Platform — Consolidated Design
**Status: LIVE — 2026-09-24**

---

## The Problem

Three overlapping systems, all executing commands:
1. **Intent Layer** — 24 YAML files in `~/.estate/intents/`
2. **Helper Layer** — 10 shell/Python scripts in `~/.estate/libexec/`
3. **MCP Executor Layer** — `estate_executor.py` (13 raw tools) + `estate_simulate.py`

The MCP layer bypassed the intent layer. Agents had two ways to run commands:
execute_command (MCP) vs estate_invoke (intent). This is the root cause of hallucinations.

---

## The Rule

**One execution model. The intent is the tool.**

If an action isn't defined in a YAML intent, the agent cannot perform it.
The MCP server's only job is to wrap and expose that registry.

---

## What's Deleted

| File | Reason |
|------|--------|
| `noop.yaml` | Redundant — `halt` covers workflow termination |
| `shell.locate.yaml` | Logic merged into `shell.parse --context=N` |
| `mcp/plugins/estate_executor.py` | 13 raw tools (execute_command, propose_patch, verify, seal, admit, etc.) — all duplicate intent layer |
| `mcp/plugins/estate_simulate.py` | Redundant — equivalent to `shell.verify` + dry-run |

---

## What's Kept (Read-Only Inquiry — Not Deleted)

| Plugin | Tools | Purpose |
|--------|-------|---------|
| `estate_holmes` | ask_holmes | Estate AI investigator (Kubernetes, logs, Prometheus, Robusta findings) |
| `estate_inventory` | get_estate_inventory | What is the estate? (crew/STATE.md + Backstage catalog) |
| `estate_memory` | remember, recall | Hindsight vector store (permanent agent memory) |
| `estate_sessions` | list_sessions, get_session | Session catalog (from catalog-info.yaml) |
| `estate_state` | get_estate_state | Estate state document (from estate-db, freshness-gated) |
| `estate_twin` | estate_twin | Live state vs declared state (from estate-db) |
| `estate_guards` | get_estate_guards | Read-only policy check |

These are inquiry tools. They answer questions. They do not execute commands. They are not duplicated by the intent system.

---

## The 24-Intent Registry

### Group A: Read (Safe, zero side-effects)

| Intent | Description | Args |
|--------|-------------|------|
| `k8s-get` | Read-only kubectl get | kind, name, namespace, selector, output |
| `k8s-describe` | kubectl describe | kind, name, namespace |
| `spire-agent-logs` | SPIRE agent logs by node | node, lines, since |
| `spire-csi-check` | CSI driver + pod inspection | node |
| `spire-entries-list` | ClusterSPIFFEID entries | — |
| `spire-proof-run` | SPIRE SVID one-shot pod | namespace, timeout |
| `litellm-status` | Litellm deploy + ExternalSecret + pod events | component |
| `vault-ocid-get` | Vault OCID from ConfigMap | — |
| `ci.errors` | All failing CI jobs/steps/errors | repo, run, pr |
| `ledger-verify` | Router reachability | — |
| `router-status` | Router up/down + model catalog | — |
| `cost-today` | Router spend query | — |

### Group B: Code Surgery (Bounded, sandboxed)

| Intent | Description | Args |
|--------|-------------|------|
| `shell.parse` | shellcheck -f json → structured errors | file |
| `shell.suggest` | Unified diff to stdout, never writes | file, line, fixed_file |
| `shell.verify` | Sandbox apply + bash -n + shellcheck | file, patch |

### Group C: Write (Gated, branch/dry-run only)

| Intent | Description | Args |
|--------|-------------|------|
| `git.branch` | New branch from HEAD, never main | name |
| `git.commit` | Apply patch + commit, never main | file, patch, message |
| `oci-kubeconfig-refresh` | Refresh OKE kubeconfig token | — |
| `flux-reconcile` | flux reconcile | kind, name, namespace |
| `flux-suspend` | flux suspend | kind, name, namespace |
| `build-image` | CI image pipeline trigger | — |
| `ci.run` | Push + gh run watch | branch |

### Group D: Interactive

| Intent | Description | Args |
|--------|-------------|------|
| `explore` | Freeform exploration, needs model | — |

### Group E: Meta

| Intent | Description | Args |
|--------|-------------|------|
| `halt` | Print state and exit | — |

---

## Target Architecture

```
~/.estate/
├── bin/
│   └── estate-execute          # Python executor — tickets, ledger, SQL
├── intents/                    # 24 YAMLs — the only execution surface
│   ├── shell.parse.yaml
│   ├── git.branch.yaml
│   └── ...
├── libexec/                    # 1 helper per complex intent (10 scripts)
│   ├── shell-suggest.py
│   ├── shell-verify.py
│   ├── ci-errors.sh
│   └── ...
└── estate.db                   # tickets, audit

mcp/plugins/
├── estate_mcp.py               # 3 tools: estate_list, estate_show, estate_invoke
├── estate_holmes.py            # inquiry only
├── estate_inventory.py         # inquiry only
├── estate_memory.py            # inquiry only
├── estate_sessions.py          # inquiry only
├── estate_state.py             # inquiry only
├── estate_twin.py              # inquiry only
└── estate_guards.py           # inquiry only
```

---

## MCP: 3 Tools Only

```python
estate_list(intent_kind="shell")  # filter by group, or list all
estate_show(intent="shell.parse") # full args, description, steps
estate_invoke(intent="shell.parse", args={"file": "bin/idp-ci"})
```

---

## How the Agent Works

1. Agent calls `estate_list` → sees available intents
2. Agent calls `estate_show shell.parse` → sees args and description
3. Agent calls `estate_invoke shell.parse file=bin/idp-ci` → gets JSON errors
4. Agent calls `estate_show shell.suggest` → sees how to propose a fix
5. Agent writes the fixed line to `/tmp/fixed.txt`, calls `estate_invoke shell.suggest file=bin/idp-ci line=550 fixed_file=/tmp/fixed.txt > /tmp/patch.diff`
6. Agent calls `estate_invoke shell.verify file=bin/idp-ci patch=/tmp/patch.diff` → ALL PASS
7. Agent calls `estate_invoke git.branch name=fix/sc2086-550`
8. Agent calls `estate_invoke git.commit file=bin/idp-ci patch=/tmp/patch.diff message="fix: quote XD"`
9. Agent calls `estate_invoke ci.run branch=fix/sc2086-550` → green → PR ready

**The agent never runs arbitrary bash. It never calls `execute_command`. It never modifies a source file directly.**
