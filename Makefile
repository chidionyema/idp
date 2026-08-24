
.PHONY: diagrams
diagrams: ## Re-render the C4 views from architecture/workspace.dsl
	./architecture/render

.PHONY: cluster-up cluster-down cluster-status catalogue-deploy
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
