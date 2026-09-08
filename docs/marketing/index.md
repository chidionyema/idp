# The catalogue — what we sell

This is the buyer's index to every product, feature and bundle the estate ships.
Every page below follows the same shape: the problem first, what you get, how it
works, why us, pricing, and how to start.

The full register of everything built, product or not, with who it is useful for: [capabilities.md](./capabilities.md).

## Products

| Product | What it is | Tier |
|---|---|---|
| [The Platform](./products/platform.md) | The whole IDP, sold as a managed deployment | Strategic |
| [FleetView](./products/fleetview.md) | One live board for every AI agent you run, with stop/approve/steer from the page | 2 weeks |
| [Voice Gate](./products/voice-gate.md) | Deterministic prose linter for house voice | Ship now |
| [Otto Assistant](./products/otto-assistant.md) | A personal agent that lives in your chat | Ship now |
| [Inventory + Dual-Renderer](./products/inventory-dual-renderer.md) | One source, two renderers, runtime-separated fallback | Ship now |
| [MCP Gateway](./products/mcp-gateway.md) | One policed door for every tool an agent can reach | 90 days |
| [Spend-bounded LLM Gateway](./products/llm-gateway.md) | An LLM router that cannot lose you money | 90 days |
| [Model Forge](./products/model-forge.md) | A tiny-model factory for narrow tasks | 90 days |
| [Edge Runtime](./products/edge-runtime.md) | Private inference on cheap hardware | 90 days |
| [Zero-Trust Boundary](./products/zero-trust.md) | Calico policy-only, audit-first enforcement | 6 months |
| [Secrets Bridge](./products/secrets-bridge.md) | Bitwarden bridges to OCI Vault for workloads | 6 months |
| [Compliance Pack](./products/compliance-pack.md) | SBOM + license + placement gates as a CI image | 6 months |
| [Agent Workforce + Research Engine](./products/agent-workforce.md) | Self-hosted engineering operations automation | 6 months |
| [Vendor Key Activation](./products/vendor-key-activation.md) | A vendor pastes one key; the platform does the rest | 6 months |

## Bundles

A bundle is what we sell when one product alone is not the story. Every bundle is
cheaper than the sum of its parts and tells a single, end-to-end story a buyer can
take to their board.

| Bundle | The story the buyer tells their board |
|---|---|
| [AI-Safe Portal](./bundles/ai-safe-portal.md) | "We shipped AI to production in week 4, with every call traced, every action governed, every $ capped, every voice reviewed." |
| [Private Inference Stack](./bundles/private-inference.md) | "We pay frontier rates for judgment, cents per hour for narrow classification, and we hold the artifacts." |
| [Compliance-as-Code](./bundles/compliance-as-code.md) | "What runs, in whose pocket, with what licenses, with what CVEs, on a clock." |
| [Zero-Trust Estate](./bundles/zero-trust-estate.md) | "Every pod's traffic is enforced by the network; every tenant is in its own lane; every drill proves the SLO." |
| [Engineering Operations Automation](./bundles/eng-ops.md) | "Linear tickets turn into PRs without a person; CI red turns into triage without a person; research runs on a clock without a person." |

## How to start

Every product above has three ways in:

1. **Run the install wedge** — a single image, `idp/quickstart`, that runs the
   platform on a fresh k3d cluster in 30 minutes. The drill is the demo; the
   screenshot is the case study.
2. **Read the showcase** — `/showcase` on the install wedge renders the live
   estate bar, the per-system health donuts, and the buyer sandbox launch
   button. The showcase is the page a buyer's engineer opens first.
3. **Call us** — for the platform itself, for the bundles, and for any product
   that needs a tenant, a SOC 2 conversation, or a procurement-grade security
   one-pager.

The drill runs hourly. The receipts land in the collector. The case study is
the dogfood chain: we ship every product here because we use every product here.
