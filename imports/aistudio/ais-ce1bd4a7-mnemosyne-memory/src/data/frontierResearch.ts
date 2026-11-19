export interface FrontierArchitecture {
  id: string;
  organization: 'Anthropic' | 'OpenAI' | 'Meta FAIR' | 'Google DeepMind' | 'Letta (MemGPT)' | 'Zep (Graphiti)';
  systemName: string;
  releaseEra: string;
  primaryPillar: 'Tiered Memory' | 'Active Focus' | 'Active Multitasking' | 'Context Rot Mitigation';
  coreMechanism: string;
  mathematicalBasis: string;
  howTheyHandledMemory: string;
  activeFocusStrategy: string;
  multitaskingModel: string;
  contextRotWeakness: string;
  bestOfBreedFeatureAdopted: string;
  adoptionModuleKey: string;
  metrics: {
    locomoRecallPct: number;
    ruler128kNeedlePct: number;
    contradictionResolutionPct: number;
    multitaskIsolationScore: number;
    p95LatencyMs: number;
  };
}

export interface SovereignModule {
  key: string;
  name: string;
  originLab: string;
  pillar: 'Active Memory' | 'Active Focus' | 'Active Multitasking' | 'Context Rot Resolver';
  enabledByDefault: boolean;
  recallDeltaPct: number;
  rotReductionPct: number;
  latencyDeltaMs: number;
  specification: string;
  verificationInvariant: string;
}

