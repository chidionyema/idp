# The estate context broker: the one public door to the estate's context.
#
# This image carries the broker and nothing else. The context engine is a separate image
# (gortex-engine.Dockerfile) and it never runs here: it is a private sidecar in the same pod,
# bound to loopback. The door and the engine are separate images because they have different
# lifetimes and different trust: this one faces the network, that one does not.
#
# The broker is standard library only, on purpose. It is the estate's enforcement point, and an
# enforcement point that depends on a library whose transport API can change underneath it is a
# worse enforcement point (the MCP SDK was the plan; a hand-written JSON-RPC transport over
# http.server is what shipped, and it is testable on a laptop without a container).
FROM docker.io/python:3.13-slim
# The base floats, and on 2026-09-12 an upstream rebuild shipped perl-base with three CRITICAL
# CVEs against a fix already published (see estate-mcp.Dockerfile for the same note).
RUN apt-get update \
 && apt-get upgrade -y \
 && rm -rf /var/lib/apt/lists/* \
 && useradd --system --uid 10001 --create-home broker
COPY platform/estate/context /app/estate/context
ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1
# The build fails if the package does not import, if its tools do not register, or if the policy
# module is missing. A door that cannot start is a closed door, and it must not be closed by a
# packaging mistake nobody saw until a client called it.
RUN cd /tmp && python3 -c "
from estate.context import server, broker, claims
names = sorted(t['name'] for t in server.TOOLS)
assert names == ['estate_context', 'estate_context_status'], names
assert server.decide(broker.ContextRequest(tool='smart_context', paths=[], request_commit=None, mode='committed', token_budget=10),
                     broker.BrokerState(index_commit='a'*40, head_commit='a'*40, claim_paths=['x'], secrets={}, engine_reachable=True)).verdict == 'ALLOW'
print('estate-context-broker tools register:', names)
"
USER broker
EXPOSE 8002
CMD ["python3", "-m", "estate.context.server"]
