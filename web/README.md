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
| `CONTACT_WEBHOOK_URL` | yes | `https:` endpoint that receives the submission as JSON |
| `CONTACT_WEBHOOK_TOKEN` | no | sent as `Authorization: Bearer <token>` |

Nothing else changes when you change providers. With `CONTACT_WEBHOOK_URL` unset the route
returns **503** and logs — it refuses to accept a lead it cannot deliver, so a
misconfigured deployment looks broken rather than successful.

Payload shape:

```json
{
  "source": "meridian.ai/contact",
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
