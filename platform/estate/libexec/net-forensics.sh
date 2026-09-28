#!/usr/bin/env bash
# net-forensics -- READ-ONLY node network forensics, one call, every node (or one).
#
# Runs inside each node's calico-node pod (privileged, host network namespace), so it reads the
# HOST's kernel state without an ssh key or a debug pod. The calico-node image has no head, awk,
# nstat, ss, bridge or dmesg: everything below is sh + grep + ip + iptables + /proc reads.
# Nothing here writes. Findings are prefixed "!! " so an agent can grep them.
#
# Born 2026-09-26 (SPIRE outage): cross-node pod TCP dead; the cause was a flannel MASQUERADE chain
# that survived --ip-masq removal. k8s-diag reads API objects only and names a "k8s-net-doctor"
# companion for packet level that never existed; this is it.
#
# usage: net-forensics.sh [node|all] [probe]
#   probe  -- also launch two throwaway busybox pods and test pod->pod TCP across nodes
#             (creates and deletes pods; off by default).
set -uo pipefail
export PATH="/opt/local/bin:/opt/homebrew/bin:/usr/local/bin:$HOME/.local/bin:$HOME/.rd/bin:$PATH"
NODE="${1:-all}"; PROBE="${2:-}"
K=(kubectl --request-timeout=30s)

read -r -d '' REMOTE <<'SH'
f() { printf '\n--- %s\n' "$1"; }
f "1 limits: conntrack"
c=$(cat /proc/sys/net/netfilter/nf_conntrack_count 2>/dev/null); m=$(cat /proc/sys/net/netfilter/nf_conntrack_max 2>/dev/null)
[ -n "$c" ] && { echo "conntrack $c / $m"; [ $((c*100/m)) -ge 80 ] && echo "!! conntrack >= 80% full: new flows drop silently"; }
echo "file-nr $(cat /proc/sys/fs/file-nr)"; cat /proc/net/sockstat
for p in cpu memory io; do [ -f /proc/pressure/$p ] && echo "psi $p: $(grep ^some /proc/pressure/$p)"; done

f "2 rp_filter (1 strict drops asymmetric/overlay traffic)"
for d in /proc/sys/net/ipv4/conf/*; do n=${d##*/}; v=$(cat $d/rp_filter)
  case "$n" in all|default|enp*|eth*|ens*|vxlan*|flannel*|tunl*|cni*) echo "$n=$v";; esac
  [ "$v" = 1 ] && case "$n" in all|vxlan*|flannel*|tunl*|cni*) echo "!! $n rp_filter=1";; esac
done
echo "ip_forward=$(cat /proc/sys/net/ipv4/ip_forward)"; [ "$(cat /proc/sys/net/ipv4/ip_forward)" = 1 ] || echo "!! ip_forward off"

f "3 kernel protocol drop counters (/proc/net/snmp + netstat, non-zero)"
for file in /proc/net/snmp /proc/net/netstat; do
  while read -r hk; do read -r vv; set -- $vv; pfx=$1; shift
    for k in ${hk#* }; do v=$1; shift
      case "$k" in *Drop*|*Err*|*Fail*|*Overflow*|*Reject*|*Discard*|*Retrans*|*Timeout*) [ "$v" != 0 ] && echo "$pfx$k=$v";; esac
    done; done < "$file"; done

f "4 interfaces: MTU, state, rx/tx errors+drops (/proc/net/dev)"
ip -o link show | grep -E "enp|eth|ens|vxlan|flannel|tunl|cni" | sed -E 's/^[0-9]+: ([^:@]+).*mtu ([0-9]+).*state ([A-Z]+).*/\1 mtu=\2 state=\3/'
grep -E "enp|eth|ens|vxlan|flannel|tunl|cni" /proc/net/dev | while read -r i rb rp re rd _ _ _ _ tb tp te td _; do
  echo "${i%:} rx_err=$re rx_drop=$rd tx_err=$te tx_drop=$td"; done
ip -d link show vxlan.calico 2>/dev/null | grep -o "vxlan id [0-9]* local [0-9.]* dev [a-z0-9]* .*dstport [0-9]*"
ip -d link show flannel.1 2>/dev/null | grep -o "vxlan id [0-9]* local [0-9.]* dev [a-z0-9]* .*dstport [0-9]*"

f "5 CNI collision: flannel vs calico rules (nft + legacy)"
for t in nat filter mangle raw; do
  fl=$(iptables-nft-save -t $t 2>/dev/null | grep -c FLANNEL); ca=$(iptables-nft-save -t $t 2>/dev/null | grep -c cali-)
  lg=$(iptables-legacy-save -t $t 2>/dev/null | grep -c "^-A")
  echo "$t: flannel=$fl calico=$ca legacy_rules=$lg"
