#!/usr/bin/env bash
# The same question asked of the platform.
python3 -c 'from mcp.plugins.workload_state import build_workload_state'
bin/estate-twin-runtime --once --dead
bin/idp-kube get pods -n via-negativa
