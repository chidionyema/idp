# 0035. All ways: no single point of failure, every capability has many homes

Status: accepted, 2026-09-29 (founder).

## Context

On 2026-09-29 the laptop LLM router disrupted every agent session, all day. The founder's
sessions logged 235 session-stopping API errors in 24 hours: 83 "Connection refused" while the
router was down or restarting, 52 "Not logged in" while the relay sent no credential upstream, and
80 "Request timed out" since midday on a laptop at load 15-123 on 4 cores. One Python process on
one overloaded laptop sat in every session's path, so every fix to one cause (a lane, a key, a
restart) was followed by the next cause taking sessions down.

The first fix proposed was to move everything to the cloud and take the laptop out of the path. The
founder rejected it: "Our philosophy is All ways, so we need to move to cloud but retain laptop
capability. The estate has 2 macbooks and although this one does not have much resources, the
others do... The same way Otto has many homes the crew need many homes." "We don't allow for single
points of failure." "The platform demonstrates it: we aim for all ways." "We are model agnostic
and not anthropic." An earlier ruling applies
the same rule the other way (2026-09-26, `llm/config.yaml`): "if cluster breaks we are all
disabled", which is why the Claude relay was kept off the cluster.

## Decision

Every capability the founder depends on has several homes and fails over between them, on three
axes: hosts (OKE, cloud session runners, this MacBook, the second MacBook), model vendors
(Anthropic, DeepSeek, MiniMax, Gemini, Groq and the router's other lanes) and agent runtimes
(Claude Code, Codex, Gemini CLI, Otto). No home on any axis, the cloud and any single vendor
included, is a single point of failure.

1. Moving a capability to the cloud adds a home. The laptops keep the ability to run it.
2. Nothing we operate sits alone in a session's critical path. A router, relay or proxy in front of
   a session fails open to another home or another vendor within the same request.
3. Running work is never disrupted by a move. The new home is built beside the old one and proved
   in parallel with a failure test (kill or freeze a home under live traffic; sessions see zero
   errors). Only new work is sent to it, and rollback is pointing new work back.
4. A capability with one home is not finished. Its README names its homes, its failover, and the
   test that proves the failover.

## Consequences

- The router, voice-router, /fleet and the crew's sessions each need a second live home and a
  failover proof before the laptop stops being load-bearing: OKE plus a MacBook, or two MacBooks,
  and more than one model vendor and agent runtime behind each.
- The estate's model-agnostic framework (crew#568) is the vendor and runtime axis of this rule.
- AGENTS.md §12 carries this rule to every agent. Enforcement belongs in the gates, per AGENTS.md's
  own header; until a gate exists, reviewers refuse a change that makes a capability single-homed.
- Otto (hermes-agent) is the precedent: the crew gets the same many-homes treatment.
