# pennyd — Failure Mode & Effects Analysis

Taxonomy grounded in current research: LLM gateways fail in recurring classes —
streaming token protocols (mid-stream truncation, double-billing on retry),
cascading overload (thundering herds, failover storms, Retry-After ignored),
context asymmetry across fallback lanes, and silent observability gaps. Every
row below is either prevented by construction, handled at runtime, or
explicitly accepted with its bound. "Test" = automated test name.

## Input / client
| ID | Failure | Response | Test |
|---|---|---|---|
| F-IN-1 | Malformed JSON body | axum 4xx rejection, nothing billed | (extractor) |
| F-IN-2 | Missing/malformed auth | 400 | missing_auth_rejected |
| F-IN-3 | Unknown API key | 401 by default; opt-in `allow_unknown_keys` | unknown_key_rejected_by_default |
| F-IN-4 | Unknown model | 400 listing available aliases | unknown_model_lists_available |
| F-IN-5 | Oversized body (DoS/memory) | 413 via DefaultBodyLimit before any upstream exposure | oversized_body_rejected_413 |
| F-IN-6 | Key escapes to expensive model | per-key `allowed_models` ACL → 403 | model_acl_enforced_403 |

## Cache
| ID | Failure | Response | Test |
|---|---|---|---|
| F-CA-1 | Expired entry served | lazy expiry, never served | hit_and_expiry |
| F-CA-2 | Poisoned/corrupt entry | evict + serve fresh; never 400 a valid request | poisoned_cache_entry_falls_through |
| F-CA-3 | Alias fragmentation (same model, many keys) | cache keys on canonical provider/model | alias_resolves_and_caches |
| F-CA-4 | Capacity pressure | moka bounded LRU evicts cold entries; availability preserved (documented) | — |
| F-CA-5 | Stampede on cold key | concurrent duplicates may each bill once; bounded by budgets (accepted, documented) | — |

## Routing / upstream
| ID | Failure | Response | Test |
|---|---|---|---|
| F-RO-1 | Lane timeout | reqwest per-lane timeout → error → declared fallback | (implicit via breaker tests) |
| F-RO-2 | All lanes down | 502 AllLanesFailed, decision logged | declared_fallback_escalates_end_to_end |
| F-RO-3 | Lane flap | circuit breaker: N consecutive failures open the lane for cooldown | circuit_opens_after_threshold |
| F-RO-3b | Lane recovers | breaker closes after cooldown; lane serves again | circuit_recovers_after_cooldown |
| F-RO-4 | Deterministic 4xx retried across lanes | non-retryable stops the chain immediately — no amplification | deterministic_400_stops_chain_without_fallback |
| F-RO-5 | Oversized prompt for a lane | context-window fit check before routing; 400 naming the model | context_window_overflow_refused_before_routing |
| F-RO-6 | 429 from lane | RateLimited carries Retry-After; breaker opens for the advertised window | rate_limit_honors_retry_after |
| F-RO-7 | Thundering herd on a lane | per-lane bulkhead (max_inflight_per_lane); excess skips to fallback instantly | bulkhead_saturates_and_skips |
| F-RO-8 | Fallback cycle (A→B→A) | chain dedupe at resolution | (unit: resolve_chain) + unknown_fallback_rejected_at_load |
| F-RO-9 | Cross-model substitution | impossible by construction: resolved model → own lane; escalation only via explicit `fallbacks` | declared_fallback_escalates_end_to_end |
| F-RO-10 | Mid-stream upstream disconnect | stream truncates; client sees partial; no retry (no double-billing); never cached (accepted — see Streaming) | — |

## Streaming
| ID | Failure | Response | Test |
|---|---|---|---|
| F-ST-1 | stream=true on non-streaming dialect | lane skipped; if none capable → loud error, never silently buffered | streaming_skips_non_streaming_lanes |
| F-ST-2 | Streaming response cached | streams never enter cache (est. charge flagged `est:true`) | (code path) |
| F-ST-3 | Streamed usage unknown | input-estimate charge, flagged in decision log | streaming_passes_through_sse |
| F-ST-4 | Mid-stream failure after headers | connection terminates; partial output; counted as dropped in client, not billed beyond estimate (accepted) | — |

## Budget
| ID | Failure | Response | Test |
|---|---|---|---|
| F-BU-1 | Spend past daily limit | hard refusal 429, structured; never silent degrade | budget_refusal_is_loud |
| F-BU-2 | Day rollover | spend resets on day boundary | day_rollover_resets |
| F-BU-3 | Clock jumps backwards | monotonic day: no free reset | day_never_goes_backwards |
| F-BU-4 | Negative prices in config | refused at registry load | negative_prices_rejected |
| F-BU-5 | Estimate undershoot on streams | conservative input-only estimate, flagged (accepted bound) | — |

## Registry / config
| ID | Failure | Response | Test |
|---|---|---|---|
| F-RG-1 | Bad provider TOML | boot/refuse loud; watcher keeps last good registry | filename_is_law, (watcher logs) |
| F-RG-2 | Provider file deleted | hot reload shrinks registry within reload_interval_s | reload_after_file_delete |
| F-RG-3 | Unknown dialect/fallback/dup alias/dup id | load refuses, file+reason named | unknown_fallback_rejected_at_load, duplicate_alias_rejected |
| F-RG-4 | Missing lane env var | boot fails with the var named | (ProviderLane::new error path) |
| F-RG-5 | Misordered/invalid daemon config | validate() at load, loud | rejects_empty_keys |

