# The MCP door, proved with one call

Every agent tool call in this estate goes through one gateway (decision 0006). This page is what it
looks like when that door is open, and what it looks like when it is not.

## A real call, against the running gateway

```
$ MCP_GATEWAY_KEY=<vault entry mcp-gateway> python3 bin/idp-mcp-door --route estate
ok    mcp-door http://agentgateway.mcp.svc.cluster.local:3000/estate/mcp answered 200 with
      14 tool(s): ask_holmes, execute_change, execute_sql, get_database_schema,
      get_estate_inventory, get_estate_state, get_session, get_workload_logs
```

Fourteen tools, from the live gateway, through the same Service and the same policies a real agent
uses. That is the door working.

## The header is the whole story

This gateway's `apiKey` policy reads **`Authorization: Bearer <key>`**. Nearly every MCP client —
and the estate's own documentation — sends `x-api-key`. That spelling is rejected:

```
$ MCP_GATEWAY_KEY=<the same, correct key> ... -H 'x-api-key: <key>'
HTTP 401   error="api key authentication failure: no API Key found"   reason=APIKeyAuth
```

The same value in the right header:

```
HTTP 200   protocol=mcp   mcp.method.name=tools/list   duration=21ms
```

A 401 that means "wrong header" is indistinguishable from a 401 that means "wrong key" or "the
service is down". That ambiguity cost an evening on 2026-09-13, which is why the probe prints the
header it used and why the gateway logged `reason=APIKeyAuth` for all three.

## What the gateway records in its own log

```
http.status=200 protocol=mcp mcp.method.name=tools/list duration=21ms
```

It knows the MCP method name and the protocol. That is a real agent action passing the door, and it
is the traffic the evidence layer exists to record.

## Where to look

- `bin/idp-mcp-door` — the probe
- `platform/mcp/agentgateway.yaml` — the routes and the apiKey policy
- `docs/how-to/onboarding/mcp-door.md` — what it costs and how to stop it
