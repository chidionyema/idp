# Paying for her shopping: every option, and what a tooling company would actually ship

2026-09-11. Written because the last missing piece of the concierge was a card number we would
hold, and that turned out to be the wrong question. Sources are listed; where the evidence is weak
this says so rather than implying it.

## The question, restated the way a tooling company asks it

Not *"how do we get her card into our vault"* but *"what is the cheapest, safest, most durable way
for an agent to pay a merchant on her behalf, and which of the mechanisms available in 2026 should
we build on"*.

The answer changed twice while researching this.

## Option 1 — we hold the card. What is built today.

**What it is.** She gives us the number once; we store it encrypted under `CARD_KEY_HEX` as one
object per customer; the runtime decrypts it into a sandbox's memory for one order and the Rust vault
sidecar swaps it for a surrogate over CDP.

**Why it is defensible.** It works at **any** shop, including the ones with no API at all. The
vault means the model driving the browser never sees the digits. The keys are split so a leaked
profile key is not a leaked card.

**Why it is the weakest option on this list.** *We hold her card.* Under our key, in our bucket,
indefinitely. Every one of the controls above exists to make that fact survivable rather than to
remove it. The architecture's own sentence — "we never hold your card" — is not true in this option,
and the honest version is "we hold it under these specific protections".

**Verdict.** Keep it as the fallback for shops that offer nothing else. Do not build on it.

## Option 2 — Apple Pay. Asked about directly on 2026-09-11.

**What it is.** She confirms with Face ID on her own phone; the merchant receives a network token.

**Why it cannot be the mechanism.** There is no API that returns a card number, on any platform, to
any developer. The card is tokenised into a Device Account Number held in the Secure Element, and
the payment token is single-use, merchant-bound and expires in minutes — replaying one later is
precisely what it is designed to prevent. Reading the DPAN would require a jailbreak and would still
be useless without Apple's per-transaction cryptograms.

**And the merchant side does not hold either.** Tesco's own online grocery payment pages list Visa,
Mastercard, Amex, Maestro, Visa Debit, Clubcard Plus and Tesco Bank cards. **Apple Pay is not among
them.** Tesco Bank's Apple Pay page is about their *cardholders* using Apple Pay in other merchants'
apps and stores, which is a different thing and does not imply Tesco Grocery accepts it.

**Verdict.** Not available for the shop that matters most, and even where it is, it changes nothing
about our storage — it removes the need for it. See the recommendation.

## Option 3 — the Agentic Commerce Protocol (ACP). The one we should have looked at first.

**What it is.** An open standard maintained by **OpenAI and Stripe** for exactly this problem: an AI
agent completing a checkout on a user's behalf. Versioned REST API — `POST /checkout_sessions`,
update, retrieve, complete, cancel — with the merchant returning authoritative cart state on every
response, idempotency for safe retries, and webhooks. **Payments stay on the merchant's own rails.**

**What that means for us.** A merchant that speaks ACP has said *"agents may buy here"*. No browser,
no bot detection, no datacentre IP problem, no card in our vault. The hardest problem in this product
— being blocked by Akamai for looking like a robot — **does not exist on this path**, because the
merchant invited the agent in.

**Adoption, honestly.** Launched September 2025 with Etsy and Shopify. Google's competing Universal
Commerce Protocol followed in January 2026 with Walmart, Target and Shopify. UK adoption is around
**3% of transactions** and I could find **no evidence that a UK supermarket is a member.** Some
reporting says OpenAI pulled back its flagship in-chat checkout after weak sales, which is a caution
about the hype as much as about the protocol.

**Verdict.** Not usable today for her weekly shop, and this is the path the product should be
*shaped* for. It costs nothing to be ready: an ACP merchant integration is a checkout session, and
our runtime already has a place for one.

## Option 4 — delegated payment: one card, one purchase, scoped.

**What it is.** The issuer mints a **single-use virtual card per transaction**, scoped by amount,
merchant and context, with a mandate ledger linking the user's instruction to the agent's identity
and the credential's scope. Stripe's "Issuing for agents" and their Link wallet do this; Cross River
expanded their Stripe Issuing partnership for it in July 2026; Visa Intelligent Commerce and
Mastercard Agent Pay do the network-level version.

