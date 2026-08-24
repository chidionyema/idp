
.PHONY: diagrams
diagrams: ## Re-render the C4 views from architecture/workspace.dsl
	./architecture/render

.PHONY: cluster-up cluster-down cluster-status catalogue-deploy spire-up spire-status spire-proof
cluster-up: ## Create the local k3d cluster from platform/k3d/estate.yaml
	@k3d cluster list estate >/dev/null 2>&1 \
		&& echo "cluster 'estate' is already up" \
		|| k3d cluster create --config platform/k3d/estate.yaml
	@echo
	@echo "export KUBECONFIG=$$(k3d kubeconfig write estate)"
	@echo
	@$(MAKE) --no-print-directory bind-audit

catalogue-deploy: ## Build the catalogue image, import it into k3d, apply platform/backstage/overlays/local, port-forward 127.0.0.1:3100
	docker compose -f backstage/compose.yml build catalogue
	k3d image import idp/backstage:local -c estate
	KUBECONFIG=$$(k3d kubeconfig write estate) kubectl kustomize --load-restrictor LoadRestrictionsNone platform/backstage/overlays/local | KUBECONFIG=$$(k3d kubeconfig write estate) kubectl apply -f -
	KUBECONFIG=$$(k3d kubeconfig write estate) kubectl -n backstage rollout status deploy/catalogue --timeout=240s
	@echo "KUBECONFIG=$$(k3d kubeconfig write estate) kubectl -n backstage port-forward --address 127.0.0.1 svc/catalogue 3100:3100"

spire-up: ## Install SPIRE (spiffe/helm-charts-hardened) on the k3d cluster from platform/spire/values.yaml
	helm repo add spiffe https://spiffe.github.io/helm-charts-hardened/ >/dev/null 2>&1 || true
	helm repo update spiffe >/dev/null
	KUBECONFIG=$$(k3d kubeconfig write estate) helm upgrade --install spire-crds spiffe/spire-crds -n spire-mgmt --create-namespace
	KUBECONFIG=$$(k3d kubeconfig write estate) helm upgrade --install spire spiffe/spire -n spire-mgmt -f platform/spire/values.yaml --wait --timeout 10m

spire-status: ## Registered SPIFFE identities and attested agents
	@KUBECONFIG=$$(k3d kubeconfig write estate) kubectl -n spire-server exec statefulset/spire-server -- spire-server agent list
	@KUBECONFIG=$$(k3d kubeconfig write estate) kubectl -n spire-server exec statefulset/spire-server -- spire-server entry show | grep -E 'SPIFFE ID' | sort | uniq -c | sort -rn | head

spire-proof: ## A pod in the backstage namespace fetches its X.509 SVID from the Workload API (the receipt)
	@KUBECONFIG=$$(k3d kubeconfig write estate) kubectl delete -f platform/spire/proof.yaml --ignore-not-found >/dev/null
	@KUBECONFIG=$$(k3d kubeconfig write estate) kubectl apply -f platform/spire/proof.yaml >/dev/null
	@KUBECONFIG=$$(k3d kubeconfig write estate) kubectl -n backstage wait --for=condition=complete job/spiffe-proof --timeout=120s >/dev/null
	@KUBECONFIG=$$(k3d kubeconfig write estate) kubectl -n backstage logs $$(KUBECONFIG=$$(k3d kubeconfig write estate) kubectl -n backstage get pods -l job-name=spiffe-proof --field-selector status.phase=Succeeded -o name | head -1) | grep -E 'SPIFFE ID|Received|Valid'

cluster-down: ## Delete the local k3d cluster and everything in it
	k3d cluster delete estate

cluster-status: ## Nodes, pods, and what the cluster costs the machine
	@KUBECONFIG=$$(k3d kubeconfig write estate) kubectl get nodes,pods -A
	@echo
	@echo "-- docker VM memory (shared with every other container) --"
	@colima ssh -- free -m | sed -n 2p
	@echo "-- the cluster's own container --"
	@docker stats --no-stream --format '{{.Name}}\t{{.MemUsage}}\t{{.CPUPerc}}' k3d-estate-server-0

.PHONY: bind-audit
bind-audit: ## Fail if anything but the gateway is listening on a non-loopback address
	@bin/bind-audit
