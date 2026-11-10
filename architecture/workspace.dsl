/*
 * The estate, as a C4 model. This file is the model; every diagram is a VIEW of it.
 *
 * Why a model and not a picture: a picture goes stale the day after it is drawn and nobody
 * can tell. A model is one file, in git, that a command renders. Add a view five years from
 * now and you do not redraw the existing ones.
 *
 * Render:  make -C .. diagrams        (structurizr/cli in docker, no local install)
 * Output:  ../docs/explanation/architecture/*.mmd, committed, so GitHub and TechDocs render them
 *          without anyone installing anything.
 *
 * Decision: ../docs/decisions/0002-documentation-is-code-and-the-portal-renders-it.md
 */
workspace "Estate" "The platform, the products under it, and the substrate under both." {

    !identifiers hierarchical

    model {
        founder = person "Founder" "Does not use a command line (LAW 31). Reads the board, ticks the box (R16)."
        buyer   = person "Buyer's engineer" "Arrives with diligence. Takes apart anything half-stitched."
        agent   = person "Agent session" "Six of them, stateless, cannot see each other. Bound by ~/AGENTS.md."

        platform = softwareSystem "idp — the platform" "One of each layer. Products are onboarded onto it, they do not carry copies of it." {
            board    = container "Board" "GitHub Issues, chidionyema/crew" "STANDARDS row 27. R16 governance as checkbox rows; ticking a box is an act. Kanboard retired 2026-08-26 (crew#282)."
            portal   = container "Portal" "Backstage" "Service catalog and TechDocs. Renders the catalog and the docs; it does not discover them."
            gateway  = container "Gateway" "Gateway API v1.6.0 / Traefik" "One front door. No service publishes a host port."
            routing  = container "Model routing" "LiteLLM" "One model gateway with one budget."
            traces   = container "Traces and audit" "Langfuse" "Every model call in the estate lands here."
            secrets  = container "Secrets" "sops + age directory vault" "secrets/<env>/<name>.yaml, private repo, never a value in a log."
            sched    = container "Scheduling" "Dagster" "One scheduler. launchd is the substrate's supervisor, not the estate's scheduler."
            ci       = container "CI" "GitHub Actions" "The gate. A repo with no CI gets a gate before it gets a merge."
            catalog  = container "Catalog source" "idp/bin/catalog-gen" "Generates catalog-info.yaml from the LAW 39 inventory. Never hand-edited."
            docs     = container "Docs tree" "Markdown, Diataxis, MkDocs" "Lives beside the code it describes. Rendered by the portal."

            // --- The control plane: the parts that decide, gate and deliver. -----------
            // Every container below names the source it is derived from, so the diagram is
            // traceable to repository bytes rather than to a hand-drawn picture.
            greenlane = container "Greenlane" "greenlane/engine.py" "The gated trunk: a serial trunk that batches, bisects and lands a PR only when its required checks passed at that exact sha (I1)."
            spine     = container "Event spine" "spine/, spine/bridge.py" "The environment emits facts and an agent responds: Flux -> NATS JetStream -> the bridge -> Temporal -> a receipt."
            factory   = container "Factory" "factory/" "Collects the estate's capabilities into the registry the catalogue reads."
            census    = container "Census" "catalog/census/" "Runs the collectors, joins what they saw, and says what is missing: MANAGED or UNCATALOGUED with a reason."
            policy    = container "Operating model policy" "policy/operating_model.rego" "The estate-as-platform rules as a gate rather than a paragraph: the founder approves, agents implement."
            executor  = container "Executor" "catalog/critical-functions.json (executor)" "The executor daemon. Every agent's tool calls go through this door; without it no agent can run a command."
            bus       = container "Estate bus" "catalog/critical-functions.json (estate-bus)" "The event bus. State is streamed over it; without it the surfaces go stale and agents cannot be told what happened."
            memory    = container "Memory plane" "catalog/critical-functions.json (memory-plane)" "The estate's single memory plane: brief, recall, remember."
            lanes     = container "Critical lanes" "platform/ladder/critical-lanes.json" "The estate's critical lanes as data. A home is a failure domain: a place the service runs that can die without taking the others with it."
            probes    = container "Probes" "probes/" "What the drills assert, as code: the front door, the catalogue, Langfuse, Signoz, the backstages."
        }

        prospector = softwareSystem "prospector" "The product. Stays the product. Lives outside idp on purpose."
        hermes     = softwareSystem "hermes-v2" "A product."
        crew       = softwareSystem "crew" "Where the standards row and the estate snapshot live."

        founder -> platform.board "Reads. Ticks the box. Only he moves a card to LIVE."
        founder -> platform.portal "Reads what exists and what depends on what."
        buyer   -> platform.portal "Diligence starts at the catalog."
        agent   -> platform.board "Writes the Observation column and the two agent lanes. Never the approval column."
        agent   -> platform.ci "Opens the PR. The gate decides, not the agent."

        platform.gateway -> platform.portal "routes"
        platform.gateway -> platform.traces "routes"
        platform.gateway -> platform.routing "routes"

        platform.portal  -> platform.catalog "reads the generated entities"
        platform.portal  -> platform.docs    "renders via TechDocs"
        platform.routing -> platform.traces  "emits every call"
        platform.routing -> platform.secrets "reads provider keys"
        platform.sched   -> platform.ci      "triggers"
        platform.ci      -> platform.secrets "reads, never prints"

        // The control plane reads the catalog and the policy, and writes to the board.
        platform.greenlane -> platform.ci      "grades the PR; lands by squash only when green"
        platform.greenlane -> platform.board  "writes the observation, never the approval"
        platform.spine     -> platform.bus     "the fabric between the environment and the agent's clock"
        platform.factory   -> platform.catalog "collects the capabilities the catalogue publishes"
        platform.census    -> platform.catalog "joins what it saw against the catalogue"
        platform.policy    -> platform.greenlane "the rules the gated trunk enforces"
        platform.probes    -> platform.lanes   "measures each lane; the drill decides health"
        platform.lanes     -> platform.gateway "the published hostnames"
        platform.executor  -> platform.secrets "runs a command under scoped authority"
        platform.memory    -> platform.bus     "state is streamed, not polled"

        // The estate's own critical functions, as the registry names them.
        platform.routing -> platform.lanes "the lanes the running router serves"

        prospector -> platform.routing "every model call goes through the one gateway"
        prospector -> platform.traces  "every trace lands in the one collector"
        prospector -> platform.secrets "one vault"
        prospector -> platform.catalog "is an entity in the one catalog"
        hermes     -> platform.routing "same"
        hermes     -> platform.traces  "same"
        crew       -> platform.catalog "the standards row names the layer"

        deploymentEnvironment "Laptop — backup environment" {
            deploymentNode "MacBook" "darwin 23.5.0" "The substrate until k8s. Proves things work; it is not production." {
                deploymentNode "colima" "Docker engine" {
                    containerInstance platform.portal
                    containerInstance platform.routing
                    containerInstance platform.traces
                }
                deploymentNode "launchd" "Supervisor" "51 LaunchAgents. Supervises; does not schedule estate work."
            }
        }

        deploymentEnvironment "Cluster — production, being built" {
            deploymentNode "Kubernetes" "k3s or managed" {
                deploymentNode "Gateway API" "HTTPRoute, portable across 16 conformant implementations" {
                    containerInstance platform.gateway
                }
                containerInstance platform.portal
            }
        }
    }

    views {
        systemContext platform "Context" {
            include *
            autolayout lr
            description "Who touches the platform, and what sits beside it."
        }

        container platform "Containers" {
            include *
            autolayout lr
            description "One of each layer. The row in crew/docs/STANDARDS.md is the same list."
        }

        deployment platform "Laptop — backup environment" "Laptop" {
            include *
            autolayout lr
            description "What actually runs today, on the machine the founder is sitting at."
        }

        deployment platform "Cluster — production, being built" "Cluster" {
            include *
            autolayout lr
            description "Where it goes. Nothing here has been booted, and the diagram says so."
        }

        container platform "Control-path" {
            include platform.greenlane
            include platform.policy
            include platform.ci
            include platform.board
            include platform.executor
            include platform.bus
            include platform.memory
            include platform.spine
            include platform.factory
            include platform.census
            include platform.catalog
            include platform.probes
            include platform.lanes
            include platform.secrets
            include platform.gateway
            include platform.sched
            autolayout lr
            description "How one change reaches the board and the founder: the gated trunk, the rules it enforces, the gate it waits on, and the observation it may write. Every box names the source it came from."
        }

        styles {
            element "Person" {
                shape person
            }
            element "Software System" {
                background #1168bd
                color #ffffff
            }
            element "Container" {
                background #438dd5
                color #ffffff
            }
        }
    }
}