## Decision log / observability
| ID | Failure | Response | Test |
|---|---|---|---|
| F-LOG-1 | Tamper/edit log | verify() names the broken seq; /health reports | tamper_detected_with_seq |
| F-LOG-2 | Torn write / crash mid-append | open() truncates to last valid record | torn_tail_recovered_on_open |
| F-LOG-3 | Log write I/O failure | reopen-once after rotation; failures counted in /health `dropped_decisions` | reopens_after_log_deleted |
| F-LOG-4 | Unbounded growth | operator logrotate (documented); chain verified across rotation | reopens_after_log_deleted |

## Concurrency
| ID | Failure | Response | Test |
|---|---|---|---|
| F-CON-1 | Hot reload mid-request | registry/router swapped as Arc; in-flight requests keep the old snapshot by construction | — |
| F-CON-2 | RwLock poison after panic | panic = bug; guarded critical sections hold no `.unwrap()`-panic paths while mutating shared state | — |
| F-CON-3 | Bulkhead counter skew | acquire/release paired on all paths (success, error, skip-before-acquire) | bulkhead_saturates_and_skips |
| F-CON-4 | Request storm on healthy lane | bulkhead admits up to cap; excess skips to fallback; budgets bound total | storm_64_concurrent_all_succeed_on_healthy_lane |

## Anthropic ingress
| ID | Failure | Response | Test |
|---|---|---|---|
| F-AI-1 | Malformed anthropic body | 400 with anthropic-shaped error envelope | messages_ingress_errors_are_anthropic_shaped |
| F-AI-2 | Cache fragmentation across edges | canonical body is the cache key — openai and anthropic clients share one namespace | messages_and_openai_share_cache_namespace |
| F-AI-3 | SSE event split across upstream chunks | buffered line parser; event boundaries recovered | sse_translation_split_chunks_and_done |
| F-AI-4 | Anthropic client routed to openai lane (stream) | SSE event-stream translation (message_start→message_stop) | messages_ingress_streaming_translates_sse |
| F-AI-5 | Upstream ends without [DONE] | well-formed close events emitted, stream terminates | sse_empty_stream_yields_wellformed_message |
| F-AI-6 | Wrong stop_reason vocabulary | finish_reason mapped (stop→end_turn, length→max_tokens, tool_calls→tool_use) | response_maps_stop_reasons |

## Integration proof
| ID | Failure | Response | Test |
|---|---|---|---|
| F-INT-1 | Subsystems drift apart (cache/ledger/log/auth disagree) | `full_pipeline_proof_everything_works_together` cross-asserts ledger + chain verify + /health + dropped==0 in one session | full_pipeline_proof_everything_works_together |

## Failure pack (structured format: id | trigger | expected | detected_by | test | recovery)
| id | service | trigger | expected | detected_by | test | recovery |
|---|---|---|---|---|---|---|
| FP-P0-2 | anthropic-ingress | request carries tools/tool_choice | tools mapped to openai functions | unit probe | anthropic_tool_catalog_reaches_the_openai_lane | n/a |
| FP-P0-3 | anthropic-ingress | streamed tool-call deltas | tool_use blocks + stop_reason=tool_use | unit probe | streamed_tool_calls_produce_tool_use_blocks | fall back to non-streaming |
| FP-P0-4 | decision-log | any request | key_fp only, never raw key | log audit | bearer_key_never_reaches_the_decision_log | rotate key if seen |
| FP-P0-5 | budget | restart mid-day / overrun | spend persists; reserve pre-dispatch; overrun exhausts | persisted file + 429 | spend_survives_restart, settle_records_overrun_and_exhausts | raise budget or next day |
| FP-P0-6 | cache | same request via both edges | one canonical entry | hit-rate metric | messages_and_openai_share_cache_namespace | n/a |
| FP-P1-5 | decision-log | tamper + restart | tampered_at visible, not erased | /health.tampered_at | tampering_is_visible_after_restart | investigate host |
| FP-P1-7 | registry | provider file deleted | hot reload drops lane | reload error log | deletion_changes_fingerprint | restore file |
| FP-P1-8 | lanes | streaming 429 | Retry-After honored | breaker window | rate_limit_honors_retry_after | wait window |
| FP-P1-9 | anthropic-ingress | auth/ACL/rate/upstream errors | matching error kind | response audit | anthropic_error_kinds_match_failures | n/a |

## Explicitly accepted bounds (documented, not hidden)
- Cold-key stampede: N concurrent identical requests may each bill once. Bound: budgets. Fix path: single-flight.
- Stream truncation cost: estimate may undershoot true usage; flagged `est:true`, input-only.
- No proactive/latency-based breaker: reactive breaker + per-lane timeout + bulkhead is the v1 position.
- Anthropic-protocol edge ingress: not yet built (tracked) — Claude Code cannot enter via /v1/messages yet.
