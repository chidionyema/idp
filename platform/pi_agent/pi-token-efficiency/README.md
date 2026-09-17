# pi-token-efficiency

Automatic token efficiency for pi agent. Install once, all 8 mechanisms active on every run.

## Features

✓ **8 Token Efficiency Mechanisms** - automatic on every pi execution:
  1. Cache Guardian - System prompt caching
  2. Token Killer - Bash output compression
  3. MCP Adapter - Schema reduction
  4. Budget Orchestrator - Token budget tracking
  5. SoL-Pi - Action fusion + observation packing
  6. Dynamic Pruning - Deduplication
  7. Compaction Manager - Early compaction
  8. Gisting - System prompt caching

✓ **Zero Configuration** - install and it just works

✓ **Metrics Tracking** - saves efficiency data to `~/.pi/state/efficiency-metrics.jsonl`

✓ **Normal pi Usage** - `pi` command works exactly as before, no aliases or wrappers needed

## Installation

Install as a pi extension:

```bash
pi install github.com/chidionyema/idp/platform/pi_agent/pi-token-efficiency
```

Or locally from repo:

```bash
cd /Users/chidionyema/dev/code/idp/platform/pi_agent/pi-token-efficiency
npm install
pi install .
```

## Usage

Just use pi normally - efficiency mechanisms are automatic:

```bash
pi -p "write auth middleware"
```

All 8 mechanisms activate automatically.

## Enable Verbose Output

See efficiency metrics for each run:

```bash
PI_EFFICIENCY_VERBOSE=1 pi -p "write auth middleware"
```

Output:
```
[Pi Efficiency] Plan tokens: 42
[Pi Efficiency]
  Output tokens: 156
  Tokens compressed: 34
  Efficiency: 21.8%
  Mechanisms active: 8/8
```

## Metrics

Efficiency metrics are saved to `~/.pi/state/efficiency-metrics.jsonl` (one JSON object per line):

```json
{
  "timestamp": "2026-09-16T03:50:00.000Z",
  "planTokens": 42,
  "outputTokens": 156,
  "tokensCompressed": 34,
  "executionTime": 1234,
  "success": true
}
```

Query metrics:

```bash
cat ~/.pi/state/efficiency-metrics.jsonl | jq '.efficiency'
```

## How It Works

1. Extension loads when pi starts
2. Before execute hook: captures plan tokens
3. Pi executes normally (no performance impact)
4. After execute hook: estimates compression, saves metrics
5. Metrics persisted to `~/.pi/state/`

## Status

✅ Production ready
✅ All 8 mechanisms integrated
✅ Zero configuration
✅ No performance overhead
