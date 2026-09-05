# Otto's door gets hands and senses

**Executor:** DeepSeek, one branch on `chidionyema/hermes-v2`, one branch on `chidionyema/idp`.
**Reads:** this file only. Every path below is real on `hermes-v2` `origin/main` at `17aa95e`
and `idp` `origin/main`; nothing here is invented.
**Founder record:** `~/.claude/docs/founder/2026-09-05T2200Z-what-did-founder-request-9360268a.md`
("what we are building is not what the spec demanded", "audit everything", "just the spec").
**Tickets:** crew#768 CP2 (tool gateway with real tools), crew#773 CP2 to CP4 (voice in, voice
out, vision). Board boxes are ticked by a QA session on a green run, never by the executor.

## The one fact this spec fixes

Every Telegram message to Otto lands on the door: `otto/ingress/worker.py` `_handle` calls
`answer_envelope` in `otto/boot/pipeline.py`. That path holds a tool gateway with exactly one
registered tool, `note` (`build_registry`, `NOTE_TOOL_NAME`), and a provider client that sends
one user message with no `tools` field (`otto/router/providers.py` `LiteLLMClient.complete`).
The Telegram binding reads only `message["text"]` (`otto/surface/bindings/telegram.py`
`normalize`). So Otto has memory and a model, and no hands, no ears, no eyes.

The hands already exist in the same container image. The door runs
`ghcr.io/chidionyema/hermes-agent`, whose `Dockerfile` clones the fork into
`/app/hermes-agent` and installs the `otto` runtime into that venv. So from the door's process,
`import model_tools` and `import toolsets` work, and:

- `model_tools.get_tool_definitions(enabled_toolsets=[...])` returns the OpenAI-format tool
  list for 35 toolsets (`toolsets.py`: `terminal`, `web`, `search`, `skills`, `file`, `vision`,
  `tts`, `memory`, `code_execution`, `cronjob`, `todo`, `browser`, ... and the MCP servers named
  in `config.yaml` `mcp_servers`, which is how `estate` and `ask_holmes` arrive).
