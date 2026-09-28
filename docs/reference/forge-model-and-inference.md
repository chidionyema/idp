# The Forge's Modal contract and the serving-endpoint question (2026-09-08)

A durable record so the "how is Modal authenticated / can we host a model" question is answered
once, with file:line, and never re-derived per session. Verified from the repo and a peer session
on 2026-09-08.

## The two claims that keep being repeated, and their ground truth

1. **"We already use Modal in our stack"** — TRUE, but with a narrow meaning. Modal is in the
   stack for the **Forge's ephemeral GPU training runs** only.
   - CLI: `modal` present on this Mac (`modal client version 1.5.5`).
   - The one Modal app is `modal.App("model-forge")` in `forge/modal_app.py`, documented as an
     **"Ephemeral GPU launcher"**: `modal run forge/modal_app.py --task ...`. It trains, pushes to
     GHCR, files an experiment record. There is **no `modal serve`/`modal deploy` and no
     `web_endpoint`** anywhere in `forge/`. It is training-only.
   - Cost model in `forge/common.py`: `GPU_USD_PER_HOUR` = {T4, L4: $0.80, L40S: $1.95, ...}; every
     run passes `cost_gate()` vs a task `budget_usd`. Paid GPU is budget-gated.

2. **"Modal is authenticated / it's a frictionless one-root problem"** — Modal auth in this estate
   is **CI-only by design** (R52 "one root per provider"; the whole `forge-train.yml` comment says
   "no terminal, no token on a laptop"):
   - The Modal one-root is the **GitHub repository secret pair** `SEED_MODAL_TOKEN_ID` +
     `SEED_MODAL_TOKEN_SECRET`, set once via `bin/idp-set-root modal`
     (`bin/idp-set-root` lines ~126-127; `platform/vendors/consoles.yaml:29`).
   - `.github/workflows/forge-train.yml` exports them as `MODAL_TOKEN_ID`/`MODAL_TOKEN_SECRET`
     and proves the pair with `modal secret list` before any `modal run` (forge-train.yml:38-39,58-60).
   - **No local/mac session authenticates Modal with the repo secrets.** A laptop session with no
     token fails (`modal app list` -> "Token missing"). `modal token new` on a laptop is what the
     estate rules forbid. So an agent session runs Modal authenticated only inside CINODE, with the
     secret pair in env — there is no recorded local invocation.

## The serving-endpoint question (Qwen-14B / your "$penny open-model" idea)

The proposal repeated in several sessions — host Qwen-2.5-14B-Instruct-AWQ on a Modal
L4, scale-to-zero, exposed as an OpenAI-compatible endpoint wired as a LiteLLM lane — is a
**brand-new pattern this estate has never deployed**:
- It needs an `@app.cls` + `@modal.web_endpoint` (or an ASGI/HTTP serving class) with
  `scale_to_zero`, NOT the existing `@app.function` `modal run` training shape.
- It is PAID GPU kept reachable (warm-or-scheduled), so it is a forge `cost_gate`/budget decision,
  and under the CI-only rule a deploy would go through a new CI workflow (`modal deploy`), not a
  laptop `modal deploy` with a local token.
- The estate's one model ROUTER is LiteLLM (`llm/config.yaml`); a self-hosted lane would be added
  there, not as a second inference system (one-platform rule).

DECISION OPEN (founder, 2026-09-08): whether to stand up a paid Modal serving deployment of an
open model as a LiteLLM lane. Until then: Modal = ephemeral training only; inference stays on the
managed lanes in `llm/config.yaml`. This record exists so the "can we host our own model for
pennies" question is answered with the real constraint (CI-only auth, training-only forge, paid GPU
gated) rather than re-explored each time.

## Concrete facts a future session needs

- Run a training task authenticated: do it in CI or export `MODAL_TOKEN_ID`/`MODAL_TOKEN_SECRET`
  from the repo secrets into env, then `modal secret list` to prove, then `modal run forge/modal_app.py --task <task>`.
- Pricing (forge/common.py `GPU_USD_PER_HOUR`): T4, L4 = $0.80/hr; L40S = $1.95/hr.
- Files: `forge/modal_app.py`, `forge/common.py`, `bin/idp-set-root`, `platform/vendors/consoles.yaml`,
  `.github/workflows/forge-train.yml`.
