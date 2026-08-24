# Onboarding — the MCP gateway

## What it is for

Agents need tools: read the estate inventory, read crew issues. Each tool server
speaks MCP. Without a gateway every agent holds its own copy of every credential
and every server is a separate open door. Agentgateway puts one door in front of
all of them: one address, one API key at the listener, the backend tokens held by
the gateway and never handed to the agent. This is row 4 of the fortress stack
(docs/specs/fortress-stack.md, CP5).

Two routes today:

- `/estate/mcp` — Datasette with datasette-mcp over `catalog/estate.db`,
  read-only. Tools: `list_databases`, `get_database_schema`, `execute_sql`.
- `/github/mcp` — GitHub's own MCP server, `--read-only --toolsets issues`.
  Tools: `list_issues`, `get_label`, and four more.

## What it costs

Nothing per month. Agentgateway (Apache-2.0), github-mcp-server (MIT), Datasette
and datasette-mcp (Apache-2.0) all run on this Mac under colima. Three containers,
a few hundred MiB.

The maintenance cost is version pinning: `mcp/agentgateway.yml` pins
agentgateway v1.4.1 and github-mcp-server v1.10.1; `bin/idp-ci` validates
`mcp/agentgateway.yaml` against the pinned tag's config schema, so a bump that
changes the config format fails CI before it fails at runtime. datasette-mcp
0.1a0 and Datasette 1.0a38 are alphas and will need a bump when they release.

## Where it lives

- `mcp/agentgateway.yml` — compose file, three services.
- `mcp/agentgateway.yaml` — gateway config: one bind on 127.0.0.1:3310, two
  routes, strict API-key policy on both, backend token injected toward GitHub only.
- `mcp/estate-mcp.Dockerfile` — the Datasette + datasette-mcp image.
- `bin/mcp-up`, `bin/mcp-status`, `bin/mcp-down` — same shape as `bin/litellm-*`.
  `mcp-up` writes a 600 `.env` with the listener key and the GitHub token read
  from the age vault; `mcp-status` calls `tools/list` and one `tools/call` per
  route through the gateway and exits 1 on any failure.

The gateway listens on 127.0.0.1 only. Nothing reaches it from the network.

## How to stop it

    bin/mcp-down

## Known gap

The vault holds no `GITHUB_MCP_TOKEN` yet. Until it does, `bin/mcp-status`
prints `github FAIL http 400` and exits 1; the estate route works regardless.
