# Onboarding: the router's image lanes

## What it is for

Making a picture, from anything in the estate, without that thing holding a
vendor key. Before this the router had no image lane at all — the `vision`
row reads an image and does not make one — so the only ways to get a picture
were to put a vendor key in a workload or to go without. The first breaks the
rule that the router is the one door to a model; the second is why the
storefront has no category headers.

There are two lanes because the founder split them: MiniMax to judge quality
cheaply, Gemini for anything that ships.

## Where it lives

`platform/llm/config.yaml`, which is the LiteLLM configuration the cluster
reconciles. The shipping lane is the `model_list` row named `image`, with
`image-or` behind it: the same Google model bought through OpenRouter, so one
empty account does not take pictures off the estate the way it took `embed`
off on 2026-08-30. The test lane is a `pass_through_endpoints` route at
`/minimax/image` in
`general_settings`, and it is shaped differently for a vendor reason rather
than a preference: LiteLLM has no MiniMax image provider, and OpenRouter does
not resell one either — every MiniMax model it lists is text-output only. The
vendor's own endpoint is the only door, so the router forwards it.

Both read their key from the mount the ExternalSecret fills. Neither key is
written down in the configuration, and `tests/test_image_lane.py` fails if one
ever is.

## What it costs

Nothing standing: no new workload, no new pod, no new schedule. Per-image
spend comes out of the ceiling the whole router already lives under,
`max_budget` in `general_settings`, so a runaway caller stops at the same
place every other lane stops. One caveat on the numbers you will see in
tracing: the Gemini image model is newer than this LiteLLM's price map, so
calls on that lane trace at zero cost until the map catches up. Zero there
means unpriced, not free.

## How to stop it

Delete the rows, or the route, from `platform/llm/config.yaml` and let Flux
reconcile. Nothing else in the estate depends on any of the three yet. The one
chain that names them holds image models only, and must keep doing so: a
fallback out of an image lane into a text model answers a picture request with
prose, which looks like an answer and is worse than a clean failure.