**Why this is the strongest option on the list.** It is the only one that removes the sentence we
cannot honestly say. She does not give us a card; **her bank issues a card for this purchase, for
this amount, to this merchant, once.** The number we would hold is worthless after the order, and
there is a mandate record showing she authorised it — which is also the answer to "how do you prove
an 82-year-old agreed to this".

**What it costs.** An issuing relationship, and the merchant must accept the card (they accept Visa
and Mastercard, so yes). It is real work and it is not free.

**Verdict.** This is the destination. It is the only option where "we never hold her card" is true
and stays true.

## What a tooling company ships, given all four

**Ship the layer, not the integration.**

Every mechanism above is a way of answering one question: *may this agent spend this much, at this
merchant, for this purchase, right now?* We have already built that question — `policy_engine`
decides the tier, the Guardian holds the red button, the ledger records what happened. What is
missing is that the answer is expressed as **a browser filling a form** rather than **a mandate
handed to a payment mechanism**.

So the shape is:

```
her request -> intent (the model) -> HER shops (preferences.py) -> the policy answer (tier, limit)
                                                                          |
                                          ---------------------------------
                                          |               |               |
                                    ACP session     delegated card    the browser
                                    (merchant       (one per order,   (the fallback,
                                     invited us)     scoped)           card in the vault)
```

Three mechanisms, one decision above them, and the decision is the product. That is a tooling
company's answer: the mechanism is a plugin, the authorisation is the asset.

**Concretely, and in order:**

1. **A `payment` seam** — one interface, `authorise(order) -> Mandate`, with three implementations.
   Today there is one implementation inlined into the browser path.
2. **Delegated cards first**, because they delete the vault's reason to exist for the shops that
   support them, and the mandate ledger is the evidence an adversarial diligence reader will ask for.
3. **ACP detection** — before driving a shop, ask whether it speaks ACP. A minute of work that skips
   the entire bot-detection problem where it is available.
4. **The vault stays** for shops that offer neither, and is honest in the docs about what it is:
   the fallback that keeps the product working everywhere, not the crown jewel.

## The one thing this research changes today

**Do not enrol a card into the vault as the primary path.** It was the last missing piece and it is
now the least durable of four options. The card-key work from this afternoon is not wasted — it is
the fallback implementation of a seam that should have existed from the start — but the next piece
of real work is the seam and the mandate, not the enrolment form.

## Sources

- Apple Pay Merchant Integration Guide, Apple — https://developer.apple.com/apple-pay/Apple-Pay-Merchant-Integration-Guide.pdf
- Apple Pay on the Web — https://developer.apple.com/documentation/applepayontheweb
- Tesco, cards accepted for online grocery — https://www.tesco.com/help/pages/online-grocery-faqs/payment-issues-and-information/credit-and-debit-cards-i-can-use
- Tesco Bank, using Apple Pay (their cardholders, not Tesco Grocery) — https://www.tescobank.com/help/apple-pay/
- Agentic Commerce Protocol, specification and RFC — https://github.com/agentic-commerce-protocol/agentic-commerce-protocol
- Agentic Checkout spec, OpenAI — https://developers.openai.com/commerce/specs/checkout
- ACP adoption table — https://agenticcommerceprotocol.info/adoption
- UK agentic commerce status, mid-2026 — https://ve3.global/blog/agentic-commerce-update-mid-2026-whats-actually-changed-and-what-it-means-for-retailers
- Consumer trust in agentic commerce — https://www.checkout.com/newsroom/consumer-demand-for-ai-shopping-is-forming-fast-but-trust-for-agentic-commerce-is-still-catching-up
- Stripe Issuing for agents — https://docs.stripe.com/issuing/agents
- Stripe, giving agents the ability to pay — https://stripe.com/blog/giving-agents-the-ability-to-pay
- Cross River and Stripe agent card payments, mandate controls — https://rzifi.com/blog/cross-river-stripe-agentic-card-mandate-controls/
