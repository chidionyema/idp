# The Face, audited — and what it needs to do everything the founder can do

Audit run 2026-10-22, 12:40–13:25 UTC, by an agent on `lane/meridian-design`.
Section 2 was corrected at 13:15Z after the first pass read deployment *names* instead of images;
the correction is stated at the top and in section 9.
Every fact below was measured this session; the command that produced it is in Appendix A.
Nothing here is pushed. Nothing here is already shipped.

> **Blocked, not done.** The Face still cannot do most of what section 7 says it must.
>
> **Status, 20:10Z the same day** (this block is the only part of the document written after
> 13:25Z; everything below it is the audit as measured). A claim is now open — idp#6859, agent
> `pi-epic-090` — and the first two slices are on lanes, not on `main`:
> `lane/voice-intent-args` (2cc538ebc: `GET /voice/intents` publishes a per-argument schema,
> `POST /voice/intent` takes `{intent,args}`, `execute()` passes each value as one argv word with
> no shell, non-scalar values refused before anything runs) and `lane/estate-doors-that-fit`
> (95a2e546c: `bin/claim-open` claims from the worktree you stand in, and `lane-submit`'s push step
> fits inside the estate's own 100s command ceiling). Neither has landed: `main` has not moved
> since 15:03Z. The blocker is not this document and not those slices — it is the pipeline's
> dependency rung, where `black==26.3.1` (CVE-2026-114134) and `opentelemetry-api==1.29.0`
> (CVE-2026-114603) turned `security-scan` red on *every* lane, because every lane is scanned in
> its own tree and all of them were branched from the same stale `main`. Both pins are bumped on
> `lane/fix/security-scan-black-cve` (280d8bf14). Read section 7 as the specification of what is
> still owed, not as a plan of record that has been executed.
>
> **Correction, same day, 13:15Z.** An earlier version of section 2 said the Face was not in
> production and that the `backstage` namespace held no Face. That was wrong: I read deployment
> *names* (`catalogue`, `rotation-canary`) and concluded there was no Backstage. The deployment is
> named `catalogue` and runs the Backstage image. The corrected section 2 is measured from inside
> the pod.
>
> **Status, 2026-10-23 00:37–00:47Z — measured against production, not a plan.** Two of the gaps
> this document recorded are closed, and the real blocker is somewhere else entirely:
>
> 1. `GET https://catalogue.mumchimp.com/api/proxy/fleetview/voice/intents` → **200, 31 120 b,
>    64 intents, 53 of them declaring arguments, 7 marked `read_only`**. It was 404. The Commands
>    tab has a catalogue. `main` (63c632795, #6870) pins both `backstage` and
>    `fleetview-backend` at `main-14799-fed2b447`, which is the image that serves this route — the
>    old `main-14676` image answered `404` for `/voice/intents` and `405` for `/voice/intent`, and
>    nothing else changed but the pin.
> 2. `POST /voice/intent {"intent":"cost-today"}` → **200, `status: ok`, 4 s**. Named intent,
>    no utterance, no fuzzy match.
> 3. `POST {"intent":"ci.status","args":{"pr":6870},"session_id":"probe-6886"}` →
>    `pending_confirmation` in 2 s; `{"text":"yes","session_id":"probe-6886"}` → **`ok` in 3 s**.
>    S1 (intents carry arguments) is **operating**, for every intent whose YAML declares them,
>    through the same door the voice uses.
>
> Three defects were measured in the same ten minutes, and they are the reason "arguments work"
> is not yet the same sentence as "the founder can get anything done":
>
> - **The read-back drops the arguments.** `{"intent":"pr-list","args":{"limit":1}}` asks
>   `Run pr-list? Say yes to confirm.` — not *which* repo, not *how many*. The founder confirms a
>   name and never the thing that changes the blast radius. S2's ladder is the fix, and the rungs
>   are still hand-written in Python: `ci.status` is a *read* classified `W`, so a status query
>   needs a "yes".
> - **`pr-list` fails through the door.** The same two-step call ends
>   `error | pr list failed. [estate] status=halted`, because the installed intent still says
>   `--repo chidioniema/idp` (one letter short of `chidionyema`) and throws its stderr away. The
>   fix exists on `lane/fix/intents-name-a-real-repo` (f87791f77, 09d46f2fd) and is **not on
>   main**; `main` carries the typo.
> - **Nothing delivers main to the laptop.** This is the blocker the document did not see.
>   `estate-execute` prints `[estate] UNCONVERGED: IDP-Estate.pkg has not installed the converger;
>   running the local copy`, and the filesystem agrees: `/usr/local/estate/releases` does not
>   exist, `/usr/local/estate/sbin` does not exist, `/Library/LaunchDaemons` has no
>   `ai.estate.converge.plist`, and `/usr/local/estate` was last written **2026-09-24**. The
>   executor falls back to `~/.estate/intents`, a hand copy from that date. So the Face executes a
>   month-old snapshot of the catalogue: an intent fixed on `main` never reaches it, and
>   `pr-list` above fails in production *for a typo that is fixed on a lane*. `sudo -n true`
>   answers `a password is required`, so this one step — `installer/build.sh` → install
>   `IDP-Estate.pkg` once, for the root-owned LaunchDaemon — is founder-gated by design
>   (`installer/README`: "You enter your password once, here"). Until it is done, **every**
>   intent fix in section 7 is invisible to the Face, however green its lane.
>
> What is still absent, measured from the same 64-intent catalogue: no `agent.*` verb (S3), no
> `laptop.*` verb (S4), no `memory.*` or `audit.last` (S5). Section 7 stands as the remaining work;
> it now has a delivery step in front of it that did not appear in the original audit.

---

## 1. Verdict

*(Superseded in part 2026-10-23 00:45Z — see the status block above for what is now measured: the
catalogue answers 200 with 64 intents, and arguments work. The paragraph below is the audit as it
stood, kept unedited.)*

The Face **can** answer out loud, **can** run 64 arg-free estate intents by name (after a spoken
"yes" for 56 of them), **can** give one agent a job in a GitHub sandbox with the `pi` harness, and
**can** hand a task to the concierge. That is real, and it is real **in production**: inside the
`backstage/catalogue` pod, `POST /voice/intent` answered `200` with
`{"kind":"intent_result","intent":"ci.status","status":"pending_confirmation",…}` during this
audit. The Face is live at `https://catalogue.mumchimp.com/face/`.

It **cannot** pass an argument to anything (no PR number, no repo, no target, no path), **cannot**
run any of the 333 intents that exist only on this laptop, **cannot** choose or steer or stop an
agent, **cannot** start a fleet session, **cannot** claim work or land it, **cannot** touch the
laptop, **cannot** remember anything. Its own command catalogue answers **404 in production**, so
the Commands tab is an error string, not 64 commands — because the container that serves the Face
and the container that backs it run images two days apart (section 3.4).

---

## 2. Where the Face actually runs

The Face is a **Backstage image in the cluster**, and the laptop runs a second, independent copy of
the same code. Both are listed because the second one is what this session accidentally audited.

| Piece | Where | Evidence |
|---|---|---|
| `/face` page, production | pod `catalogue-6d6d69d6df-kz6sl`, ns `backstage`, container `catalogue`, image `ghcr.io/chidionyema/backstage:main-14776-9cc4f9ce…`, port 3100 | `kubectl get pod -n backstage -o jsonpath=…` |
| public URL | `https://catalogue.mumchimp.com/face/` → **200, 10 835 b** | `curl -L`; `/face` 301 → `/face/` |
| backend, production | same pod, container `fleetview-backend`, image `ghcr.io/chidionyema/fleetview-backend:main-14676-e403b8c0…`, ports 18790 + 8091 | pod jsonpath |
| routing | HTTPRoute `backstage/catalogue` host `catalogue.mumchimp.com`: `/api/proxy/fleetview/voice/` → svc `fleetview-voice:18790`, `/api/proxy/fleetview/` → `catalogue:3100`, `/face /fleet /voice /static …` → `catalogue:3100` | `kubectl get httproute -n backstage catalogue -o yaml` |
| intent egress | `FLEETVIEW_INTENTS_URL=http://fleetview-mac.backstage.svc.cluster.local:18790/voice/intent` — the pod forwards execution to **the laptop** over Tailscale (`fleetview-mac` is an ExternalName) | deployment env |
| second copy: page | **laptop**, two Backstage dev servers, pids 66406 and 72932, cwd `~/.estate/frontend/idp/backstage/packages/app` | `ps` |
| second copy: backend | **laptop**, launchd `ai.estate.fleetview-backend`, pid 14000, `127.0.0.1:18790`, cwd `~/.estate/runtime/idp` | `plutil -p …plist`, `lsof` |
| laptop voice-router | `127.0.0.1:8091`, `VOICE_INTENT_URL=http://127.0.0.1:18790/voice/intent` | `ps eww` |
| cluster `voice-router` ns | `voice-router-director` only — the cinema narrator, **not** the streaming router | `kubectl get deploy,pods -n voice-router` |
| cluster `mcp` ns | `estate-mcp` ×2 — the intent door is in the cluster too | `kubectl get deploy -A` |

What this changes, relative to the first version of this document:

1. **The Face has a production home**, at `catalogue.mumchimp.com/face/`, and it survives the Mac
   for the *page*. Closing the Mac still kills the machine that executes the intents: the pod's
   `FLEETVIEW_INTENTS_URL` points at `fleetview-mac`, so a sleeping laptop means a Face that talks
   and cannot act. That is the real shape of the defect — **the mouth is in the cluster and the
   hands are on the Mac** — not "the Face is a dev server".
2. **`/voice/*` exists in production** behind `/api/proxy/fleetview/voice/` → `fleetview-voice`.
   `FacePage.tsx`'s comment that "production has no voice router behind `/voice/*`" is therefore
   **stale**; the route table shows one.
3. **The laptop's copy is a shadow**, not the original: two dev servers running the same commit as
   production is the duplicate layer AGENTS.md §6 deletes, and it is why this session measured the
   wrong backend for forty minutes.
4. The Cloudflare tunnel (`~/.cloudflared/config.yml`) serves a Postgres endpoint and a 404 catch
   all; public `catalogue.mumchimp.com` is reached through the cluster's Gateway, not that tunnel.

---

## 3. Face, part A — the surface, read from the deployed commit

Source: `~/.estate/frontend/idp` @ `9cc4f9ce`: `FacePage.tsx` (512 lines), `FaceDeck.tsx`,
`faceCommands.ts`, `useVoiceRouter.ts`, `useEstateVoice.ts`, `faceEngine.ts`, `useAgentJobs.ts`,
`intentCue.ts`.

**On the screen.** Avatar owns the viewport (`FacePage.tsx`, fixed inset layer, z 2000);
TalkingHead vendored under `/face/`, no model downloaded to the phone (`faceEngine.ts` header). One
glass pill: captions, reply, mic, milestone toggle. Three muted strips: newest research claim, lane
+ burn, the agent jobs the face sent. **The Deck** (`FacePage.tsx:311`) — closed by default, tabs
`commands` / `agents` / `persona`.

**Two voice engines**, chosen by `useFaceVoiceEngine`; `estate.face.voice=legacy` in localStorage
forces the old one. `useVoiceRouter` = one WebSocket `/voice/ws`, partials while speaking, first
audio 2.26 s (its own comment, measured 2026-09-26) vs 3.0–3.8 s for `useEstateVoice`'s three round
trips. Both drive the lip-synced clause sink.

**Every door the Face can knock on.**

| # | Door | Fires when | Ceiling |
|---|---|---|---|
| 1 | brain answer | any speech | words only |
| 2 | `POST /voice/intent` (voice) | utterance names an intent | 64 argless intents |
| 3 | `POST /voice/intent` (deck) | tap **Run** | same door, same gate — by design (`faceCommands.runCommand`) |
| 4 | `give an agent a job: <task>` | regex `_AGENT_JOB_PHRASE` | 1 workflow, harness **`pi` hardcoded** |
| 5 | `concierge, <task>` | regex `_CONCIERGE_PHRASE` | local Chrome, stops before paying |
| 6 | `GET /voice/intents` | Deck Commands tab | **404 on the live backend** |
| 7 | `GET /agent-jobs` | `useAgentJobs` poll 10 s / 60 s | read-only |
| 8 | avatar / voice swap | Persona tab | deck only — **no spoken verb** |

### 3.1 No arguments. At all.

`execute()` (`voice_intents.py:372`) runs `subprocess.run([exe, intent])` — an argv list of two.
`load_catalog()` (`:233`) *excludes* any intent whose args are not all defaulted:

```python
if not all(isinstance(v, dict) and "default" in v for v in args.values()):
    continue
```

Measured with the estate's own loader:

```
arg-free intents in the voice catalog: 64
```

"merge pull request 6846", "run the tests in idp", "logs of the fleetview pod", "review the diff"
are all **outside the Face**. The founder's most common sentences need a number.

### 3.2 The matcher is a name-token subset, not language

`match()` (`:257`): `if set(name_tokens(name)) <= words`. `pr-merge` is reached by saying *"pr
merge"*. "merge pull request 6846" normalises to `{merge, pull, request}`, which does not contain
`pr` — no match; the brain answers instead. The Face is a voice **menu**, not a voice **operator**.

### 3.3 Only 8 of 64 run without a confirmation

`READ_ONLY` (`:22–31`) = `ci-status, ci.errors, cost-today, git-log, lane, router-status,
voice-turns, ledger-verify`. The other 56 answer `pending_confirmation` and wait ≤ 60 s for exactly
`yes|confirm|do it`. Everything interesting is in that 56 — including `halt`, `disk-cleanup`,
`flux-kick`, `secrets-discovery`, `site-onboard`, `net-flannel-unmasq`.

### 3.4 The catalogue is 404 — in production and on the laptop, for two different reasons

Two deployments answer this door, and **both** say 404. The symptom is the same; the causes are
different, and the production one is the more serious.

**Production — sibling image skew inside one pod.** The Face and its backend are two containers of
`catalogue-6d6d69d6df-kz6sl`, deployed from two images:

| container | image | commit date |
|---|---|---|
| `catalogue` (the Face) | `backstage:main-14776-9cc4f9ce…` | 2026-10-22 10:35Z — **carries `FaceDeck` and the catalogue call** |
| `fleetview-backend` | `fleetview-backend:main-14676-e403b8c0…` | 2026-10-20 07:52Z — **predates `GET /voice/intents`** |

Measured from inside the pod, against the container's own loopback:

```
/voice/intents    404 22 b          <- route absent from the image
/voice/intent     405 31 b          <- route present, POST only
/openapi.json     200 14 224 b
module: /app/backstage/plugins/fleetview-backend/src/fleetview_backend
has catalogue route: False
```

So the new Deck is asked to fetch a route that its sibling container's image does not have. The
public path agrees: `GET https://catalogue.mumchimp.com/api/proxy/fleetview/voice/intents` →
**404 `{"detail":"Not Found"}`** (FastAPI's own body, i.e. it reached the backend and the backend
did not know the path). `e403b8c0` **is** an ancestor of `9cc4f9ce`, so this is not a divergent
branch — it is two images from consecutive days landing in one pod, because Flux image automation
bumps the `backstage` image and the `fleetview-backend` image independently.

**Laptop — an editable install shadowing the runtime checkout.** `plutil -p` shows the launchd job
runs `/Library/Frameworks/Python.framework/…/python3 -m fleetview_backend.serve` with
`WorkingDirectory = ~/.estate/runtime/idp`, and that checkout *does* have
`@app.get("/voice/intents")` at `serve.py:740`. Yet the process answers 404, because
site-packages holds `__editable__.fleetview_backend-0.1.0.pth` pointing at
`~/Documents/code/idp/backstage/plugins/fleetview-backend/src`, and that dev checkout — on
`lane/meridian-design`, 37 commits behind `main` — has no such route:

```
$ cd ~/.estate/runtime/idp && python3 -c 'import fleetview_backend…'
resolves to: /Users/roseonyema/Documents/code/idp/backstage/plugins/fleetview-backend/src/fleetview_backend
has catalogue route: False
```

In both places `CommandsTab` renders `face-deck-error` — "The catalogue answered 404." — while the
voice door next to it works. **The deployed pair of images is incoherent, and the laptop's install
is incoherent with its own directory.**

Not yet verified: whether `FaceDeck` renders at all in a browser, and what is on cluster port 8091
(`/health`, `/voice/ws` and `/voice/intents` all 404 there, so it is not a second backend on that
port). I claim only what the probes printed.

---

## 4. Estate, part B — the plane the Face is allowed to touch

### 4.1 Three different intent registries

| Registry | Count | Who sees it |
|---|---|---|
| `platform/estate/intents/*.yaml` (the record) | **91** | the voice catalogue, reviewers |
| `~/.estate/intents/*.yaml` (the laptop, the truth) | **333** | the running executor |
| arg-free subset of the committed 91 | **64** | the Face |

242 intents exist **only on this laptop**: uncommitted, unversioned, invisible to every other
agent, invisible to the Face, lost with the disk. `estate_list` shows ~400 names, most of them
one-off session debris — `check-pr-final-state`, `step1-main`, `fix-both`, `test-heredoc`,
`proof`, `proof2`. That is not a verb vocabulary; it is a transcript of past sessions in YAML. And
the one capability that matters — *doing a thing with an argument* — is absent from all 333.

`pr-list`, one of the 91, cannot parse its own body: the embedded Python lost its indentation and
dies `IndentationError: expected an indented block`. Policy shadow, same turn: `would refuse
pr-list -- 7/7 runs not ok in 30d`. `gh-api` is `22/22 not ok in 30d` — while a plain
`gh api repos/…/issues/6836` answered correctly in 25 s. The intent is broken; the network is not.

Every intent invocation this session printed:

```
[estate] UNCONVERGED: IDP-Estate.pkg has not installed the converger; running the local copy
```

The converger is not installed, so every recorded action runs off a local fallback copy.

### 4.2 The agent plane

- **A job** = one run of `.github/workflows/agent-sandbox.yml`: agent works in a runner with **no
  credential**, main's epistemic firewall grades every claim, the App opens a PR,
  `merge-when-green` lands it. `HARNESSES = ("pi", "claude-code")`, `MAX_ACTIVE = 3`, task ≤ 4000
  chars, duplicate window 120 s, and a redactor refuses a task that looks like it holds a secret
  (`agent_jobs.validate`, `:233`).
- **What voice reaches:** `_send_agent_job` → `agent_jobs.submit(task, "pi", …)` — harness
  **hardcoded** (`voice_intents.py:166`). `claude-code` is unreachable by voice. No verb for list /
  stop / steer / resume; the face can only watch and speak the ending.
- **The fleet-scale plane is inert.** `estate_session_start` documents `echo | sleep | ask | claude
  | llm`. `sovereign/engine/runners.py:159`:

  ```python
  REGISTRY = {"echo": _echo, "sleep": _sleep, "ask": _ask, "burn": _burn, "llm": _llm}
  ```

  There is **no `claude` runner**; `run()` answers `unknown runner: claude` with `done: True` — a
  refusal shaped like success. "Invoke any agent" at fleet scale is impossible today.
- **On this laptop:** `claude` (`~/.local/bin`), `pi`, `ollama`, `sb`, `growmos`. No `codex`, no
  `gemini`, no `grok`. None is a verb on the Face.

### 4.3 Coordination

`idp#6836` is **open** — "face: land the FaceFindingsStrip hooks fix on its own (live /face React
#310)", updated `2026-10-22T10:38:22Z` — held by another agent on
`backstage/packages/app/src/modules/home/FacePage.tsx`. This audit respects the claim: no file under
that path was touched. `estate-graph`: `bin/graph-health` → `ok  graph-health: all checks passed`,
with `WARN 757 sources registered but never extracted`.

---

## 5. Research, part C — what a voice control plane for everything actually looks like

Fetched this session through `r.jina.ai` (sources at the end). Condensed to what changes a design:

1. **Tool calling is the architecture, not an add-on.** MCP: a server declares tools with `name`,
   `description`, `inputSchema` (JSON Schema), optional `outputSchema` and `annotations`; the client
   sends `tools/list`, then `tools/call` with a structured `arguments` object, and gets structured
   content back, with `isError` distinguishing execution failure from protocol error. The estate's
   intents already have `name`, `description`, `args` — they are one schema declaration away from
   being tools. **The Face needs no new capability layer; it needs its existing intents to carry
   schemas and arguments.**
2. **Annotations keep a gate deterministic while the model stays free.** MCP's `annotations` carry
   behavioural hints (read-only vs destructive, idempotent) *alongside* the schema. That is exactly
   the estate's `READ_ONLY` — except today it is a hand-maintained frozenset of 8 names in one
   Python module, not a property of the intent. Move the hint onto the YAML and the gate becomes
   data, not a list that drifts.
3. **Long actions must run in the background, not block the mouth.** LiveKit is explicit: tools run
   synchronously or *in the background so the agent keeps talking while the work completes*; a tool
   may also `session.say()`, hand off to another agent, or forward the call to the front end over
   RPC. The estate's 120 s `EXEC_TIMEOUT_S` and a silent `Thinking…` are the opposite pattern.
   Every heavy verb should return a handle and narrate.
4. **Provider-side computer use is a trap for this estate.** Anthropic ships `ComputerUse` as a
   provider tool (as LiveKit consumes it); OpenAI ships `WebSearch`/`FileSearch`/`CodeInterpreter`.
   None is governable by the estate's gate, none leaves an intent ticket, none is `estate-execute`.
   Using them would be a second execution boundary — AGENTS.md §6 forbids exactly that. The Face's
   superpowers must come from **the estate's own intents**, not a vendor's sandbox.
5. **Realtime sessions are stateful, and tool calls chain inside one turn.** OpenAI's Realtime API
   keeps a `Session`, a `Conversation` of items, and `Response` objects; function calling happens
   inside the session, so the model sees the tool result and can chain a second call in the same
   turn. `/voice/ws` already has the session shape (`session.Session`, turn ids, barge) — but its
   intent hook fires **once per final transcript** and returns the result's last line, not a tool
   result the model can chain from. That is the difference between "the face can run a command" and
   "the face can do a job".

---

## 6. The gap, as a matrix

Founder action → what the Face can do today. **W** works, **P** partial, **A** absent.

| # | The founder does this on the computer | Today | Why (measured) |
|---|---|---|---|
| 1 | "what's going on?" | **W** | brain + `FaceEstateLine` / `FaceFindingsStrip` |
| 2 | read-only status intents by name | **W** (8) | `READ_ONLY` |
| 3 | any other argless intent | **P** | needs literal "yes"; 56 names |
| 4 | see the catalogue of what is possible | **A** | `/voice/intents` 404 on the live backend |
| 5 | merge PR **6846** | **A** | no args anywhere |
| 6 | run tests in repo **idp**, target **x** | **A** | no args |
| 7 | logs of pod **y** in ns **z** | **A** | no args |
| 8 | give an agent a job | **P** | works; harness hardcoded `pi` |
| 9 | give that job to **claude-code** | **A** | harness is not a voice parameter |
| 10 | list / stop / steer / resume jobs | **A** | no verbs; only polling |
| 11 | start a budgeted fleet session (`sb start`) | **A** | no verb; and no `claude` runner exists |
| 12 | claim an issue, submit a lane, land | **A** | no verbs |
| 13 | shell on the laptop | **A** | deliberate — and correct — but nothing replaces it |
| 14 | edit a file / write code | **A** | must be an agent; no "start a session here" verb |
| 15 | remember / recall a fact | **A** | `estate-memory` is MCP-only, not on the Face |
| 16 | ask the concierge for a web task | **W** | `concierge-task` |
| 17 | approve or deny a pending action | **W** | "yes"/"no", 60 s TTL |
| 18 | change the avatar or the voice | **P** | deck only; no spoken verb |
| 19 | see what the estate did and why | **P** | `~/.estate/voice-intents.jsonl`; no read-back |
| 20 | deploy / check Flux | **P** | only the argless flux/k8s intents |
| 21 | two things in one breath ("check CI then merge") | **A** | one intent per final transcript |
| 22 | interrupt a running action | **P** | barge silences audio and cancels the ctx |
| 23 | work from another device, or after the Mac sleeps | **P** | the page is in the cluster; the *execution* goes to `fleetview-mac`, so a sleeping Mac is a Face that talks and cannot act |

**Nineteen of twenty-three are P or A, and all four W's are read-only or canned.**

---

## 7. Superpowers — the design that closes it

The estate does not need a new execution plane. It needs **seven changes to what already exists**, and
the Face inherits each for free because it only ever talks to `POST /voice/intent`.

### S1. Intents carry arguments, and the brain fills them

`intents/*.yaml` already declares `args: {type, default}`. Add `required`, per-arg `description`,
and emit the whole thing as MCP `inputSchema`. Then:

- `GET /voice/intents` returns `name, description, read_only, inputSchema` — one field more, no new
  route.
- `POST /voice/intent` accepts `{intent?, args?, text?, session_id}`. With `intent` set the gate runs
  it directly with `args`, no fuzzy matching. With only `text`, the brain makes one **structured**
  call — `{"intent": "…", "args": {…}}` — validated against the schema before the gate sees it.
- `execute()` becomes `[exe, intent, *--k=v]`, argv only, still never a shell string.

**This alone moves rows 5, 6, 7 from A to W.**

### S2. The confirmation ladder becomes intent data

Today: 8 read-only names in a Python frozenset. Instead each intent declares a rung, and the gate
enforces it deterministically — the model never chooses:

| Rung | Declared | Voice rule |
|---|---|---|
| `read` | `risk: read` | runs immediately |
| `write` | `risk: write` | spoken read-back, then "yes" (TTL 60 s) |
| `destructive` | `risk: destructive` | read-back naming target **and** blast radius, then "yes" **and** a spoken 2-word code, TTL 30 s |
| `irreversible` | `risk: irreversible` | **refused from voice**; names the web button that does it |

This is the estate's own `break-glass` TTL idea (`ttl 30 s–1 h, SQLite audit`) applied per intent.
The 242 uncommitted intents get a rung or they are deleted — a rung is the price of being callable.

### S3. Agents become a verb family, not a regex

Five intents with schemas, so the Face inherits them and `claude-code` stops being unreachable:

- `agent.job` — `{task, harness: enum(pi, claude-code), repo?}` → `agent_jobs.submit`
- `agent.jobs` — list with state
- `agent.stop` — `{run_id}` (new cancel call; `agent_jobs` has none today)
- `agent.say` — `{run_id, text}` steer
- `session.start` — `{task, runner, budget, critical}` → `sb start` for work too big for a sandbox

`give an agent a job: <task>` keeps working — one regex stays, for the founder's habit — but becomes
an alias onto `agent.job`. `useAgentJobs` already narrates the ending; `agent.stop` lets the founder
say "no, not that one" *while it runs*. **Rows 9, 10, 11 close.**

### S4. The laptop gets a governed verb, or the founder keeps a blind spot

Rows 13/14 are the honest hard part: "anything the founder can do on the computer" includes a
shell. The answer is **not** a raw shell from a language model. It is:

- `laptop.run` — `{command, why}` where `command`'s argv[0] must match an allow-listed binary
  (`rg, git, ls, cat, kubectl get, gh api`; no `rm`, no `curl | sh`), risk `write`, argv-split, no
  shell, output recorded in `voice-intents.jsonl`, refused with the matched rule named otherwise.
- `laptop.agent` — `{task, cwd}` → starts a real `claude` or `pi` session on this Mac, so "edit this
  file" is done by an agent with a claim, not by the Face.
- Anything else: the Face names the door that exists instead.

Anything wider is a second execution boundary and breaks AGENTS.md §6. That trade-off should be
said to the founder in these words, not quietly shipped.

### S5. Memory and audit become verbs

- `memory.remember` — `{fact, type}` → estate-memory.
- `memory.recall` — `{question}` → estate-memory, spoken.
- `audit.last` — `{n}` → the last *n* lines of `voice-intents.jsonl`, spoken short.

Row 19 today requires opening a file on the laptop; that is not a work surface.

### S6. The hands move into the cluster

The page already lives in the cluster; the execution does not. `FLEETVIEW_INTENTS_URL` points at
`fleetview-mac` over Tailscale, so every intent — including `read` ones — needs this laptop awake.
The pieces exist: `estate-mcp` already runs 2 replicas, the `voice-router` namespace exists and
holds only a narrator, and `fleetview-voice` is already a ClusterIP service behind the HTTPRoute.
Deploy the executor in-cluster, keep `laptop.run` / `laptop.agent` as the only laptop-bound verbs,
and make a sleeping laptop a spoken refusal that names `fleetview-mac` — not a pending confirmation
that never resolves.

### S7. One door, so a tap and a sentence cannot differ

`faceCommands.runCommand` already posts the intent *name* through `POST /voice/intent`, on purpose.
Keep that invariant as arguments arrive: the Deck sends `{intent, args: defaults}`, the voice sends
the same shape after the brain fills it, and both are judged by the same rung. Two doors with
different rules is how the estate got a `/voice/intents` that 404s next to a `/voice/intent` that
works.

---

## 8. Defects found this session, in fix order

1. **The Face and its backend are two images two days apart in one pod.** `backstage` at
   `9cc4f9ce` asks for `GET /voice/intents`; `fleetview-backend` at `e403b8c0` (2026-10-20 07:52Z)
   does not have it → 404 in production, on the public path too. Fix: make the two images bump as
   one unit (Flux `image-automation` policy on the pod's image set, or one image with both
   processes), and add a production probe that asserts the *frontend's own* catalogue call is 200
   after every deploy — a gate that checks `/voice/intent` alone would have passed this.
2. **The laptop's backend imports an editable install of the dev checkout** (`__editable__
   .fleetview_backend-0.1.0.pth` → `~/Documents/code/idp/.../src`, no route) while its own
   `WorkingDirectory=~/.estate/runtime/idp` has the route. Fix: drop the editable install from the
   framework Python or pin `PYTHONPATH` in the plist, then assert 200 on restart.
3. **Two Backstage dev servers run the same commit as production** (pids 66406, 72932). Fix: one
   surface, or a dev server that says out loud which commit it is on.
4. **No arguments anywhere** (S1).
5. **`READ_ONLY` is a frozenset of 8 in Python** (S2).
6. **Harness hardcoded `pi`** in `_send_agent_job` (S3).
7. **`claude` is not in the runner registry** and `run()` reports `done: True` for an unknown
   runner — a refusal that reads as success. Fix: add the runner or return `done: False` with
   `unknown runner`.
8. **242 intents live only on the laptop**; the record is 91. Fix: a gate that refuses a
   `~/.estate/intents` name absent from `platform/estate/intents`, and deletes session debris.
9. **`pr-list` has an `IndentationError`; `gh-api` fails 22/22** while `gh api` works. Fix both;
   they are the read doors the Face needs most.
10. **The converger is not installed** — `[estate] UNCONVERGED` on every call.
11. **The hands are on the Mac.** The Face page and its backend run in the cluster, but
    `FLEETVIEW_INTENTS_URL` points at `fleetview-mac` (Tailscale ExternalName), so execution stops
    when the laptop sleeps. Fix: add the in-cluster execution path (S6), and make a sleeping laptop
    a spoken refusal with its reason rather than a pending confirmation that never resolves.
12. **`voice-router` ns runs the cinema narrator only** — the streaming router has no workload
    there; `/voice/ws` on cluster port 8091 answers 404 on `/health` and `/voice/ws`.

---

## 9. What I did not verify, and will not claim

- **I got section 2 wrong once, and this is what it cost.** My first pass ran
  `kubectl get deploy -n backstage`, saw the names `catalogue` and `rotation-canary`, and wrote
  "no Face, no fleetview, no backstage". The deployment is *named* `catalogue` and runs
  `backstage:main-14776-9cc4f9ce…` with a `fleetview-backend` sidecar. I had measured names and
  graded the thing by its name. Corrected from inside the pod; the error and its cause are recorded
  at the top of this document.
- I did not speak into the microphone. The voice→intent path was exercised over HTTP
  (`POST /voice/intent`), in the production pod and on the laptop; I did not watch a spoken turn
  light up `intent_result` on a screen.
- I did not render `/face/` in a browser. I know production serves the HTML shell (200, 10 835 b)
  from the image built at the commit that adds `FaceDeck`, and that the bundle is lazy-chunked (no
  `Face` chunk appears in `runtime.37c46c2bad22.js`), so I am not claiming the deck draws.
- I did not resolve what cluster port 8091 is for (`/health`, `/voice/ws`, `/voice/intents` all 404
  inside the pod).
- `kubectl port-forward` to `searxng` did not establish, so online research went through
  `r.jina.ai` over plain HTTPS, not the estate's own search.
- Nothing here was landed: no claim, no lane, no PR. `idp#6836` holds `FacePage.tsx`.

---

## Appendix A — the commands that produced these facts

```
rg -l "useEstateVoice|FacePage|faceCommands|faceEngine" .            # surface map
wc -l …/home/{FacePage.tsx,useVoiceRouter.ts,voice.py,serve.py}      # sizes
python3 -c "from fleetview_backend import voice_intents as v; print(len(v.load_catalog()))"
ls ~/.estate/intents/*.yaml | wc -l ; ls platform/estate/intents/*.yaml | wc -l
curl -s -X POST http://127.0.0.1:18790/voice/intent -d '{"text":"ci status",…}'
curl -s http://127.0.0.1:18790/openapi.json            # no /voice/intents
curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:18790/voice/intents   # 404 (laptop)
plutil -p ~/Library/LaunchAgents/ai.estate.fleetview-backend.plist            # cwd + -m module
python3 -c 'import fleetview_backend…'                 # -> editable install, dev checkout
ls /Library/Frameworks/Python.framework/…/site-packages/*fleetview*           # .pth
curl -sL -o /dev/null -w '%{http_code}' https://catalogue.mumchimp.com/face/  # 200, production
kubectl get pod -n backstage -o jsonpath='{.items[*].spec.containers[*].image}'
kubectl exec -n backstage <pod> -c fleetview-backend -- python3 -c 'urllib …'  # 404 / 405 / route
kubectl get httproute -n backstage catalogue -o yaml   # /api/proxy/fleetview/voice/ -> fleetview-voice
curl -s https://catalogue.mumchimp.com/api/proxy/fleetview/voice/intents      # 404 detail Not Found
git show e403b8c0:…/serve.py | rg voice/intents        # absent (deployed backend image)
git merge-base --is-ancestor e403b8c0 9cc4f9ce         # yes — skew, not divergence
ps eww -p 72858                                        # VOICE_INTENT_URL set
kubectl get deploy -n backstage ; -n voice-router ; -A | rg 'fleet|voice|backstage'
gh api repos/chidionyema/idp/issues/6836 --jq '{state,title,updated}'
bin/graph-health --root ~/Documents/code/estate-graph
```

**Sources (fetched 2026-10-22 via `r.jina.ai`).**
OpenAI, *Realtime conversations* — https://platform.openai.com/docs/guides/realtime-conversations ·
LiveKit, *Tool definition and use* — https://docs.livekit.io/agents/build/tools/ ·
Model Context Protocol, *Tools* (spec 2025-06-18) — https://modelcontextprotocol.io/specification/2025-06-18/server/tools

