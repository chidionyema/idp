#!/usr/bin/env bash
# Install the statically linked Pennyd on the Oracle recovery host.
#
# This replaces the memory-heavy Python LiteLLM container. The host's instance principal already
# reads the router-recovery vault entry and the estate-router-recovery bucket; that is the whole
# trust boundary. No secret is written into the object store.
set -euo pipefail

if [ "$(id -u)" != "0" ]; then
  exec sudo -n bash "$0" "$@"
fi

export OCI_CLI_AUTH=instance_principal SUPPRESS_LABEL_WARNING=True
region=uk-london-1
compartment=ocid1.compartment.oc1..aaaaaaaaynd3mq5nhnccywzbmwfdevpkmvyzwcsxm7kyevei5s72ikyge5oq
namespace=lr7j97fk6nor
bucket=estate-router-recovery
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT

install -d -m 0700 /etc/estate /etc/pennyd /var/lib/pennyd /opt/pennyd

sid=$(oci vault secret list --compartment-id "$compartment" --region "$region" \
  --name router-recovery --lifecycle-state ACTIVE --query 'data[0].id' --raw-output --all)
[ -n "$sid" ] && [ "$sid" != null ] || {
  echo "BLIND pennyd-install: no ACTIVE router-recovery secret"
  exit 2
}

umask 077
oci secrets secret-bundle get --secret-id "$sid" --region "$region" \
  --query 'data."secret-bundle-content".content' --raw-output |
  base64 -d |
  python3 -c 'import json,sys; [print(k + "=" + v) for k, v in json.load(sys.stdin).items()]' \
    > /etc/estate/router.env.new
chmod 600 /etc/estate/router.env.new
mv /etc/estate/router.env.new /etc/estate/router.env

oci os object get --namespace "$namespace" --bucket-name "$bucket" \
  --name pennyd-bundle.tgz --file "$work/pennyd-bundle.tgz" --region "$region"
tar -xzf "$work/pennyd-bundle.tgz" -C "$work"
(cd "$work" && sha256sum -c SHA256SUMS)

systemctl stop estate-pennyd.service 2>/dev/null || true
install -m 0755 "$work/pennyd" /opt/pennyd/pennyd
install -m 0755 "$work/prepare-keys" /opt/pennyd/prepare-keys
install -m 0644 "$work/pennyd.toml" /opt/pennyd/pennyd.toml
install -d -m 0755 /opt/pennyd/providers
install -m 0644 "$work"/providers/*.toml /opt/pennyd/providers/
install -m 0644 "$work/estate-pennyd.service" /etc/systemd/system/estate-pennyd.service

# Keep the Python unit on disk as a labelled rollback, but remove it from the active path.
systemctl disable --now estate-router.service 2>/dev/null || true
podman rm -f estate-router 2>/dev/null || true

systemctl daemon-reload
systemctl enable --now estate-pennyd.service

for _ in $(seq 1 40); do
  if curl -fsS --max-time 2 http://127.0.0.1:4000/health >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

curl -fsS --max-time 5 http://127.0.0.1:4000/health
echo
echo "pennyd_sha256=$(sha256sum /opt/pennyd/pennyd | awk '{print $1}')"
echo "pennyd_state=$(systemctl is-active estate-pennyd.service)"
echo "litellm_state=$(systemctl is-active estate-router.service 2>/dev/null || true)"

systemctl restart estate-tunnel.service 2>/dev/null || true
for _ in $(seq 1 12); do
  if podman ps --format '{{.Names}}' 2>/dev/null | grep -qx estate-tunnel; then
    break
  fi
  sleep 2
done
echo "tunnel_state=$(systemctl is-active estate-tunnel.service 2>/dev/null || true)"
