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
# build-multiarch.yml builds this file for BOTH linux/amd64 and linux/arm64, so the kubectl
# fetch below is derived from the build's own target architecture rather than typed. TARGETARCH
# is exported by buildkit on every build, amd64 and arm64 alike.
ARG TARGETARCH
# MUM-288: the world-model door's six graders ARE this repository's own bin/ programs
# (bin/idp-admission-dryrun, bin/idp-rules, bin/idp-shadow-verify, bin/idp-calico-deny-log,
# bin/idp-fits-a-node, bin/idp-blast-grade). The plugin marshals their verdicts rather than
# copying their logic, so the programs have to exist where the plugin runs. Before this,
# the image carried only plugins/ and every grader answered "could not run: ValueError" on
# the live cluster -- the door opened and refused everything, which is not a graded door.
#
# kubectl (Apache-2.0) is what bin/idp-admission-dryrun shells to for
# `kubectl apply --dry-run=server`: Kyverno's ClusterPolicies and every validating webhook
# answer for real and nothing persists. It is the admission grader's only cluster read; the
# other five read a file or a provided input (see each grader's docstring).
#
# Fetched the same way platform/oci/cloud-init/bridge.yaml fetches it for the estate's own
# hosts (dl.k8s.io/release/stable.txt, then that version's linux/amd64 binary), so there is
# one kubectl installer idiom in this repository rather than two.
RUN pip install --no-cache-dir "datasette==1.0a38" "datasette-mcp==0.1a0" "pyyaml==6.0.3" \
 && apt-get update \
 && apt-get install -y --no-install-recommends curl \
 && rm -rf /var/lib/apt/lists/* \
 && kubectl_version="$(curl -fsSL https://dl.k8s.io/release/stable.txt)" \
 && curl -fsSLo /usr/local/bin/kubectl \
      "https://dl.k8s.io/release/${kubectl_version}/bin/linux/${TARGETARCH}/kubectl" \
 && chmod 0755 /usr/local/bin/kubectl \
 && useradd --system --uid 10001 datasette
# crew#216 CP2 adds a second plugin, plugins/workload_state.py, through the same
# --plugins-dir mechanism. It needs no new dependency: sqlite3 is stdlib, and it reads
# the estate.db already mounted below for execute_sql/list_databases.
# crew#216 CP3 adds a third plugin, plugins/workload_logs.py -- also no new
# dependency (plistlib is stdlib). It reads a scheduled_job asset's own launchd
# plist path, which is not mounted into this image; see the plugin's own docstring
# for the residual.
COPY mcp/plugins /app/plugins
# The grader programs, their registry, and the trees the graders read by path at run time.
# ESTATE_REPO_ROOT=/app makes the plugin resolve `/app/bin/...`.
#
# `bin/` carries the six grader programs themselves. `rules.yaml` is bin/idp-rules' registry.
# `policy/fixtures` and `tests/fixtures` are read BY bin/idp-rules when it grades a rule against
# its two fixtures (a rule row names both), so a laws grade without them is a laws grade that
# cannot run. These are the whole of what the graders touch; nothing else in the tree is copied,
# and each path here is one a grader was observed to open.
#
# The build context is this repository's root, not mcp/. The graders live at bin/ and
# rules.yaml at the root, and a Docker build can only COPY from its own context -- the previous
# mcp/-rooted context made every one of these COPY lines unresolvable, so the image could not be
# built at all once the graders were named. estate-scheduler.Dockerfile already builds from the
# root for the same reason, and that is the row bin/dockerfiles now emits for this file too.
COPY bin /app/bin
COPY rules.yaml /app/rules.yaml
COPY policy/fixtures /app/policy/fixtures
COPY tests/fixtures /app/tests/fixtures
USER datasette
EXPOSE 8001
