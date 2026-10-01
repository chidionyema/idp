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
# See sovereign-worker.Dockerfile: the base floats, and on 2026-09-12 an upstream rebuild
# shipped perl-base 5.40.1-6 with three CRITICAL CVEs (CVE-2026-13221, CVE-2026-42496,
# CVE-2026-8376) against a fix already published as 5.40.1-6+deb13u1.
RUN apt-get update \
 && apt-get upgrade -y \
 && rm -rf /var/lib/apt/lists/*
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
RUN pip install --no-cache-dir "datasette==1.0a38" "datasette-mcp==0.1a0" "mcp==2.2.0" "pyyaml==6.0.3" \
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
# The grader programs and the trees they read by path at run time.
# ESTATE_REPO_ROOT=/app makes the plugin resolve `/app/bin/...`.
#
# `bin/` carries the grader programs themselves; the fixture trees are what they read. rules.yaml
# and bin/idp-rules were deleted 2026-09-21 (founder ruling: a rule is a rung in bin/idp-ci, not a
# row in a table), so the registry is no longer copied and the laws grade in mcp/plugins/
# estate_simulate.py reports UNKNOWN rather than folding per-rule verdicts.
#
# The build context is this repository's root, not mcp/. The graders live at bin/, and a Docker
# build can only COPY from its own context -- the previous mcp/-rooted context made every one of
# these COPY lines unresolvable, so the image could not be built at all once the graders were
# named. estate-scheduler.Dockerfile already builds from the root for the same reason, and that is
# the row bin/dockerfiles now emits for this file too.
COPY bin /app/bin
COPY policy/fixtures /app/policy/fixtures
COPY tests/fixtures /app/tests/fixtures
# The intent library, so estate_list and its plain-words search answer in production. Until
# 2026-10-01 the image carried none: the live pod answered "# 0 intents available" and
# estate_invoke said "unknown intent" for every name, so the one door agents keep once bash is
# gone was empty wherever it was served.
COPY platform/estate/intents /app/intents
ENV ESTATE_INTENTS_DIR=/app/intents
# The build fails if the estate tools cannot register on the MCP SDK installed above. From 2026-09-28
# the pod crash-looped on `add_tool() got an unexpected keyword argument 'inputSchema'` (crew#990),
# found only at start-up; this runs the same registration at build time, with each tool's schema.
RUN cd /tmp && python -c "import importlib.util,sys,asyncio; from mcp.server.mcpserver import MCPServer; \
spec=importlib.util.spec_from_file_location('estate_mcp','/app/plugins/estate_mcp.py'); m=importlib.util.module_from_spec(spec); \
sys.modules['estate_mcp']=m; spec.loader.exec_module(m); s=MCPServer('build-check'); m.register_mcp_tools(datasette=None, mcp=s); \
got={t.name: t.input_schema for t in asyncio.run(s.list_tools())}; \
assert set(got)=={d['name'] for d in m.TOOL_DEFS}, got; \
assert all(set(got[d['name']].get('required',[]))==set(d['inputSchema'].get('required',[])) for d in m.TOOL_DEFS); \
print('estate-mcp tools register:', sorted(got))"
# The build fails if the library did not arrive or the search cannot find a known intent in it.
RUN cd /tmp && python -c "import importlib.util; \
spec=importlib.util.spec_from_file_location('estate_mcp','/app/plugins/estate_mcp.py'); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); \
n=len(m._load_intents()); assert n >= 50, 'only %d intents in /app/intents' % n; \
hit=m._estate_list({'query': 'ci status'}); assert '## intent ci-status' in hit, hit[:300]; \
print('estate-mcp intent library:', n, 'intents, search finds ci-status')"
USER datasette
EXPOSE 8001