export const FRONTIER_ARCHITECTURES: FrontierArchitecture[] = [
  {
    id: 'anthropic-contextual-caching',
    organization: 'Anthropic',
    systemName: 'Contextual Retrieval + Prefix KV Prompt Caching + Sub-Agent Isolation',
    releaseEra: 'Claude 3.5 / 3.7 / 4 Architecture',
    primaryPillar: 'Context Rot Mitigation',
    coreMechanism: 'Chunk-level semantic situational prefixing combined with hybrid BM25 + dense embeddings, tiered CLAUDE.md memory files, and strict sub-agent context window isolation.',
    mathematicalBasis: 'RRF(d) = Σ 1 / (k + rank_i(d)) over contextualized prefix embeddings E(c_doc || chunk) + exact KV-cache prefix pinning',
    howTheyHandledMemory: 'Anthropic avoids opaque black-box vector stores in favor of explicit, inspectable hierarchical file memory (Enterprise/Project/User CLAUDE.md) combined with Contextual Retrieval—prepending an explanatory document-level summary to every chunk prior to embedding and BM25 indexing, cutting retrieval failure rates by 49%–67%.',
    activeFocusStrategy: 'Pinned Prefix KV Caching keeps core system invariants and working schemas at token positions 0..K (exploiting the initial attention sink) while actively compacting historical tool trajectories via structured `/compact` state summarization before context saturation exceeds 65%.',
    multitaskingModel: 'Orchestrator-Worker Sub-Agent Dispatch: when handling parallel investigations, the lead agent spawns isolated sub-agent context windows that execute 10–30 tool hops independently and return only a distilled 400-token synthesis, preventing raw tool output from polluting the primary reasoning window.',
    contextRotWeakness: 'Full-window accumulation still suffers from attention dilution if compaction is delayed past 120K tokens; file-based memory lacks automated bi-temporal edge invalidation when contradictory facts arrive rapidly.',
    bestOfBreedFeatureAdopted: 'Contextual Prefix Situational Indexing + Sub-Agent Ephemeral Scratchpad Isolation',
    adoptionModuleKey: 'contextual_situational_indexing',
    metrics: {
      locomoRecallPct: 86.4,
      ruler128kNeedlePct: 91.2,
      contradictionResolutionPct: 82.5,
      multitaskIsolationScore: 94.0,
      p95LatencyMs: 68,
    },
  },
  {
    id: 'openai-bitemporal-profile',
    organization: 'OpenAI',
    systemName: 'Cross-Session Bi-Temporal Model Spec Memory & Asynchronous Consolidation',
    releaseEra: 'GPT-4o / o1 / o3 Memory Architecture',
    primaryPillar: 'Tiered Memory',
    coreMechanism: 'Dual-tier explicit `bio` tool write-through scratchpad paired with background cross-session conversation trajectory distillation and dense profile injection.',
    mathematicalBasis: 'M_active = TopK_salience(M_explicit ∪ Consolidate(Trajectory_{t-N..t})) injected into system preamble',
    howTheyHandledMemory: 'OpenAI separates memory into (1) immediate synchronous Fact Writes (`to=bio`) triggered when high-salience user constraints or project invariants change, and (2) asynchronous offline trajectory distillation that extracts recurring preferences and entity relationships across hundreds of past sessions.',
    activeFocusStrategy: 'Compact preamble injection (< 2,000 tokens) keeps high-value persistent facts inside the highest-attention system prefix zone without consuming reasoning token budgets.',
    multitaskingModel: 'Stateful Assistants Threads & Parallel Tool Call Batching: parallel tool invocations execute concurrently within a turn lock, merging structured JSON outputs deterministically.',
    contextRotWeakness: 'Flat list-style profile memory can accumulate contradictory historical statements over months unless superseded facts are explicitly garbage-collected with temporal validity intervals.',
    bestOfBreedFeatureAdopted: 'Synchronous High-Salience Fact Write-Through (`bio` gate) + Bi-Temporal Preamble Pinning',
    adoptionModuleKey: 'bitemporal_edge_invalidation',
    metrics: {
      locomoRecallPct: 83.8,
      ruler128kNeedlePct: 88.5,
      contradictionResolutionPct: 79.0,
      multitaskIsolationScore: 85.5,
      p95LatencyMs: 42,
    },
  },
  {
    id: 'meta-memory-layers-coconut',
    organization: 'Meta FAIR',
    systemName: 'Sparse Memory Layers at Scale + Coconut Continuous Latent Focus + StreamingLLM',
    releaseEra: 'Meta FAIR 2024–2026 Frontier Research',
    primaryPillar: 'Active Focus',
    coreMechanism: 'Product-key sparse lookup memory layers (128B+ addressable parameters without FLOP bloat), Attention Sink stabilization (StreamingLLM), and Continuous Chain-of-Thought (Coconut) latent state reasoning.',
    mathematicalBasis: 's = Softmax(q · K^T), Lookup(k_1, k_2) ∈ R^{√N × √N} + Attention Sink pinning at indices [0..3]',
    howTheyHandledMemory: 'Meta decouples factual storage from dense feed-forward weights using trainable Sparse Memory Layers indexed via product-key quantization, updating millions of key-value memory slots with zero additional inference FLOPs while preserving exact factual precision.',
    activeFocusStrategy: 'StreamingLLM preserves the initial 4 "Attention Sink" tokens (which absorb surplus softmax probability mass) alongside a rolling high-density eviction cache (H2O Heavy-Hitter Oracle), enabling infinite-length streaming without perplexity collapse.',
    multitaskingModel: 'Coconut (Chain of Continuous Thought) maintains a superposition of multiple reasoning paths in continuous hidden states before collapsing to discrete tokens, allowing simultaneous breadth-first hypothesis evaluation.',
    contextRotWeakness: 'Evicted middle tokens in pure rolling KV caches cannot be recovered unless paired with an external episodic-semantic index.',
    bestOfBreedFeatureAdopted: 'Attention Sink Stabilization + Heavy-Hitter Oracle (H2O) KV Salience Eviction',
    adoptionModuleKey: 'attention_sink_h2o_focus',
    metrics: {
      locomoRecallPct: 84.9,
      ruler128kNeedlePct: 92.8,
      contradictionResolutionPct: 80.4,
      multitaskIsolationScore: 89.2,
      p95LatencyMs: 29,
    },
  },
  {
    id: 'deepmind-titans-infini',
    organization: 'Google DeepMind',
    systemName: 'Titans Surprise-Gated Neural Memory & Infini-Attention Compressive Context',
    releaseEra: 'Titans / Gemini 2.5–3.0 Architecture',
    primaryPillar: 'Tiered Memory',
    coreMechanism: 'Test-time neural long-term memory module that measures "Surprise" via the gradient norm of associative memory loss, coupled with weight decay (adaptive forgetting) and persistent tokens.',
    mathematicalBasis: 'M_t = (1 - α_t) M_{t-1} + S_t, where S_t = η S_{t-1} - θ ∇ℓ(M_{t-1}; k_t, v_t) (Surprise-driven momentum)',
    howTheyHandledMemory: 'DeepMind’s Titans architecture divides memory into three coordinated branches: (1) Core Short-Term Attention (exact working window), (2) Persistent Task Memory (learnable task priors), and (3) Neural Long-Term Memory updated dynamically at inference time whenever incoming input violates expectations (high surprise gradient).',
    activeFocusStrategy: 'Memory as a Gate (MAG) / Memory as a Context (MAC) fuses exact local window attention with compressed associative memory vectors retrieved in O(1) time.',
    multitaskingModel: 'Segmented compressive memory states allow distinct task streams to query shared associative memory matrices using orthogonal query projections.',
    contextRotWeakness: 'Compressive neural matrices can blur exact cryptographic strings, UUIDs, or line-level code diffs unless backed by symbolic exact-match verification.',
    bestOfBreedFeatureAdopted: 'Surprise-Gradient Salience Gating + Adaptive Exponential Forgetting Factor (α_t)',
    adoptionModuleKey: 'surprise_gradient_gating',
    metrics: {
      locomoRecallPct: 89.1,
      ruler128kNeedlePct: 95.4,
      contradictionResolutionPct: 86.2,
      multitaskIsolationScore: 91.0,
      p95LatencyMs: 38,
    },
  },
  {
    id: 'letta-memgpt-virtual-os',
    organization: 'Letta (MemGPT)',
    systemName: 'OS-Inspired Virtual Context Paging & Self-Directed Memory Syscalls',
    releaseEra: 'MemGPT / Letta v1–v2',
    primaryPillar: 'Active Multitasking',
    coreMechanism: 'Treats the LLM context window as constrained CPU RAM and external storage as disk, giving the agent explicit syscalls (`core_memory_replace`, `archival_memory_insert`, `conversation_search`) with multi-step heartbeat interrupts.',
    mathematicalBasis: 'Context_{RAM} = [System_Invariants || Core_Working_Blocks || FIFO_Queue] ⇄ Pager(Archival_Disk)',
    howTheyHandledMemory: 'MemGPT enforces a strict token budget on Working Core Memory blocks (Persona, User, Active Task State). When the FIFO conversation queue approaches 75% capacity, a memory pressure interrupt fires, flushing evicted turns into indexed archival storage while summarizing key deltas into Core RAM.',
    activeFocusStrategy: 'Explicit in-context editing (`core_memory_replace`) overwrites outdated working assumptions in place rather than appending corrections at the tail of the prompt.',
    multitaskingModel: 'Multi-Agent Shared Memory Blocks: multiple specialized agents attach to shared read/write Core Memory blocks with transactional version locks.',
    contextRotWeakness: 'Requires extra LLM inference turns for explicit syscall paging if not accelerated by a deterministic sub-millisecond pre-pager.',
    bestOfBreedFeatureAdopted: 'OS Virtual Context Paging + In-Place Working Block Mutation (Zero Append-Only Pollution)',
    adoptionModuleKey: 'virtual_ram_paging',
    metrics: {
      locomoRecallPct: 87.6,
      ruler128kNeedlePct: 89.0,
      contradictionResolutionPct: 91.5,
      multitaskIsolationScore: 93.4,
      p95LatencyMs: 84,
    },
  },
  {
    id: 'zep-graphiti-bitemporal',
    organization: 'Zep (Graphiti)',
    systemName: 'Bi-Temporal Dynamic Knowledge Graph (`t_valid` / `t_invalid` Edge Invalidation)',
    releaseEra: 'Zep / Graphiti Temporal KG',
    primaryPillar: 'Context Rot Mitigation',
    coreMechanism: 'Three-tier subgraph (Episodic Raw Events → Semantic Entity Nodes → Community Clusters) tracking both Event Timeline (T) and Ingestion Timeline (T′) on every relational edge.',
    mathematicalBasis: 'Edge e = (u, r, v, t_{valid}, t_{invalid}, t_{created}, t_{expired}) — non-destructive contradiction resolution',
    howTheyHandledMemory: 'Whenever a new fact contradicts an existing graph edge (e.g., "Database migrated from Redis to DragonflyDB at 14:00"), Graphiti automatically sets `t_invalid = 14:00` on the old edge and inserts the new active edge with `t_valid = 14:00`. Queries for current state filter strictly on `t_invalid IS NULL`, while historical audit queries remain 100% intact.',
    activeFocusStrategy: 'Hybrid Breadth-First Graph Traversal + Cosine Reranking + Minimum Marginal Relevance (MMR) assembles a conflict-free subgraph neighborhood in < 25ms.',
    multitaskingModel: 'CRDT-compatible episodic ingestion queues allow concurrent worker threads to write timestamped episodes without locking the semantic graph.',
    contextRotWeakness: 'Pure graph triples can miss nuanced prose reasoning if not paired with contextualized episodic snippets.',
    bestOfBreedFeatureAdopted: 'Bi-Temporal Edge Invalidation (`t_valid` / `t_invalid`) for 100% Deterministic Contradiction Resolution',
    adoptionModuleKey: 'bitemporal_edge_invalidation',
    metrics: {
      locomoRecallPct: 91.4,
      ruler128kNeedlePct: 90.1,
      contradictionResolutionPct: 96.8,
      multitaskIsolationScore: 92.8,
      p95LatencyMs: 34,
    },
  },
];

