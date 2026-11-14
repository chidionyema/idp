# Meridian Intelligence — web

Next.js 14 App Router. Content lives in `content/`; pages in `app/`.

## Gates

Every one of these runs in CI (`.github/workflows/web.yml`) and none of them is advisory.

```bash
npm run typecheck   # tsc --noEmit
npm run voice       # VOICE.md rules; also runs inside `npm run build`
npm run voice:self-test  # proves the voice gate can fail
npm run lint        # next lint --max-warnings 0
npm test            # contact domain logic (validation, rate limit, delivery config)
npm run build       # voice-lint && next build
npm run test:smoke  # boots a production server and probes every route
npm run verify      # all of the above, in order
```

`npm run test:smoke` needs a build first; it starts its own server on port 3111 rather than
reusing a running one, because the contact endpoint keeps its rate-limit counter in memory.

## Contact form delivery

The form posts JSON to `/api/contact`. Delivery is provider-agnostic: set

| Variable | Required | Meaning |
|---|---|---|
| `CONTACT_WEBHOOK_URL` | one of two | `https:` endpoint that receives the submission as JSON |
| `CONTACT_WEBHOOK_TOKEN` | no | sent as `Authorization: Bearer <token>` |
| `TELEGRAM_BOT_TOKEN` | one of two | bot token for a delivery channel that is a chat rather than a webhook |
| `TELEGRAM_CHAT_ID` | one of two | the chat that receives the submission |

Configure the webhook pair or the Telegram pair. With neither set the route
returns **503** and logs — it refuses to accept a lead it cannot deliver, so a
misconfigured deployment looks broken rather than successful. `GET /api/contact`
reports the same state as `{"acceptingEnquiries": false}`, and the form uses it
to show an honest no-delivery state before anyone types.

Payload shape:

```json
{
  "source": "merdian-intelligence/contact",
  "received_at": "<ISO 8601>",
  "name": "...",
  "email": "...",
  "company": "...",
  "message": "..."
}
```

### Known limits

- The rate limiter (5 per 10 min per IP) is **per process**. Behind N instances a caller gets
  `5 × N` attempts, and a restart forgets everyone. Fine for form spam; not fine for anything
  billed. Move the counter to Redis or the platform edge before this protects a paid path.
- `clientKey` trusts `x-forwarded-for`. That is correct behind a proxy that sets it and
  spoofable if the app is reachable directly.

## Model roster and pricing

`content/models.ts` is the single roster behind the cost calculator, the routing playground
and the playground endpoint, so a price cannot drift between the three. Every rate is a
published list price per 1M tokens, read from the provider's own rate card. The date those
rates were last checked is exported as `pricingChecked` and printed on both tool pages.

When a provider retires or deprecates a model, remove it from the roster in the same change
that notices it. A customer who picks a model from this site and then gets an error from the
API has been misled.

## Privacy

`/privacy` is the customer-facing notice for the enquiry form. It names the controller
(Meridian Intelligence Limited, registered in England and Wales no. 16486712), what the form
collects, the lawful basis, the retention period and the processors. Change it in the same
change that changes what the form asks for.

## Corporate identity and release model (updated founder instruction 2026-11-11)
Meridian Intelligence is the parent AI laboratory and product company. Mumchimp is a group company; Genesis is a lab and operating product. Research and prototypes are not production proof.

Legacy Meridian DNS / contact deployment settings remain compatibility inputs while Meridian's canonical domain is verified. Do not claim meridian.ai belongs to Meridian or invent an email address. The contact form fails closed if no delivery endpoint exists. Previously unsubstantiated numerical case studies remain in the source for evidence review but are no longer rendered as customer proof.

Release checks: web CI typecheck, voice, lint, unit, build, smoke; independent review of brand, DNS, provider configuration, accessibility and actual customer interaction.

Public brand spelling: **Meridian Intelligence**. The older Merdian public spelling is deprecated. Existing `MERDIAN_SITE_URL` and `MERIAN_SITE_URL` env names remain backward-compatibility inputs; set `MERIDIAN_SITE_URL` for new deployments. The canonical currently configured Vercel alias is `meridian-intelligence-uk.vercel.app`, pending a verified owned domain.
