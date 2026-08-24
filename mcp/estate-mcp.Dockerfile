# Datasette with the datasette-mcp plugin. There is no published image that carries a
# Datasette 1.0 alpha (docker.io/datasetteproject/datasette stops at 0.65.x) and the
# plugin needs 1.0's permission hooks, so this is the smallest build that exists.
# Both versions are pinned; bump them together.
FROM docker.io/python:3.13-slim
RUN pip install --no-cache-dir "datasette==1.0a38" "datasette-mcp==0.1a0" \
 && useradd --system --uid 10001 datasette
USER datasette
EXPOSE 8001
