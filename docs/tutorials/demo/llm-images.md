# Demo: asking the router for a picture

Two lanes, because the founder asked for two (2026-08-30): "we test with
MiniMax see what the image quality is like, then we use Gemini for the ones
that will ship to production". Both are on the estate router, so nothing that
wants a picture ever holds a vendor key.

## The test lane

MiniMax's image endpoint is not OpenAI-shaped, so the router forwards the
vendor's own request body and puts the key in the header on the way past. You
send exactly what MiniMax documents, to the router, with a router key:

```
$ curl -sS https://llm.<zone>/minimax/image \
    -H "Authorization: Bearer $ROUTER_KEY" \
    -H 'content-type: application/json' \
    -d '{"model":"image-01",
         "prompt":"Wide editorial header illustration for a business research
                   storefront. Flat vector geometry, generous negative space,
                   muted deep slate blue, warm sand, one amber accent.
                   No text, no letters, no logos, no faces.",
         "aspect_ratio":"21:9","n":1,"response_format":"base64"}' \
  | jq -r '.data.image_base64[0]' | base64 -d > header.jpg
```

Four of these were run against four real sectors from the pack facets on
2026-08-30 and the images went to the founder. One measured defect worth
knowing before you trust a batch: one of the four invented shop signage
reading "Pxling" although the prompt bans text. Check output before shipping
it; the prompt is a request, not a constraint the model enforces.

## The shipping lane

Gemini is a first-class lane, so it is an ordinary model call and the caller
names a capability, never a vendor:

```
$ curl -sS https://llm.<zone>/v1/images/generations \
    -H "Authorization: Bearer $ROUTER_KEY" \
    -H 'content-type: application/json' \
    -d '{"model":"image","prompt":"...","n":1}'
```

Right now that lane answers with an upstream error, and the reason is money,
not configuration. Measured 2026-08-30 against the live key, on every Google
image model:

```
429 RESOURCE_EXHAUSTED
"Your prepayment credits are depleted. Please go to AI Studio ... to manage
 your project and billing."
```

The key itself is live: the same key lists all six image models with a 200.

The same model is also bought through OpenRouter as the lane `image-or`, and
`image` falls back to it, so funding either account brings the shipping lane
back. On 2026-08-30 both were empty at once — OpenRouter answered
`total_credits 10` against `total_usage 10.17171079` — which is why the pair
exists rather than one route. Until one of them has money, use the test lane
and expect the shipping lane to fail loudly rather than quietly returning
something worse.

## What proves it

```
$ python3 -m pytest tests/test_image_lane.py -q
.....                                                             [100%]
5 passed in 0.25s
```
