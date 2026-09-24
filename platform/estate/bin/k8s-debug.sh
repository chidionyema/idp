#!/usr/bin/env bash
# k8s.debug — one-shot cluster diagnostic. Read-only. Timeout-bounded.
set -uo pipefail

NS="${1:-}"
FOCUS="${2:-}"
DEPTH="${3:-full}"
SINCE="${4:-1h}"
LOG_LINES="${5:-50}"

KC=(kubectl --kubeconfig "${OKE_KUBECONFIG:-$HOME/.kube/config}" --request-timeout=10s)

hdr() { printf '\n=== %s ===\n' "$1"; }

ns_arg() { [ -n "$NS" ] && printf -- '-n %s' "$NS"; }

# --- 1. Overview -------------------------------------------------------------
hdr "OVERVIEW"
"${KC[@]}" get nodes --no-headers 2>/dev/null \
  | awk '{r[$2]++} END {for (s in r) printf "nodes %s: %d\n", s, r[s]}'
"${KC[@]}" get pods -A --no-headers 2>/dev/null \
  | awk '{r[$4]++} END {for (s in r) printf "pods %s: %d\n", s, r[s]}'

# --- 2. Nodes ----------------------------------------------------------------
hdr "NODES"
"${KC[@]}" get nodes -o wide 2>&1 | head -20

if [ "$DEPTH" = "quick" ]; then
  hdr "PROBLEM PODS"
  "${KC[@]}" get pods -A --field-selector=status.phase!=Running,status.phase!=Succeeded 2>&1 | head -40
  exit 0
fi

# --- 3. Problem pods ---------------------------------------------------------
hdr "PROBLEM PODS (not Running/Succeeded)"
"${KC[@]}" get pods -A \
  --field-selector=status.phase!=Running,status.phase!=Succeeded 2>&1 | head -60

# --- 4. High-restart pods ----------------------------------------------------
hdr "HIGH RESTARTS (>3)"
"${KC[@]}" get pods -A --no-headers 2>/dev/null \
  | awk '$5+0 > 3 {print}' | sort -k5 -rn | head -20

# --- 5. Degraded workloads ---------------------------------------------------
hdr "DEGRADED WORKLOADS"
for kind in deployment statefulset daemonset; do
  "${KC[@]}" get "$kind" -A --no-headers 2>/dev/null \
    | awk -v k="$kind" '$3 != $4 {printf "%s  %s/%s  %s  ready=%s desired=%s\n", k, $1, $2, "", $3, $4}'
done | head -40

# --- 6. Warning events -------------------------------------------------------
hdr "WARNING EVENTS (last $SINCE)"
"${KC[@]}" get events -A --field-selector type=Warning 2>&1 \
  | sort -k1,1 -k5 2>/dev/null | tail -40

# --- 7. Pending PVCs ---------------------------------------------------------
hdr "PVCs NOT BOUND"
"${KC[@]}" get pvc -A --no-headers 2>/dev/null \
  | awk '$3 != "Bound" {print}' | head -20

# --- 8. Services with no endpoints -------------------------------------------
hdr "SERVICES WITH ZERO ENDPOINTS"
"${KC[@]}" get endpoints -A --no-headers 2>/dev/null \
  | awk '$3 == "<none>" || NF < 3 {print $1, $2}' | head -20

# --- 9. Flux (if present) ----------------------------------------------------
if "${KC[@]}" get ns flux-system >/dev/null 2>&1; then
  hdr "FLUX KUSTOMIZATIONS"
  "${KC[@]}" get kustomizations -A 2>&1 | head -30
  hdr "FLUX HELMRELEASES"
  "${KC[@]}" get helmreleases -A 2>&1 | head -30
fi

# --- 10. Focus mode ----------------------------------------------------------
if [ -n "$FOCUS" ]; then
  hdr "FOCUS: $FOCUS"
  "${KC[@]}" describe pod $ns_arg "$FOCUS" 2>&1 | tail -60
fi

# --- 11. Failing pod logs ----------------------------------------------------
hdr "LOGS FROM PROBLEM PODS (last $LOG_LINES lines each)"
BAD=$("${KC[@]}" get pods -A \
  --field-selector=status.phase!=Running,status.phase!=Succeeded \
  --no-headers 2>/dev/null | awk '{print $1"/"$2}' | head -5)

for p in $BAD; do
  ns="${p%%/*}"; pod="${p##*/}"
  printf '\n--- %s/%s ---\n' "$ns" "$pod"
  "${KC[@]}" -n "$ns" logs "$pod" --tail="$LOG_LINES" --since="$SINCE" 2>&1 \
    | tail -"$LOG_LINES"
done