done
iptables-nft-save -c -t nat 2>/dev/null | grep -E "FLANNEL-POSTRTG.*MASQUERADE|-j FLANNEL-POSTRTG" | grep -v "^\[0:0\]" \
  | while read -r l; do echo "!! flannel masquerade live (SNATs cross-node pod traffic): $l"; done
iptables-legacy-save -c 2>/dev/null | grep -E "^:|DROP|REJECT|MASQ" | grep -v "^\[0:0\] -A"

f "6 DROP/REJECT rules that have hit (nft)"
iptables-nft-save -c 2>/dev/null | grep -E -- "-j (DROP|REJECT)" | grep -v "^\[0:0\]"

f "7 routing: pod routes, policy rules, broken neighbours"
ip route | grep -E "10\.244|vxlan|flannel|blackhole" | grep -v "dev cali"
echo "local workload routes: $(ip route | grep -c 'dev cali')"
ip rule show
ip neigh show dev vxlan.calico 2>/dev/null
ip neigh show nud failed 2>/dev/null | while read -r l; do echo "!! neighbour FAILED: $l"; done
ip neigh show nud incomplete 2>/dev/null | while read -r l; do echo "!! neighbour INCOMPLETE: $l"; done

f "8 overlay admission: which hosts calico accepts VXLAN from"
iptables-nft-save -c -t filter 2>/dev/null | grep -E -- "--dports 4789|all-vxlan|all-hosts-net" | grep -v "^:"
for s in $(ipset list -n 2>/dev/null | grep -E "all-vxlan|all-hosts"); do m=""; for x in $(ipset list "$s" 2>/dev/null | sed -n '/^Members:/,$p' | grep -v Members); do m="$m $x"; done; echo "ipset $s:${m:- (unreadable or empty)}"; done
SH
DROPS='iptables-nft-save -c 2>/dev/null | grep -E -- "-j (DROP|REJECT)"'

