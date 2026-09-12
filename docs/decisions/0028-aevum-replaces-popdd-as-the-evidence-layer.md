# 0028 — Aevum replaces POPDD as the estate's evidence layer

Founder, 2026-09-12, verbatim: "we going forward with the decin for better silution".

## The decision

The estate adopts **Aevum** (`pypi: aevum-core`, `github: aevum-labs/aevum`) as its
agent-action evidence layer. **POPDD is retired**: `popdd-ts`, `lux-popdd` and `lux` are
removed once Aevum carries the load.

## Why Aevum, and why POPDD loses

POPDD is an HMAC-chained receipt library. Its weakness is structural, not a bug: HMAC is a
**symmetric** key, so a receipt can be verified only by the party who holds the signing key.
That is a record two parties share, not evidence a third party can check.

Aevum signs with **Ed25519** and, by default, **ML-DSA-65** (post-quantum) — both asymmetric,
so any party verifies with a public key and no access to the writer. It wraps each entry in a
**COSE_Sign1** receipt with an **RFC 3161** trusted timestamp, and ships `aevum-verify`, a
standalone verifier that shares no code with the runtime.

These were measured, not read from a README. Aevum was installed into a throwaway virtualenv
and driven:

| Claim | Measurement |
|---|---|
| Records signed receipts | `audit_id: urn:aevum:audit:01a09580-a73f-7a2e-9c19-13b65279a10d` (UUIDv7) |
| Hash-chained ledger | every entry carries `prior_hash` and `payload_hash` |
| Asymmetric signing | `ed25519_pub` / `ed25519_sig` present on every entry |
| Post-quantum, by default | `mldsa65_pub` / `mldsa65_sig` present on every entry |
| Trusted timestamp | `tsa_token` / `tsa_url` populated |
| Tamper detection | a stored payload was mutated in place; `verify_sigchain()` returned `False` |
| Immutability | assigning to a signature raises `FrozenInstanceError` (frozen dataclass) |
| Gap reporting | `record_capture_gap(gap_type, actor, reason)` |
| Replay | `replay(audit_id=..., actor=...)` |

The tamper result is the one that matters: the chain was broken on purpose and it caught the
break. POPDD has no equivalent claim that survives the same test, because verification
requires the signing key.

## What this rejects

- **Keeping POPDD as-is.** Its HMAC trust model cannot produce third-party-verifiable
  evidence, and the estate is selling governance to a buyer's engineer.
- **Helixar HDP** (the other candidate, and better integrated: 12 middleware packages across
  CrewAI, LangChain, AutoGen, MCP, LangGraph, LlamaIndex, Grok, Microsoft agent-framework, plus
  a real IETF Internet-Draft). **HDP 0.1.0 is broken end to end.** In
  `packages/hdp-agent-framework/src/hdp_agent_framework/middleware.py:243` it calls
  `self._scope.to_dict()`, but `HdpScope` in `_types.py:34` is a plain `@dataclass` with no
  `to_dict`. The resulting `AttributeError` is swallowed at `middleware.py:150` by
  `except Exception` logging "HDP process failed (non-blocking)", so **no token is issued,
  nothing is recorded, and the action proceeds anyway** — `export_token()` returns `None`.
  A governance control that fails open and silently records nothing is the exact failure class
  this estate keeps paying for. HDP is reconsidered if and when it can sign one token.
- **"agent-sign", "occasio" and "auditable"** — three further tools recommended to the founder
  in the same comparison. They were searched for and **could not be found**; no action is taken
  on unfindable projects.

## What is still true and unresolved

- Aevum is maintained by **one person**, has **2 GitHub stars**, and its README states it is
  "a solo open-source research project — not a commercial product or formal legal entity."
  Adopting it makes the estate depend on an artefact that could stop. The mitigation is that
  the ledger is stored in the estate's own Postgres, so the records outlive the tool.
- Aevum's default ledger is **in-memory**. A misconfigured deployment loses every receipt on
  restart while `verify_sigchain()` still returns `True` on an empty chain — it reports green
  while recording nothing. Any deployment must fail closed on an empty ledger.
- `prospector/scripts/popdd_verify.py` imports `popdd.agent`. POPDD cannot be deleted until
  that caller is moved. The import is the reason a previous POPDD defect ("ModuleNotFoundError:
  No module named 'popdd.agent'") crashed every checkout on the machine on 2026-08-18.

## Status

Accepted. Integration is staged: recording first, enforcement later, and nothing in the
estate's request path is touched until recording is proved.
