# Datasette with the datasette-mcp plugin. There is no published image that carries a
# Datasette 1.0 alpha (docker.io/datasetteproject/datasette stops at 0.65.x) and the
# plugin needs 1.0's permission hooks, so this is the smallest build that exists.
# Both versions are pinned; bump them together.
#
# PyYAML (MIT): crew#216 CP1 adds one file, plugins/estate_inventory.py, that registers
# a fourth tool -- get_estate_inventory -- through datasette-mcp's own extension point,
# register_mcp_tools(datasette, mcp) (github.com/datasette/datasette-mcp). It reads the
# generated Backstage catalog (catalog/catalog-info.yaml), a multi-document YAML file
# already produced by bin/catalog-gen, so parsing it needs a YAML reader; PyYAML is the
# one every other Python tool in this repo already uses (bin/idp-up validates
# agentgateway.yaml with it).
FROM docker.io/python:3.13-slim
RUN pip install --no-cache-dir "datasette==1.0a38" "datasette-mcp==0.1a0" "pyyaml==6.0.3" \
 && useradd --system --uid 10001 datasette
COPY plugins /app/plugins
USER datasette
EXPOSE 8001