nodes=$("${K[@]}" get nodes -o jsonpath='{.items[*].metadata.name}')
[ "$NODE" = all ] || nodes="$NODE"
echo "================ cluster: calico's view of each node (tunnel peers + VXLAN allow-list are built from it)"
"${K[@]}" get nodes -o jsonpath='{range .items[*]}{.metadata.name} internal={.status.addresses[?(@.type=="InternalIP")].address} calico={.metadata.annotations.projectcalico\.org/IPv4Address} vtep={.metadata.annotations.projectcalico\.org/IPv4VXLANTunnelAddr}{"\n"}{end}' 2>&1 \
  | while read -r name int cal vtep; do echo "$name $int $cal $vtep"
      [ "${cal#calico=}" = "" ] && echo "!! calico has no IPv4Address for $name: peers cannot tunnel to it"
      c=${cal#calico=}; [ -n "$c" ] && [ "${c%/*}" != "${int#internal=}" ] && echo "!! calico address ${c%/*} != node InternalIP ${int#internal=} on $name: tunnels + VXLAN allow-list use the wrong IP"
    done

CN=""
cpod() { for kv in $CN; do [ "${kv%%=*}" = "$1" ] && echo "${kv#*=}"; done; }
for n in $nodes; do
  C=$("${K[@]}" -n kube-system get pod -l k8s-app=calico-node --field-selector "spec.nodeName=$n" -o name 2>/dev/null)
  [ -n "$C" ] && CN="$CN $n=$C"
  echo; echo "================ node $n (${C:-no calico-node pod})"
  [ -n "$C" ] || { echo "!! no calico-node on $n: cannot read host state"; continue; }
  out=$("${K[@]}" -n kube-system exec "$C" -c calico-node -- sh -c "$REMOTE" 2>&1 | grep -v "iptables-legacy tables present")
  echo "$out"
  # a peer node the VXLAN allow-list omits has its tunnel packets dropped on arrival
  for p in $nodes; do [ "$p" = "$n" ] && continue
    set_line=$(printf '%s\n' "$out" | grep -E "^ipset cali40all-vxlan-net: [0-9]")
    [ -n "$set_line" ] && ! printf '%s\n' "$set_line" | grep -qw "$p" \
      && echo "!! peer $p missing from $n VXLAN allow-list: its tunnel packets are dropped on arrival"
  done
done

KCOUNT='for file in /proc/net/snmp /proc/net/netstat; do while read -r hk; do read -r vv; set -- $vv; pfx=$1; shift; for k in ${hk#* }; do echo "$pfx$k $1"; shift; done; done < "$file"; done'
kcounters() { for n in $nodes; do c=$(cpod "$n"); [ -n "$c" ] || continue
  "${K[@]}" -n kube-system exec "$c" -c calico-node -- sh -c "$KCOUNT" 2>/dev/null | sed "s/^/$n\t/;s/ /\t/"; done; }
# per-rule DROP/REJECT packet counts on every node, "node<TAB>rule<TAB>packets"
drops() { for n in $nodes; do c=$(cpod "$n"); [ -n "$c" ] || continue
  "${K[@]}" -n kube-system exec "$c" -c calico-node -- sh -c "$DROPS" 2>/dev/null \
    | sed -E "s/^\[([0-9]+):[0-9]+\] (.*)/$n\t\2\t\1/"; done; }

if [ "$PROBE" = probe ]; then
  echo; echo "================ cross-node pod->pod TCP probe (kube-system client -> default listener: no policy fences either end)"
  set -- $nodes
  [ $# -ge 2 ] || { echo "single node: no cross-node path to probe"; exit 0; }
  SC='"securityContext":{"runAsNonRoot":true,"runAsUser":65534,"seccompProfile":{"type":"RuntimeDefault"}}'
  CSC='"securityContext":{"allowPrivilegeEscalation":false,"capabilities":{"drop":["ALL"]}},"resources":{"requests":{"cpu":"10m","memory":"16Mi"},"limits":{"cpu":"50m","memory":"32Mi"}}'
  fails=0
  for pair in "$1 $2" "$2 $1"; do set -- $pair; tag=nf-$RANDOM
    "${K[@]}" -n default run "$tag-l" --restart=Never --image=busybox:1.36 --overrides='{"spec":{"nodeName":"'"$2"'",'"$SC"',"containers":[{"name":"t","image":"busybox:1.36","command":["sh","-c","mkdir -p /tmp/w; echo ok > /tmp/w/index.html; timeout 90 httpd -f -vv -p 8099 -h /tmp/w 2>&1"],'"$CSC"'}]}}' >/dev/null
    "${K[@]}" -n default wait --for=condition=Ready "pod/$tag-l" --timeout=90s >/dev/null
    L=$("${K[@]}" -n default get pod "$tag-l" -o jsonpath='{.status.podIP}')
    before=$(drops); kbefore=$(kcounters)
    "${K[@]}" -n kube-system run "$tag-c" --restart=Never --image=busybox:1.36 --overrides='{"spec":{"nodeName":"'"$1"'",'"$SC"',"containers":[{"name":"t","image":"busybox:1.36","command":["sh","-c","for i in 1 2 3 4 5; do e=$(nc -w3 '"$L"' 8099 </dev/null 2>&1) && printf OPEN\\  || case $e in *efused*) printf REFUSED\\ ;; *) printf TIMEOUT\\ ;; esac; sleep 3; done; echo; sleep 20"],'"$CSC"'}]}}' >/dev/null
    # 5 attempts, 3s apart: TIMEOUT = packets dropped, REFUSED = reached a host that said no;
    # TIMEOUT then OPEN = programming lag, mixed = loss, all TIMEOUT = block
    CIP=$("${K[@]}" -n kube-system get pod "$tag-c" -o jsonpath='{.status.podIP}' 2>/dev/null)
    for _ in $(seq 24); do r=$("${K[@]}" -n kube-system logs "$tag-c" 2>/dev/null); [ "$(printf '%s' "$r" | wc -w)" -ge 5 ] && break; sleep 5; done
    r=$(printf '%s' "$r" | tr -s ' \n' ' '); r=${r% }; seen=$("${K[@]}" -n default logs "$tag-l" 2>/dev/null | grep -c "$CIP") 
    echo "$1 -> $2 ($L:8099): ${r:-no result}; listener log lines from client ${CIP:-?}: ${seen:-0}"
    [ "$r" = "OPEN OPEN OPEN OPEN OPEN" ] || { echo "!! cross-node pod TCP $1 -> $2 fails ($r)"; fails=$((fails+1)); }
    # which DROP rules counted packets while this probe ran: names the rule that ate it
    awk -F'\t' 'NR==FNR{b[$1 FS $2]=$3; next} ($3-b[$1 FS $2])>0{print "!! dropped during probe on " $1 " (+" $3-b[$1 FS $2] "): " $2}' \
      <(printf '%s\n' "$before") <(drops)
    awk -F'\t' 'NR==FNR{b[$1 FS $2]=$3; next} ($2 ~ /Drop|Err|Fail|Overflow|Discard|Reject/) && ($3-b[$1 FS $2])>0{print "!! kernel counter during probe on " $1 ": " $2 " +" $3-b[$1 FS $2]}' \
      <(printf '%s\n' "$kbefore") <(kcounters)
    "${K[@]}" -n kube-system delete pod "$tag-c" --wait=false >/dev/null; "${K[@]}" -n default delete pod "$tag-l" --wait=false >/dev/null
  done
  # a verify that exits 0 on a failed probe cannot fail (2026-09-26): the symptom decides the exit
  [ "$fails" = 0 ] || exit 3
fi
