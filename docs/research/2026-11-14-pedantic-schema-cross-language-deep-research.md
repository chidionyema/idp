# Pedantic Schema — cross-language architecture study and recommendation

**Research date:** 2026-11-14  
**Status:** RESEARCHED / RECOMMENDED / NOT ADOPTED ON MAIN / NOT RUNTIME-VERIFIED  
**Owner:** existing IDP schema-conformance/intent-compile owners; Argon protocol owner for federation  
**Parent mandate:** `docs/decisions/0042-one-schema-at-every-boundary.md` and `docs/specs/2026-11-14-pedantic-schema-first-class.json`

## Executive decision

**Do not make Pydantic the universal source for a Rust/Python/TypeScript estate.** It is an excellent Python implementation; it is not a neutral interchange standard. For **new shared JSON payloads**, make **JSON Schema Draft 2020-12** the authoritative, versioned contract artifact, validated independently at each receiving boundary. Native language models may be *generated from* that artifact or, when a domain's owning implementation is already authoritative, generate it with Schemars/Pydantic **provided that generated schema is pinned, diffed, independently validated and explicitly accepted as the one published contract**. Never maintain two competing handwritten versions.

For **new strongly typed binary RPC/event links** where compatibility, stream efficiency and source generation justify another encoding, evaluate **Protocol Buffers + Buf** as the authoritative IDL for that bounded interface; do not retroactively wrap every agent JSON payload in Protobuf. For **config and constraint composition**, CUE is a strong complementary validator/compiler, not a default replacement for the existing intent JSON contracts. OpenAPI specifies HTTP operations built on JSON Schema and is a service contract, not a universal evidence/agent protocol. No evaluated technology alone proves provenance, authorization, truthful claims, causal custody or domain invariants.

**Key architecture distinction:** one **wire contract per interface**, not one **source language or runtime validation library** for the entire estate. `Pydantic-first` applies only within independently Python-owned private domain models; `Serde-first` similarly within Rust-only private models. Both must conform to the published wire schema at cross-service effects.

## Primary source research

