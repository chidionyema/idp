# k3s Legion substrate — estate stack on the Oracle Always Free ARM VM

One VM (4 OCPU / 24 GB aarch64, $0) runs the whole estate control plane.
The Mac is a dev client only. No OKE. GitHub-hosted runners provide burst compute.

## 1. Provision the VM (founder, ~15 min)

Oracle Cloud → Always Free → Ampere A1 ARM, 4 OCPU / 24 GB, Ubuntu 22.04 aarch64.
Open ingress 6443 (k8s API) to your IP only; 22 for ssh. Cloudflare Tunnel carries
all user-facing traffic — no public ports for services.

## 2. Install k3s (founder, one line)

    curl -sfL https://get.k3s.io | sh -s - --disable traefik

    export KUBECONFIG=/etc/rancher/k3s/k3s.yaml

## 3. Create secrets (founder — never through agents)

See secrets.example.yaml for the exact `kubectl create secret` command.
Real values are typed by the founder directly; they never enter git, logs, or agent context.

## 4. Apply the stack (order matters)

    kubectl apply -f 00-namespace.yaml
    kubectl apply -f 10-nats.yaml
    kubectl apply -f 20-temporal.yaml
    kubectl apply -f 30-litellm.yaml
    kubectl apply -f 40-langfuse.yaml
    kubectl -n estate rollout status deploy/nats deploy/temporal deploy/litellm deploy/langfuse

## 5. Expose via Cloudflare Tunnel (founder)

    cloudflared tunnel create estate
    # route: litellm.<domain> -> http://localhost:4000 (kubectl port-forward svc/litellm)
    # route: langfuse.<domain> -> http://localhost:3000 (kubectl port-forward svc/langfuse)

## Sizing budget (24 GB)

| service   | request | limit  | notes                                   |
|-----------|---------|--------|-----------------------------------------|
| nats      | 128 Mi  | 512 Mi | JetStream on, emptyDir (dev-grade)      |
| temporal  | 512 Mi  | 1 Gi   | auto-setup, in-memory sqlite (dev-grade)|
| litellm   | 256 Mi  | 1 Gi   | model-agnostic gateway — non-negotiable |
| langfuse  | 768 Mi  | 3 Gi   | web + postgres                          |
| kronos    | —       | —      | joins after chidionyema/kronos#2 merges |

Total request ~1.7 Gi — leaves ~20 Gi headroom for burst jobs.

## Dev-grade caveats (truth standard: configured != healthy != verified)

- emptyDir + sqlite = data dies with the pod. Fine for bootstrap; the durability
  lane (R2 backup, idp#7084) upgrades these to PVCs when sign-off lands.
- temporal auto-setup is not HA. One VM means nothing is HA yet — accepted for $0.
- ARM64: all images above publish arm64 manifests; verify with
  `docker manifest inspect <image>` before apply if a tag changes.
