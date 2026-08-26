/*
 * The estate, as a C4 model. This file is the model; every diagram is a VIEW of it.
 *
 * Why a model and not a picture: a picture goes stale the day after it is drawn and nobody
 * can tell. A model is one file, in git, that a command renders. Add a view five years from
 * now and you do not redraw the existing ones.
 *
 * Render:  make -C .. diagrams        (structurizr/cli in docker, no local install)
 * Output:  ../docs/architecture/*.mmd, committed, so GitHub and TechDocs render them
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