| Technology | Strength | Limitation/fit |
| --- | --- | --- |
| **Rust Serde** | Native typed serialization/deserialization; `#[serde(deny_unknown_fields)]` closes unknown fields. | Not a general cross-language constraint language; deserializing a Rust struct is not automatically a full business validator. [Serde docs](https://serde.rs/attributes.html) |
| **Rust Schemars** | Derives JSON Schema from Rust structures and honours several Serde attributes. | Generated schema representation can evolve across dependency versions even if Rust API does not; pin and diff. [Schemars](https://docs.rs/schemars/latest/schemars/) |
| **Rust Garde / validator** | Declarative field-level validation and custom checks. | Arbitrary custom checks are not faithfully expressible/portable in JSON Schema; write independent cross-language fixtures. [Garde](https://docs.rs/garde/latest/garde/) |
| **Rust jsonschema** | Validates instances against published schemas with Draft 2020-12 support and explicit format options. | Dialect/format/vocabulary compatibility must be tested; newer drafts have partially unsupported features. [jsonschema crate](https://docs.rs/jsonschema/latest/jsonschema/) |
| **Rust Typify** | Generates Serde-compatible Rust types from JSON Schema. | JSON Schema constraints exceed what Rust static types encode; generation may not capture all conditional/custom constraints. Retain runtime validation at effect door. [Typify](https://docs.rs/typify/latest/typify/) |
| **Pydantic v2** | Python domain models, validation, two JSON Schema modes (validation/serialization). `pydantic-core` is itself partly Rust. | Python validators/custom semantics are not necessarily representable as wire constraints; generator defaults/alias/null coercion vary. [Pydantic docs](https://pydantic.dev/docs/validation/latest/concepts/json_schema/) |
| **JSON Schema 2020-12** | Portable JSON vocabulary for presence, types, enum, ranges, patterns, closure, composition. Existing IDP contract already uses it. | Not a specification for RPC transport, authentication, causal evidence or arbitrary semantic assertions. `format` defaults to **annotation**, not necessarily assertion: enforce format validators explicitly. [Spec](https://json-schema.org/draft/2020-12) |
| **OpenAPI 3.1+** | HTTP endpoints, status responses, auth declarations, generated clients; 3.1 schema is a superset of JSON Schema 2020-12. | HTTP API description only, not a substitute for agent/instruction/evidence/event contracts; dialect details matter. [OAS 3.1](https://spec.openapis.org/oas/v3.1.0.html) |
| **Protocol Buffers + Buf** | Compact binary messages, Rust Prost, strong generated types, formal compatibility checks (`buf breaking`). | ProtoJSON differs from regular JSON; unknown fields are not preserved in ProtoJSON and field renames can break JSON consumers; strict arbitrary constraints require further tooling. [Google ProtoJSON](https://protobuf.dev/programming-guides/json/) [Buf breaking](https://buf.build/docs/breaking/) [Prost](https://docs.rs/prost/latest/prost/) |
| **CUE** | Constraint unification, closed structs, config validation, schema composition, JSON Schema/Protobuf integration. | Cross-language static code generation and some semantic conversions need evaluation; introduces an additional authoring language and is most defensible for config/policy composition, not every user-facing request. [CUE integration](https://cuelang.org/docs/integration/) [CUE JSON Schema](https://cuelang.org/docs/concept/how-cue-works-with-json-schema/) |
| **Smithy 2.0** | Service/resource IDL, protocol independence, constraint traits and codegen, supported Rust/TS toolchains. | Higher migration/ecosystem cost for estate's current JSON first agent ingress; evaluate if service API synthesis becomes dominant. [Smithy specification](https://smithy.io/2.0/spec/index.html) |

## Important risks a library comparison alone would miss

1. **Presence is not null.** Distinguish absent, explicit null, empty string and UNKNOWN. Do not allow Serde defaults or Pydantic defaulted fields to mint plausible state.
2. **Format is not always a hard check.** JSON Schema Draft 2020-12 separates `format-annotation` and `format-assertion`; build deliberately with format assertions on where required. Verify Rust/Python/TS parity.
3. **Numeric serialization differs.** Large integers, decimal money, float NaN/Infinity, timestamps with offsets, canonical date-only fields and precision can diverge across JS, Rust, Python. Money must be integer minor units + ISO currency or explicit decimal strings, never silently rounded float.
4. **String formats and regex are not universally equal.** Regex dialects, unicode normalization, IDNA, URI parsing and special field annotations vary. Use a conservative portable subset and shared negative fixtures.
5. **Discriminated unions need a real discriminator.** Ensure closed schema for each variant, explicit `kind` and independent negative tests, not ambiguous union coercion.
6. **Open-world versus closed-world schemas are domain decisions.** Reject unknown keys by default on **commands, claims, authorization and effects**; allow explicitly namespaced extension maps only for forward-compatible observations. Avoid unexpected global legacy rejections.
7. **Schema validates structure, not truth.** A perfectly well-formed fake evidence URL or forged signature cannot settle a FLOW/KARMA obligation. Independent provenance, existence, cryptography, authorization, source and effect still required.
8. **Custom Pydantic/Garde validators do not travel automatically.** Where domain invariants cannot be expressed in the common schema, publish versioned semantic validation rules with differential fixtures, implement in native runtimes, and never falsely advertise round-trip equivalence.
9. **Generator output is not normative merely because it compiles.** Pin compiler and schema versions; compare deterministic canonical output/digests; schema compilation and contract-compatibility both gate promotion.
10. **External fetches are a supply-chain surface.** No network `$ref` resolution at validation time on privileged paths. Use locally pinned, digested approved bundles; impose depth/size/time limits.

## Estate-specific reconciliation (source inspected 2026-11-14)

- `docs/decisions/0042-one-schema-at-every-boundary.md` already decides to extend **`bin/intent-compile` + `schema/intent/*.schema.json`** and avoid a second validator. Its three boundaries are B1 decode, B2 execution-argument validation and B3 repair receipts.
- `bin/schema-conformance` contains a legacy ratchet. Historic measurements show existing violations; *do not infer current counts from 2026-10-25 history*. Strict migration without a clean cohort would turn a schema mandate into a legitimate-work outage.
- `platform/estate/protocolkit/SPEC.md` defines typed stages, ingress/egress and audit; it does not establish live integration at every runtime.
- `chidionyema/argon/policy/turn.rego` enforces a separate structured turn packet. A conformance matrix and explicit translation are needed; do not duplicate the verifier in IDP.
- Rust, Python and TypeScript components share agent claims/events and effects. For their shared **JSON** boundary, the published schema is the canonical artifact. Rust-generated and Python-generated private types are implementation details except at a language-owned boundary with explicit wire artifact approval.
- The previous `Pedantic Schema` source spec said *no new Pydantic/BAML registry as parallel authority*. This means **no duplicate registry**, not **ban Pydantic** as a local library.

## Normative contract shape for any NEW shared JSON boundary

- `$schema`: pinned Draft 2020-12; stable `$id`; `title`, `description`; explicit domain `kind`, `schema_version`.
- Envelope: `instruction_id`, `correlation_id`, `causation_id`, `actor`, `effect_scope`, `source_sha`, `policy_digest`, `idempotency_key`, timestamp with declared timezone, `verdict` (PASS/FAIL/BLIND or typed domain state), `evidence` as structured refs; disclose `UNKNOWN` explicitly.
- `type`, `required`, `additionalProperties: false` for effect-bearing commands, no hidden coercion and explicitly typed nullability; `format` assertion where security-critical; limits on nested depth/array length/string length and numeric ranges; no secrets or personal data in public receipts.
- Schema and semantic validation must be independent of the untrusted output and operate on the actual effect boundary.

**Illustrative minimal JSON Schema (shape only; not a claim of current runtime deployment):**

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://schemas.meridian.example/estate/task-command/v1",
  "type": "object",
  "additionalProperties": false,
  "required": ["schema_version","instruction_id","action","idempotency_key"],
  "properties": {
    "schema_version": {"const":"1.0.0"},
    "instruction_id": {"type":"string","minLength":1},
    "action": {"enum":["domain.lookup","domain.quote"]},
    "idempotency_key": {"type":"string","minLength":16}
  }
}
```

The `example` domain is deliberately non-resolvable placeholder; canonical $ids MUST be provisioned in the existing schema registry before use.

## Decision matrix (qualitative engineering assessment, not benchmark)

| Need | Primary choice | Why not substitute |
| --- | --- | --- |
| One common contract for JSON across Python/Rust/TypeScript and agents | JSON Schema 2020-12 | Language-native Python/Rust classes cannot be the universal common format. |
| Python-only internal domain models | Pydantic v2 | Native validators and type ergonomics; export and diff any published contract. |
| Rust-only internal domain models | Serde + Schemars + Garde when required | Native high-performance types; no Python runtime. |
| Shared HTTP endpoints | OpenAPI 3.1+ with referenced canonical JSON Schemas | HTTP-specific operations and auth descriptions. |
| High-volume typed internal RPC/events | Protobuf + Buf (pilot only) | Binary evolution and generation; not necessary for all agent JSON or LLM schema output. |
| Declarative configuration/constraints | CUE in bounded pilot | Valuable for overlay/unification, but do not create second estate policy authority. |
| Arbitrary domain semantic rules | Versioned native validators and differential cross-language fixtures | No general-purpose schema alone proves arbitrary code-defined semantics. |

## Falsifiable proof-of-concept before constitutional enforcement

1. Select **three authentic cross-runtime payloads**: IDP/Argon instruction packet, Legion provider-capacity decision and Concierge domain checkout hold. Derive their *current* actual accepted payloads (not fixtures invented solely for the demo).
2. Publish each under a single versioned schema in the existing source registry. Generate Rust types using Typify and Python models using existing approach, or publish generated schema from the documented authoritative owner; create TypeScript typing/validator binding. Preserve one approved digest.
3. Differential corpus across all three runtimes: at least **20 valid + 30 invalid cases per payload** for unknown/missing/null/type/enum/decimal/date/format/renamed-fields/unknown version/confusable strings/deep objects. Every runtime must agree on ALLOW/REFUSE/BLIND for the same wire payload and authenticated context.
4. Mutation tests: remove `additionalProperties: false`, skip format validation, replace schema with untrusted patch, turn parser off, accept unknown schema_version, hide repair status. Each mutation must be killed by a negative test.
5. Evolution: additive optional field, required field, rename, change enum, delete field; check producer/consumer cross-version and explicit migration. For Protobuf pilot, run `buf breaking` against current main and ProtoJSON differential.
6. Canary: run as read-only shadow verdict first, collect false positive and false negative rates, then enforce **only on a proven clean effect-scoped cohort**. Preserve the established baseline ratchet for old intents.
7. Acceptance: zero disagreement on the supported feature subset; valid legacy-safe path continues; the former invalid operation fails before model/cost/commit; release receipt reports policy SHA + source SHA + schema digest, observed real caller outcome and rollback condition.

## Decision and open qualifications

**Recommended:** universal **contract standard** = JSON Schema Draft 2020-12 for shared JSON messages; **not** universal programming language or a new validator package. Local Pydantic, Serde/Schemars/Garde, TS validators, Argon Rego policy and selected Protobuf contracts plug into the SAME existing trusted effect-door governance. The institution mandates **schema fidelity and portable observability**, not use of a single library.

This is an architectural research outcome, not a verified estate-wide rollout. Any proposal to eliminate or retain existing validators requires actual dependency-graph and live-path proof, not an assertion of duplication.
