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

## What the estate has and lacks for this spec, measured 2026-09-05 22:20Z

Measured through `bin/idp-kube` and Otto's own router key (`otto-gateway-router`), not assumed.

| need | state | what to do |
|---|---|---|
| a model that calls tools through the router | `deepseek` (the judgment lane) and `minimax` both returned a `terminal` tool call with Otto's key; `gemini` did not | nothing; the judgment lane is already the tool lane |
| git with credentials | `git` in the image; `GITHUB_TOKEN` in `hermes-agent-env` answers 200 on the repo permission endpoint | step 5 mounts the same secret on the door |
| speech-to-text, local first (ADR 0022) | `faster_whisper` and `ffmpeg` present in the image; nodes are arm64, 5.8 CPU and 20 GB each, so the `small` model runs on CPU | step 3 uses it; first note downloads the model once |
| speech-to-text, cloud fallback | no Groq, OpenAI, ElevenLabs or Mistral key exists in the vault | do not add a provider: the fallback is `gemini` through the router, which accepts audio in a chat message. No new key, no console step (R52) |
| text-to-speech | `edge_tts` present, no key needed; needs internet egress | step 5 egress rule |
| vision | `gemini` alias, proved in hermes-v2 PR #86 | step 4 |
| estate queries | `ESTATE_MCP_KEY` projected in `hermes-agent`, absent in `otto-gateway` | step 5 |
| state that survives a restart | storage class `oci-bv`, agent has a bound 5 GiB claim, the door has none | step 5, a claim for `HERMES_HOME` |
| a sandbox for the terminal | none; the fork's `code_execution` wants a container runtime the pod does not have, and `terminal` today would run inside the pod that holds the secrets | step 6 below, and `code_execution` is left out of `OTTO_TOOLSETS` until it lands |

## Step 6, the sandbox: a terminal that cannot reach the secrets (crew#768 CP2, sandbox row)

The highest standard is that a model-driven shell never runs in the process that holds the
bot token, the database password and the GitHub token. So `terminal` executes as a
Kubernetes Job in a `otto-sandbox` namespace: same image, a 5 minute deadline, no secrets
mounted, the founder's repositories cloned read-write on an ephemeral volume with a
short-lived token minted per task (GitHub App installation token, 1 hour, repository-scoped;
the app is the one root, R52), egress only to `github.com` and the estate router. The door
submits the Job through the Kubernetes API with a namespaced service account that can create
Jobs and read their logs and nothing else; the gateway's audit line carries the Job name. The
`otto-sandbox` namespace gets the both-ways default-deny, quota and limit range every
namespace must carry (`ns_fence_gate`). Reads that do not need a shell (`web`, `search`,
`vision`, `estate`) stay in-process.

Done: `bin/idp-ci` green with the new namespace; from the phone, "run `ls -la /run/secrets`
in the terminal" answers with an empty directory and the door's log shows
`gateway.call tool=terminal job=<name>`.

## Step 7, what a 2026 assistant does that neither ticket names

- **Typing and progress.** Telegram `sendChatAction typing` the moment a task starts, and for
  a task past 8 seconds a single progress message edited in place ("reading the repo",
  "searching", "writing"), never a stream of messages. `otto/boot/presence.py` is the seam.
- **Long tasks do not block the phone.** A tool loop past 60 seconds keeps running; the door
  answers "on it, I will send the result" and the worker sends the result when it lands. NATS
  already carries the task; the worker acknowledges early and publishes the result on the
  task's own subject.
- **Interrupt.** A second message from the founder while a task runs is delivered to the loop
  as a user turn, so "stop" stops and "also check the logs" adds to the task.

Done: the progress edit and the deferred result are each quoted from the door's log on a
real task from the phone; a "stop" message ends a running loop within one tool turn.

## Step 8, conversation: the door remembers the last thing you said

Measured: `answer_envelope` sends the model one user message made of the contract prompt, the
recalled memory and this message (`_prompt_for`, `_with_memory`). No earlier turn is in it.
The door has no session transcript at all; only what pgvector recall happens to surface. That
is the "awkward" the founder feels: Otto cannot answer "and the second one?" because it never
saw the first. The fork's gateway keeps a full session (`config.yaml` `max_turns: 90`,
compaction at 150k tokens) and the door threw that away.

