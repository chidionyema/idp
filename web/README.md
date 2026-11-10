# Merdian Intelligence — web

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
| `CONTACT_WEBHOOK_URL` | yes | `https:` endpoint that receives the submission as JSON |
| `CONTACT_WEBHOOK_TOKEN` | no | sent as `Authorization: Bearer <token>` |

Nothing else changes when you change providers. With `CONTACT_WEBHOOK_URL` unset the route
returns **503** and logs — it refuses to accept a lead it cannot deliver, so a
misconfigured deployment looks broken rather than successful.

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

### Pre-domain email activation

Merdian can accept enquiries **before incorporation and before a dedicated domain is purchased**.
The contact route now supports native Mailjet Send API v3.1 without an intermediary
webhook service. Configure `MAILJET_API_KEY`, `MAILJET_SECRET_KEY`,
`MERDIAN_ENQUIRIES_FROM`, and `MERDIAN_ENQUIRIES_TO` as Vercel secrets
in Production. Mailjet must verify the exact sender address first; for the
pre-domain period this can be an existing address the founder controls.
Do not publish fictional `@merdian...` addresses. No public code or DNS changes
are needed to activate this delivery path.

Priority: existing `CONTACT_WEBHOOK_URL` if configured, otherwise Mailjet,
otherwise the existing dedicated Telegram bot + chat configuration.
On non-2xx responses or a Mailjet per-message rejection the endpoint fails closed.
A successful Mailjet API response means provider acceptance, **not inbox delivery**.
`GET /api/contact` reports configured transport, not verified inbox receipt.
After the Vercel environment variables are configured, redeploy the approved
premium artefact, submit a real test enquiry and inspect its arrival in the
target inbox. This verification is mandatory before calling lead capture live.

When the registered domain is acquired: connect it to this same Vercel project,
verify ownership and DNS, provision the real inbox, set SPF/DKIM/DMARC, verify
the new Mailjet sender, replace only `MERDIAN_ENQUIRIES_FROM` and
`MERDIAN_ENQUIRIES_TO`, then switch the canonical site URL and redirect aliases.
Update the legal footer and company number only once Companies House issues
the certificate of incorporation.

### Known limits

- The rate limiter (5 per 10 min per IP) is **per process**. Behind N instances a caller gets
  `5 × N` attempts, and a restart forgets everyone. Fine for form spam; not fine for anything
  billed. Move the counter to Redis or the platform edge before this protects a paid path.
- `clientKey` trusts `x-forwarded-for`. That is correct behind a proxy that sets it and
  spoofable if the app is reachable directly.

## Corporate identity and release model (founder 2026-11-09)
Merdian Intelligence is the parent AI laboratory and product company. Mumchimp is a group company; Genesis is a lab and operating product. Research and prototypes are not production proof.

Legacy Meridian DNS / contact deployment settings remain compatibility inputs while Merdian's canonical domain is verified. Do not claim meridian.ai belongs to Merdian or invent an email address. The contact form fails closed if no delivery endpoint exists. Previously unsubstantiated numerical case studies remain in the source for evidence review but are no longer rendered as customer proof.

Release checks: web CI typecheck, voice, lint, unit, build, smoke; independent review of brand, DNS, provider configuration, accessibility and actual customer interaction.