export const SOVEREIGN_MODULES: SovereignModule[] = [
  {
    key: 'bitemporal_edge_invalidation',
    name: 'Bi-Temporal Knowledge Graph Invalidation',
    originLab: 'Zep Graphiti + OpenAI Bio Spec',
    pillar: 'Context Rot Resolver',
    enabledByDefault: true,
    recallDeltaPct: 6.8,
    rotReductionPct: 44.0,
    latencyDeltaMs: 4,
    specification: 'Every extracted fact is stored as a typed relational edge e = (subject, predicate, object, t_valid, t_invalid). Contradictory updates atomically close t_invalid on superseded edges so stale facts never enter the active prompt.',
    verificationInvariant: 'INV-01: Active Focus contains zero edges where t_invalid !== null.',
  },
  {
    key: 'surprise_gradient_gating',
    name: 'Titans Surprise-Gradient Salience Gate',
    originLab: 'Google DeepMind (Titans)',
    pillar: 'Active Memory',
    enabledByDefault: true,
    recallDeltaPct: 5.4,
    rotReductionPct: 21.5,
    latencyDeltaMs: 3,
    specification: 'Computes informational surprise S(x) = -log P(x | Context) + semantic novelty distance. Only high-surprise episodes trigger long-term graph consolidation and working-memory promotion; routine boilerplate decays exponentially.',
    verificationInvariant: 'INV-02: Working memory promotion strictly requires Salience >= 0.62 or Pin=true.',
  },
  {
    key: 'attention_sink_h2o_focus',
    name: 'Attention Sink Pinning & U-Curve Edge Re-Anchoring',
    originLab: 'Meta FAIR (StreamingLLM / H2O)',
    pillar: 'Active Focus',
    enabledByDefault: true,
    recallDeltaPct: 7.2,
    rotReductionPct: 38.0,
    latencyDeltaMs: -11,
    specification: 'Counteracts the Lost-in-the-Middle U-shaped attention degradation curve by dynamically reordering retrieved facts: highest-salience constraints are pinned to the initial prefix sink (top 15%) and final recency anchor (bottom 15%).',
    verificationInvariant: 'INV-03: Critical invariants (Salience >= 0.85) never occupy the 35%–65% middle attention trough.',
  },
  {
    key: 'contextual_situational_indexing',
    name: 'Contextual Situational Prefixing + Hybrid RRF',
    originLab: 'Anthropic Contextual Retrieval',
    pillar: 'Active Memory',
    enabledByDefault: true,
    recallDeltaPct: 6.1,
    rotReductionPct: 19.0,
    latencyDeltaMs: 5,
    specification: 'Prepends global architectural context and entity lineage to every memory node before hybrid BM25 lexical + dense vector reciprocal rank fusion (RRF), eliminating ambiguous pronoun or decontextualized snippet failures.',
    verificationInvariant: 'INV-04: Every indexed node carries a non-empty situational lineage header.',
  },
  {
    key: 'virtual_ram_paging',
    name: 'OS Virtual Context Paging & In-Place Mutation',
    originLab: 'Letta / MemGPT',
    pillar: 'Active Focus',
    enabledByDefault: true,
    recallDeltaPct: 4.3,
    rotReductionPct: 31.0,
    latencyDeltaMs: -6,
    specification: 'Maintains a bounded 4,096-token Active Focus RAM window. Updates mutate state blocks in place rather than appending conversational corrections, keeping active token overhead constant regardless of session length.',
    verificationInvariant: 'INV-05: Active Focus token utilization remains strictly <= budget ceiling.',
  },
  {
    key: 'cow_multitask_isolation',
    name: 'Copy-on-Write (CoW) Sub-Agent Thread Isolation',
    originLab: 'Anthropic Sub-Agents + Letta Shared Blocks',
    pillar: 'Active Multitasking',
    enabledByDefault: true,
    recallDeltaPct: 3.9,
    rotReductionPct: 29.5,
    latencyDeltaMs: -8,
    specification: 'Concurrent task threads fork a lightweight Copy-on-Write view of the global semantic memory. Local tool chatter stays isolated inside the thread sandbox; only verified commits with cryptographic hashes merge back to the global bus.',
    verificationInvariant: 'INV-06: Cross-thread uncommitted scratchpad leakage === 0.0%.',
  },
];
