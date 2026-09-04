# The Anthropic credential moves to Workload Identity Federation, and the router is what blocks it

2026-09-04. The founder, reading the Anthropic console while minting a replacement key: "With
identity federation, you don't need an API key ... Nothing to store in env vars, config files, or
secret managers. Tokens rotate automatically and expire in minutes." He is right, it is exactly what
LAW 52 asks for (one root per provider, code mints the rest), and this record says where it lands
and why it is not landed today.

## What the vendor offers

Anthropic's Workload Identity Federation takes a signed JWT from an issuer we already run, verifies
it against a federation rule in the Claude Console, and returns a short-lived `sk-ant-oat01-...`
token bound to a service account. The exchange is `POST /v1/oauth/token`, RFC 7523 jwt-bearer. The
supported issuers include AWS, Google Cloud, Microsoft Entra ID, Okta, GitHub Actions, **and
Kubernetes** — so in principle the LiteLLM pod could present its own projected service-account token
and this estate would hold no Anthropic key at all.

## Why the estate still holds one

**The router cannot do the exchange.** Every claude lane's credential lives in `litellm-upstream`
and is read by LiteLLM, and LiteLLM has no Anthropic WIF support: BerriAI/litellm#28607, "Support
Anthropic Workload Identity Federation (OIDC JWT-bearer token exchange)", is an open feature
request, not a shipped feature. Until it ships, a static key in the vault is the only thing the
router can authenticate with, and writing our own token-refresher beside the pod would be exactly
the stitched half-solution the headline forbids — the mature tool is the router, and the router's
answer is "not yet".

**GitHub Actions federation has no consumer here.** The one place CI touches the Anthropic
credential is `oke-check.yml` line 269, which passes `SEED_ANTHROPIC_API_KEY` to
`bin/idp-bootstrap-vendors` so it can be verified and written to the vault for the router. That job
is not calling the model API to do work; it is delivering the long-lived credential the router
needs. A short-lived token cannot be delivered — it expires in minutes — so federating that job
would authenticate a step that never needed authenticating, and leave the key exactly where it is.
No other workflow and no script under `bin/` calls `api.anthropic.com`.

## The decision

Keep `SEED_ANTHROPIC_API_KEY` as the router's credential for now, and move to federation the moment
the router can use it. The target is the Kubernetes issuer, not GitHub Actions: it removes the key
from the vault entirely rather than moving it one hop. Tracked so it is not forgotten when
litellm#28607 lands.

The estate has done this once before and the shape is the same — decision 0010 replaced the
Tailscale operator key with a federated identity and left the seed road in place for the case
federation could not reach. This is that case, on the other side of the fence.

## What does not change

Federation authenticates; it does not fund. On 2026-09-04 the router answered
`POST /anthropic/v1/messages` with `400 Your credit balance is too low to access the Anthropic API`
while the key was structurally valid. A federated token from a service account in an organisation
with no credit fails identically, so billing is a separate check on the organisation the rule
targets, whichever road the credential travels.
