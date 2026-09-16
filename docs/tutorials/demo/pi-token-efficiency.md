# Pi Token Efficiency Extension

Automatically applies 8 token efficiency mechanisms to every pi agent execution.

## Features
- Cache Guardian, Token Killer, MCP Adapter, Budget Orchestrator, SoL-Pi, Dynamic Pruning, Compaction Manager, Gisting
- Zero configuration
- Metrics tracked automatically

## Installation
```bash
pi install github.com/chidionyema/idp/platform/pi_agent/pi-token-efficiency
```

## Usage
```bash
pi -p "your task"
PI_EFFICIENCY_VERBOSE=1 pi -p "your task"  # See efficiency metrics
```

