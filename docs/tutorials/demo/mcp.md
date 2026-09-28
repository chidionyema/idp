# Demo — the MCP gateway

Recorded 2026-08-24 on the CP5 branch. Key values are never printed.

    $ docker compose -f mcp/agentgateway.yml ps
    mcp-agentgateway  ghcr.io/agentgateway/agentgateway:v1.4.1   Up             127.0.0.1:3310->3000/tcp
    mcp-estate        idp/estate-mcp                              Up (healthy)   8001/tcp
    mcp-github        ghcr.io/github/github-mcp-server:v1.10.1   Up             8082/tcp

List the estate tools through the gateway:

    $ curl -s -H "Authorization: Bearer $MCP_GATEWAY_KEY" \
        -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' http://127.0.0.1:3310/estate/mcp
    HTTP 200 — tools: list_databases, get_database_schema, execute_sql

Ask it the same question the portal answers:

    $ ... "method":"tools/call","params":{"name":"execute_sql","arguments":{"database":"estate","sql":"select count(*) as n from assets"}}
    {"columns":["n"],"rows":[[239]],"truncated":false,"isError":false}

The GitHub route, read-only:

    $ ... http://127.0.0.1:3310/github/mcp  tools/list
    HTTP 200 — 6 tools (get_label, list_issues, ...)
    $ ... tools/call list_issues {"owner":"chidionyema","repo":"crew","state":"OPEN","perPage":1}
    HTTP 200 — issue #182

Without the key:

    $ curl -s -o /dev/null -w '%{http_code}\n' -d '{}' http://127.0.0.1:3310/estate/mcp
    401

The status script, with the GitHub token in the vault and without it:

    $ bin/mcp-status
    estate  ok    3 tools
    github  ok    6 tools
    $ bin/mcp-status          # vault without GITHUB_MCP_TOKEN
    estate  ok    3 tools
    github  FAIL  http 400
    (exit 1)

CI:

    $ bin/idp-ci
    ok    compose  mcp/agentgateway.yml
    ok    schema   mcp/agentgateway.yaml against agentgateway v1.4.1
    PASS  idp-ci
