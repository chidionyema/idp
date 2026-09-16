# Token Efficiency Roadmap for Pi Agents

**Status:** 8 Critical mechanisms identified, 0/8 implemented

## Mechanism Tickets

### TIER 1: Highest ROI (Stop the Bleeding)

#### Ticket 1: pi-cache-guardian (Prompt Cache Drift)
- **Impact:** 25% token reduction on 10-turn conversation
- **Status:** TODO
- **Integration:** Hook into Claude Code `before_agent_start`
- **Implementation:**
  - Capture system prompt byte-identically on turn 1
  - Restore on every turn
  - Reorder prompt (stable content first)
  - Measure cache hit rate (target: >90%)
- **Verification:** `/cache-guardian` shows per-turn stats
- **Effort:** 2h

#### Ticket 2: pi-token-killer / RTK (Tool Output Compression)
- **Impact:** 60-90% reduction on bash commands
- **Status:** TODO
- **Integration:** Intercept bash tool calls in idp-exec
- **Implementation:**
  - Map commands: cat → rtk read, rg → rtk grep
  - Compress output before context injection
  - Fail-open if RTK missing
- **Verification:** `rtk gain` shows savings
- **Effort:** 3h

#### Ticket 3: pi-mcp-adapter (MCP Schema Bloat)
- **Impact:** 70-97% reduction on tool definitions
- **Status:** TODO
- **Integration:** Replace MCP server schemas with proxy tool
- **Implementation:**
  - Single ~200-token proxy tool
  - On-demand schema discovery
  - Lazy server startup
- **Verification:** Compare schema token count before/after
- **Effort:** 4h

### TIER 2: Context Discipline

#### Ticket 4: pi-dynamic-context-pruning (Context Replay)
- **Impact:** Eliminates duplicate tool outputs
- **Status:** TODO
- **Integration:** Hook after each agent turn
- **Implementation:**
  - Deduplication (same tool, same args)
  - Compression to technical summary
  - Configurable thresholds (80% nudge, 40% stop)
- **Verification:** Track context window size per turn
- **Effort:** 4h

#### Ticket 5: pi-compaction-manager (Early Compaction)
- **Impact:** Avoid late compaction, improve density
- **Status:** TODO
- **Integration:** Override Pi's default compaction timing
- **Implementation:**
  - Cap effective context (e.g., 128k on 1M model)
  - Trigger at 64k (before default)
  - Keep recent 20k tokens
- **Verification:** Check compaction triggers vs default
- **Effort:** 2h

### TIER 3: Leverage Layer

#### Ticket 6: SoL-Pi Integration (NVIDIA Four Mechanisms)
- **Impact:** 45-64% token reduction, retains 94% score
- **Status:** TODO
- **Integration:** Add as optional Pi extension
- **Mechanisms:**
  1. Action Fusion - combine edit + validation in one call
  2. ObservationPack - stable handles for repeated outputs
  3. Evidence-Preserving Reducer - compress logs with source matching
  4. Online Context Compact - integrate with Pi's native compaction
- **Verification:** EdgeBench score + token count
- **Effort:** 8h (each mechanism opt-in)

#### Ticket 7: TokenBudgetOrchestrator (Budget Governance)
- **Impact:** Prevent runaway agents, 50-54% cost reduction
- **Status:** TODO
- **Integration:** Sit between Claude Code and LLM provider
- **Implementation:**
  - Per-agent budget enforcement
  - Routing rules: Haiku → drafts, Sonnet → reviews, Opus → QA
  - Auto-reset (hourly/daily/weekly/monthly)
  - Block/route/warn on limit hit
- **Verification:** Cost tracking, per-model distribution
- **Effort:** 6h

### TIER 4: Advanced (Training-Time)

#### Ticket 8: Gisting (Prompt Compression)
- **Impact:** 4:1 system prompt reduction
- **Status:** RESEARCH ONLY (requires training embeddings)
- **Note:** Not a Pi extension; requires knowledge distillation
- **Alternative:** Simple prompt engineering for static content
- **Effort:** N/A (training phase, not this sprint)

## Three-Role Architecture

**Apply to pi agent stack:**

| Role | Authority | Constraint | Maps To |
|------|-----------|-----------|---------|
| Executor | Acts on tasks | Cannot self-judge | Pi agent doing work |
| Optimizer | Improves executor | Cannot execute | SoL-Pi auto-research loops |
| Governor | Validates outputs | Cannot produce | TokenBudgetOrchestrator + verif hooks |

## Implementation Order

**CRITICAL PATH (Complete before N=1 proof):**
1. ✅ Claude Code hook (50d4d390)
2. → Ticket 1: pi-cache-guardian (cache hits)
3. → Ticket 2: pi-token-killer (bash compression)
4. → Ticket 3: pi-mcp-adapter (schema bloat)
5. → Ticket 7: TokenBudgetOrchestrator (budget limits)

**Then validate N=1 proof with all 4 in place.**

**FOLLOW-UP (Context discipline):**
6. Ticket 4: pi-dynamic-context-pruning
7. Ticket 5: pi-compaction-manager
8. Ticket 6: SoL-Pi (mechanisms 1-4)

**Ticket 8 (Gisting) is research-phase only.**

## Estimated Total Effort
- Tier 1 (1,2,3): 9h
- Tier 2 (4,5): 6h
- Tier 3 (6,7): 14h
- **Total: 29h for full stack (7 implementable mechanisms)**

## Success Metrics
- Cache hit rate: >90%
- Token reduction: 45-64% vs baseline
- Cost reduction: 50-54%
- Score retention: >94%
- Budget enforcement: 100% (no runaway agents)

## Integration Points
- `before_agent_start`: pi-cache-guardian init
- `after_tool_call`: pi-token-killer compression
- `after_agent_turn`: pi-dynamic-context-pruning, budget check
- `on_context_full`: pi-compaction-manager trigger
- MCP server init: pi-mcp-adapter proxy
- LLM call: TokenBudgetOrchestrator routing

## Status Dashboard
```
Ticket  Mechanism                    Status  Effort  ETA
1       pi-cache-guardian            TODO    2h      
2       pi-token-killer (RTK)        TODO    3h      
3       pi-mcp-adapter               TODO    4h      
4       pi-dynamic-context-pruning   TODO    4h      
5       pi-compaction-manager        TODO    2h      
6       SoL-Pi (4 mechanisms)        TODO    8h      
7       TokenBudgetOrchestrator      TODO    6h      
8       Gisting (research)           HOLD    N/A     
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total                                         29h     
```