- A `conversations` table in the door's Postgres (`otto/ingress/pg_store.py` owns the
  connection): one thread per principal, not per surface, so the same thread continues
  from Telegram to the portal to a voice session (crew#773, "follows the conversation on every
  surface"). Columns: thread id, principal, surface, role, content, tool name, created at.
- The provider call sends `messages` as the last N turns of that thread (N by token budget,
  `OTTO_ROUTER_THREAD_TOKENS`, default 24k), then the recalled memory as a labelled context
  block, then this message. Tool turns from step 2 are stored too, so "run it again" works.
- Compaction: past the budget the oldest turns are summarised by the bulk lane into one
  stored summary turn, the fork's own rule at a smaller size. Nothing is deleted; the raw
  turns stay in the table for the memory hygiene job.
- A thread idles out after `OTTO_THREAD_IDLE_HOURS` (default 12); "new topic" from the
  founder starts a fresh one. An untrusted sender gets a thread of their own, never the
  founder's.
- The memory retain step keeps writing facts to pgvector exactly as today; the thread is
  short-term, memory is long-term, and the two are not merged.

Done: `otto/tests/cp4/test_thread.py` (new): three envelopes from one principal produce a
provider call whose `messages` holds the earlier two turns; a fourth from another principal
holds none of them. From the phone: "what is the second file you listed" answers correctly
after a listing, quoted from the door's log with `router.thread_turns=<n>`.

## Step 9, every surface: what was designed, what the fork already carries, what to enable

Measured: the door has two bindings, `telegram.py` and `http.py` (a pure normaliser for the
companion app's socket, nothing listening yet). `otto/surface/adapter.py` names web, Slack,
email, a voice session and a glasses card as the designed surfaces; none exists. The fork
ships transports for WhatsApp Cloud, Signal, iMessage (BlueBubbles), Microsoft Graph (Teams
and Outlook mail), a generic webhook and an API server, and `config.yaml` enables Telegram
alone.

The binding rule stays: a surface is one normaliser in `otto/surface/bindings/` producing the
same `SurfaceEnvelope`, one plugin in `otto/ingress/plugins.py` that can `send_reply` (and
`send_voice` where the surface has audio), and one row in the channel binding store. The
transport is the fork's platform adapter, never rewritten. Everything past the envelope is
the same code as Telegram, so a surface is one file and one row, and it inherits hands,
senses and the thread of step 8.

In order, each its own pull request, each proved by a message from the founder on that
surface quoted from the door's log:

1. **Backstage portal chat** (crew#758, "Backstage is the one door"): the `http.py` binding
   goes live behind the gateway's OIDC as `POST /surface/web` and the portal's Otto entity
   page gets the chat panel. Same principal as Telegram, same thread.
2. **Slack** (crew#682): Slack is the machine alert channel. Otto reads the alert channel
   and answers a thread when addressed; the founder can say "look at this" under an alert.
   Fork adapter: the generic webhook with Slack's event payload; the normaliser maps the
   Slack user to the principal allow-list.
3. **WhatsApp** (fork `whatsapp_cloud`, ready): the founder's second phone channel and the
   first customer-facing one, tenant-scoped (ADR 0021, two hats).
4. **Email** (fork `msgraph_webhook`): an email to Otto's address is a message; the reply is
   an email in the same thread.
5. **Voice session** (crew#773 CP3 beyond notes): a Telegram call or a web microphone
   stream, speech-to-text local first, the same thread; the glasses card (crew#770) is a
   read-only render of the thread's last turn and lands with it.

Done for each: the binding's test in `otto/tests/ingress/`, the row seeded by
`platform/otto-gateway/binding-seed.yaml`, and the log line `worker.answered channel=<name>`
for a real message from the founder on that surface.

## Out of scope, and said so

Verification plane wiring (crew#768 CP3), a red-team pass on the sandbox, memory hygiene job (CP4), chaos pass and weekly
digest (CP6), constitution suite (CP7). Each is its own spec after this one lands. Nothing
here makes them harder.
