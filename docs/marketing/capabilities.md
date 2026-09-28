# What we have: the capability register

Counted 2026-09-08 from `capabilities.yaml`. 50 capabilities in five ranges; 14 have a product page, 28 are surfaced nowhere; 29 are useful to a business buyer, 15 to both business and engineers.

The question each row answers, in the founder's words: is it useful for business and engineers? A row with an empty `useful_for` is a retirement candidate.


## Run AI agents: start, watch, steer and stop a workforce of agents

| capability | path | useful for | state today | surfaced |
|---|---|---|---|---|
| FleetView | `sovereign/cockpit -> backstage/plugins/fleetview` | business, engineers | cockpit built (37 tests) and not running; Backstage rebuild specced | page |
| Sovereign Bus | `sovereign/engine` | engineers | built (63 tests); worker moved to cluster 2026-08-28 | mention |
| Presence | `sovereign/presence` | business | built (5 tests); menu bar | none |
| Photo intake | `sovereign/intake` | business | built (5 tests); whiteboard photo to agent session | none |
| Shadow founder | `sovereign/shadow` | engineers | built (6 tests); branch racing and LoRA distillation | none |
| agent-foundry | `../agent-foundry` | business, engineers | built (25 test files); CLI and serve | none |
| crew | `../crew` | engineers | built (2897 test files); PM/Eng/QA roles on GitHub issues | mention |
| Cyrus | `platform/cyrus` | engineers | on cluster | mention |
| The Architect (hermes-v2) | `../hermes-v2` | business, engineers | on Mac and cluster (6082 test files) | mention |
| Otto Assistant | `sovereign/otto` | business | on cluster; five capabilities unfinished (audit v2 P6) | page |
| Agent Workforce + Research Engine | `../agent-workforce ../research-engine` | business, engineers | built; 38% of 2769 commits by bots | page |
| agent-guard | `../agent-guard` | engineers | built | none |
| maestro | `../maestro` | engineers | built (8 test files); no README | none |
| Hindsight recall | `platform/hindsight` | business, engineers | on cluster | mention |

## Govern AI agents: what an agent may reach, spend, sign and ship

| capability | path | useful for | state today | surfaced |
|---|---|---|---|---|
| MCP Gateway | `mcp platform/agentgateway` | engineers | on cluster | page |
| JIT token broker | `platform/jit` | business, engineers | on cluster (broker | none |
| Spend-bounded LLM Gateway | `platform/llm` | business, engineers | on cluster | page |
| Conscience | `conscience bin/idp-conscience` | business | built; CI and reports; no README | none |
| Intent compiler | `bin/intent-compile` | engineers | built; schemas and BDD; CLI and CI | none |
| Estate attach | `sovereign/attach` | engineers | built (10 tests); CLI | none |
| Hardware trust anchor | `sovereign/trust` | business, engineers | built (12 tests); Secure Enclave | none |
| popdd receipt chain | `../popdd-py ../popdd-ts` | engineers | publishable libraries (1 test file each) | none |
| Voice Gate | `platform/voice-gate` | business | built | page |

## Run the platform: the estate itself, secure, observed, sold as a managed deployment

| capability | path | useful for | state today | surfaced |
|---|---|---|---|---|
| The Platform | `.` | business, engineers | on cluster; 30 min install | page |
| Zero-Trust Boundary | `platform/calico platform/ns-fences` | business, engineers | on cluster | page |
| Secrets Bridge | `platform/secrets` | engineers | on cluster | page |
| estate-secrets vault | `../estate-secrets` | engineers | built | none |
| Compliance Pack | `policy bin/supply-chain` | business | built; CI gates | page |
| Inventory + Dual-Renderer | `bin/idp-inventory platform/inventory` | engineers | daily workflow green (assets | page |
| Self-healing | `platform/healing` | engineers | on cluster (k8sgpt | mention |
| Estate messaging bus | `platform/messaging` | engineers | Go module and NATS on cluster; no README | none |
| Sandbox clusters | `platform/sandbox` | business, engineers | on cluster (vcluster on a link); no README | mention |
| Screen access (Guacamole) | `platform/guacamole` | engineers | on cluster; no README | none |
| Private search (SearXNG) | `platform/searxng` | engineers | on cluster | none |
| Science lane | `platform/science ../crew/science` | business, engineers | built; 41 sources into SigNoz (DORA | none |
| Founder's estate view | `bin/estate-founder bin/idp-estate-view` | business | built; generated page and JSON | none |
| Estate clocks and diagram | `bin/estate-clocks bin/estate-diagram` | engineers | built; generated docs | none |
| Roadmap as a command | `bin/estate-next` | business | built; docs/NEXT.md | none |
| Portal buttons | `bin/idp-portal-buttons` | business, engineers | built; every workflow a Backstage button | none |
| Customer identity | `platform/customer-identity` | business | on cluster (Keycloak realm); no README | none |
| Metering and invoicing (Lago) | `platform/commerce` | business | on cluster; no README | none |
| Survival Stack | `../survival-stack` | business, engineers | built (5 test files); Cloudflare Worker | none |
| Vendor Key Activation | `platform/vendors` | business | built | page |

## Private AI: inference and models on hardware and keys you hold

| capability | path | useful for | state today | surfaced |
|---|---|---|---|---|
| Model Forge | `forge` | engineers | built | page |
| Edge Runtime | `platform/edge-runtime` | business, engineers | built | page |

## Products that run on the platform (a buyer buys these; the platform is what they run on)

| capability | path | useful for | state today | surfaced |
|---|---|---|---|---|
| Prospector engine | `../prospector-main` | business | on cluster (4050 test files) | mention |
| Storefront (paid packs) | `../prospector-main/store_platform` | business | deployed; Stripe money path proven (742 test files) | none |
| mumchimp storefront | `../mumchimp-medusa` | business | local only | none |
| pi-governance | `../prospector-main/pi-governance` | engineers | library | none |
| QAlgo | `../QAlgo` | nobody | stale since 2023; retire or archive | none |

Source of the rows outside the catalogue: a sweep of every repository under the dev root on 2026-09-08 (37 candidates), joined with the 13 catalogue products and FleetView. Test figures are test files, not passing runs.