- `model_tools.handle_function_call(function_name, function_args, task_id=...)` runs one.
- `tools/transcription_tools.py` transcribes audio, local `faster-whisper` first (ADR 0022).
- `tools/tts_tool.py` speaks text. `tools/vision_tools.py` describes an image via the `gemini`
  alias (`config.yaml` `vision:` block, PR #86).

Nothing new is written that the fork already does. The work is a bridge, a loop, and three
fields in one binding.

## Non-negotiables

1. No bypass. Telegram stays on the door. The hermes-agent gateway pod is not touched.
2. No flag or feature is removed. ADR 0022: voice ON by default, flags kept, speech-to-text
   local first, cloud fallback second.
3. Every tool call passes `ToolGateway.call` (`otto/gateway/core.py`). No handler is invoked
   around it. Tiers: read-only tools T1; tools that write inside the pod or open a pull request
   T2; anything that cannot be undone T3 (`irreversible=True`), which the gateway routes to the
   human gate. The `[capabilities] destructive` list in `idp/AGENTS.md` (`fs_delete`,
   `git_push_force`, `db_drop`, `service_destroy`) is the T3 floor.
4. The router's lanes, budget and claims contract (`otto/router/core.py`, `contract.py`) are not
   modified. The tool loop lives inside the provider client, under the router.
5. Existing tests stay green and the new ones are BDD-shaped like `otto/tests/cp2/`. The suite
   is run first; `otto/tests/boot` currently errors on collection and that is fixed before any
   feature commit (`python -m pytest otto/tests -q` must print `0 errors`).
6. Provider agnostic: tool definitions and calls use the OpenAI `tools` / `tool_calls` wire
   shape LiteLLM serves for every alias on `llm.mumchimp.com`. No provider SDK is imported.

## Work, in order. Each step ends with its done-command.

### Step 1, hermes-v2: the bridge, `otto/gateway/bridge.py` (new)

`register_fork_tools(registry: ToolRegistry, *, enabled_toolsets: list[str]) -> int`

- Calls `get_tool_definitions(enabled_toolsets=enabled_toolsets)`; for each definition builds a
  `ToolSpec(name, tier, input_schema=parameters, handler, irreversible, idempotent)` and
  registers it. `handler` is a closure calling `handle_function_call(name, args, task_id=...)`
  and returning `{"result": <string>}`; the fork returns a JSON string, never raise it away.
- Tier map is a dict in the same file, keyed by tool name with a toolset fallback:
  T1: `web_*`, `search_*`, `vision_*`, `read_file`, `session_search`, `memory` reads,
  every MCP tool whose name starts with `estate` or `ask_holmes`.
  T2: `terminal`, `write_file`, `patch`, `skills_*`, `code_execution`, `cronjob`, `todo`,
  `tts`, `memory` writes.
  T3 and `irreversible=True`: `terminal` calls whose `command` matches
  `git push --force|rm -rf|kubectl delete|drop (table|database)|terraform destroy`. This is a
  per-call tier, so the bridge wraps `terminal` in a handler that inspects `args["command"]` and
  raises `otto.gateway.errors`-style denial through a second registered spec
  `terminal_irreversible` (T3). The loop routes a matching command to that spec.
- Capacity: `GatewayConfig.max_tools` is read from an environment variable in
  `otto/gateway/config.py`; set it high enough in the deployment (step 5).
- `build_registry()` in `otto/boot/pipeline.py` keeps `note` and then calls the bridge when
  `OTTO_TOOLSETS` is set (comma list). Default in the deployment:
  `terminal,web,search,skills,file,vision,tts,memory,todo,cronjob,code_execution`.
  Import of `model_tools` is inside the function so unit tests without the fork still run.

Done: `python -m pytest otto/tests/cp2 -q` green, plus a new
`otto/tests/cp2/test_bridge.py` proving: at least 30 tools registered from a stub
`get_tool_definitions`; a `terminal` call with `rm -rf /` is denied at T2 and reaches the human
gate at T3; an unknown tool name is `DenialReason.UNKNOWN_TOOL`.

### Step 2, hermes-v2: the loop, `otto/router/providers.py`

- `ProviderClient.complete` gains keyword arguments `tools: list[dict] | None = None` and
  `tool_executor: Callable[[str, dict], str] | None = None`, both defaulting to none so every
  existing caller and fake is unchanged.
- `LiteLLMClient.complete`: when `tools` is given, send `messages` as a list starting with
  `{"role": "user", "content": payload}` and the `tools` field. While the reply carries
  `tool_calls`, append the assistant message, run each call through `tool_executor`, append
  `{"role": "tool", "tool_call_id": ..., "content": result}` and call again. Stop at
  `OTTO_ROUTER_TOOL_MAX_TURNS` (default 12) or when the reply is text. Return the final text as
  `ProviderResult` with accumulated token counts. Every turn emits one observability line
  `router.tool_turn` with `tool=<name>` and elapsed milliseconds via the existing `ObsHandle`.
- `answer_envelope` builds `tool_executor` from the gateway: it makes a `GatewayEnvelope` with
  the task's `authority_ceiling` and `untrusted` flag, calls `registry_gateway.call`, and
  returns `output["result"]` or, on denial, the string `denied: <reason>` so the model tells the
  sender what it could not do instead of hallucinating that it did. Tool definitions passed to
  the model are only those whose tier is at or below the envelope's effective tier, so an
  untrusted sender never sees `terminal` exist.
- The `note` tool and the memory recall and retain steps stay exactly where they are.

Done: `otto/tests/cp5/test_tool_loop.py` (new): a fake provider that answers with one
`tool_calls` turn then text; asserts the gateway was called once, the final text is returned,
and a T3 call is denied and the denial text reaches the model. `python -m pytest otto/tests -q`
green.

### Step 3, hermes-v2: ears and voice, `otto/surface/bindings/telegram.py` and `otto/ingress/plugins.py`

- `normalize`: if `message["voice"]` (or `audio`) exists, fetch the file through
  `getFile` and the file URL with the bot token the plugin already resolves, write it to
  `/tmp`, call `tools.transcription_tools` (local faster-whisper first, then the configured
  cloud provider if `HERMES_LOCAL_STT_COMMAND` and the local model are absent). `content` is
  the transcript prefixed `[voice] `; the envelope carries `capabilities` including `VOICE_IN`
  and a new field `wants_voice_reply: bool = True` (ADR 0022 default ON; a chat-level flag can
  set it False, never removed).
- `TelegramPlugin.send_reply` gains `send_voice(secret, reply_to, text)`: synthesise with
  `tools/tts_tool.py`, then Telegram `sendVoice`. The worker calls `send_voice` when the
  inbound envelope was voice or the chat flag is on, and always also sends the text.
- Voice never authenticates (`otto/surface/identity.py` stays the law): trust comes from the
  chat-id allowlist exactly as today.

Done: `otto/tests/ingress/test_voice.py` (new): a Telegram update with a `voice` object and a
stub transcriber yields an envelope whose content is the transcript and whose capabilities
include `VOICE_IN`; the worker with a stub plugin calls both `send_reply` and `send_voice`.

### Step 4, hermes-v2: eyes, same binding

- `normalize`: if `message["photo"]` exists, take the largest size, download it the same way,
  and call `tools/vision_tools.py` with the caption (or "describe this") as the question. The
  description becomes `content` as `[image] <caption>\n<description>` so the router and memory
  see words, and the raw path is kept on the envelope for a tool that wants the pixels.

Done: `otto/tests/ingress/test_photo.py` (new): a photo update with a stub vision function
yields content containing the stub's description; `IMAGE_IN` is in capabilities.

### Step 5, idp: the door pod can authenticate what it now holds

`platform/otto-gateway/deployment.yaml`, `network-policy.yaml`, `kustomization.yaml`:

- Mount the same `hermes-agent-env` secret the agent mounts (`platform/hermes-agent/gateway.yaml`
  lines 53 to 85 define the ExternalSecret; copy it into the `otto-gateway` namespace as
  `platform/otto-gateway/agent-env.yaml`, same vault key, same transform, including
  `GITHUB_TOKEN`) at `/run/secrets/hermes-agent-env`, and set `HERMES_ENV_DIR` to it.
- Mount `ESTATE_MCP_KEY` the way `platform/hermes-agent/mcp-key.yaml` does.
- `HERMES_HOME=/data` on a persistent volume claim sized like the agent's `data` volume, so
  skills and the fork's own memory survive a restart.
- Environment: `OTTO_TOOLSETS` (default list from step 1), `OTTO_GATEWAY_MAX_TOOLS=256`
  (use the exact variable name `otto/gateway/config.py` reads), `OTTO_ROUTER_TOOL_MAX_TURNS=12`.
- NetworkPolicy egress: add `agentgateway.mcp.svc:3000` (estate MCP) and the same internet
  egress rule the `hermes-agent` namespace has for web search, `git push` and cloud
  speech fallback. DNS, event bus, database, memory and observability rules stay.
- Faster-whisper's model download on first use needs that egress too; pre-pull is not
  required, first voice note is allowed to be slow once.

Done: `bin/idp-ci` green; `kubectl -n otto-gateway get pod` shows the new revision `Running`
with restarts 0 for ten minutes; `kubectl -n otto-gateway exec deploy/otto-gateway -- sh -c
'ls /run/secrets/hermes-agent-env | wc -l'` prints more than 0.

## Proof, from the founder's phone, in the door's log

The system is not working until each line below is quoted from
`kubectl -n otto-gateway logs deploy/otto-gateway --tail=300` after a real message from the
founder's Telegram, and the reply arrived on the phone.

| founder sends | log must show | reply must contain |
|---|---|---|
| "what branch is hermes-v2 on and what changed in the last commit" | `router.tool_turn tool=terminal` then `worker.answered` | a real branch name and commit subject |
| "research the current faster-whisper release and tell me the version" | `router.tool_turn tool=web_search` (or `search_*`) | a version number with a URL |
| "which pods are not ready in the estate" | `router.tool_turn tool=estate*` or `ask_holmes` | pod names from the cluster |
| a voice note asking any of the above | `surface.voice_in` then a tool turn, then `worker.answered` and a `sendVoice` line | text and an audio reply |
| a photo of a terminal with caption "what is wrong here" | `surface.image_in`, `router.tool_turn tool=vision*` | an answer about the image content |
| "delete the otto-gateway deployment" | `gateway.denied reason=human_gate` (T3) | a sentence saying it needs confirmation, and nothing deleted |

The `kubectl get events -n otto-gateway` output during those six messages shows no restart, no
OOM. Then, and only then, a QA session ticks crew#768 CP2 and crew#773 CP2, CP3, CP4.

## Out of scope, and said so

Verification plane wiring (crew#768 CP3), memory hygiene job (CP4), chaos pass and weekly
digest (CP6), constitution suite (CP7). Each is its own spec after this one lands. Nothing
here makes them harder.
