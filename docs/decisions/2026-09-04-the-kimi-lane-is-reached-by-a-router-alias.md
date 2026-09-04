# The Kimi lane is reached by a router alias

2026-09-04. The founder added Kimi to the estate router himself, through the LiteLLM console,
and the proxy now serves it. Probed from inside the `litellm` pod at 05:47Z:

```
models: claude claude-fast deepseek deepseek-or embed gemini gemini-or image image-or
        minimax minimax-or minimax_m27 moonshot/kimi-k3 openrouter vision

moonshot/kimi-k3   HTTP 200   30.5s   completion 1049 tokens, 1030 of them reasoning
text: 'kimi is live'
```

Two things follow from that, and this record settles both.

## The name

The lane is served as `moonshot/kimi-k3`. Asking the router for `kimi` returns HTTP 400,
`Invalid model name passed in model=kimi`. Leaving it there would put a vendor path into every
caller that wants the lane, so the day Moonshot ships k4 the rename is a change in several
repositories rather than one line here.

The fix belongs at the router, and it is an alias rather than a model row:

```yaml
router_settings:
  model_group_alias:
    kimi: moonshot/kimi-k3
```

A `model_list` row would lock the name `kimi` in the config file, and the console would then
refuse to attach a key to it — "defined in config" — which is exactly the failure the founder
hit on 2026-09-03 and the reason `platform/vendors/consoles.yaml` carries a kimi vendor row
with no `router:` block (R75). An alias declares no model and holds no credential, so it locks
nothing. The lane stays console-owned; only its short name is now stable.

Both rendered configs come from `bin/idp-vendor-render`, so the change is made in
`llm/config.base.yaml` and `platform/llm/config.base.yaml` and rendered.

## The completion budget

This is a reasoning model. It spent 1,030 tokens thinking to produce three words, and the same
lane asked with a 200-token cap returned an empty string — the whole budget went on thought and
nothing was left for output. Otto's boot lane asks the model for a JSON object, so a truncated
completion is not merely short, it is unparseable, and it reaches the founder as "the model
replied in a shape I refuse to parse".

That half is fixed in `hermes-v2`, where `LiteLLMClient` capped every completion at 2000 tokens
with no deployment override: the cap is now `OTTO_ROUTER_MAX_TOKENS`, default 8192.

## What is still open

30.5 seconds for a short answer is a long silence on a chat surface. Nothing here streams yet,
so a caller pointed at this lane waits with no signal. That is worth fixing before Otto's
default lane is moved onto Kimi; today it stays on `minimax`, which answered the same probe in
a few seconds.

Source for the consultation that prompted this work:
`~/.claude/docs/founder/2026-09-04T0545Z-lan-elite-pro-like-a-staff-engineer-or-b6b9da66.md`.
