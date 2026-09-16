# Estate DAG Generator

Generates the estate's data flow graph from live state.

## Overview

`estate-dag-gen` analyzes the platform state and generates a DAG (Directed Acyclic Graph) showing:
- Service dependencies
- Data flow paths
- Critical chains

## Usage

```bash
bin/estate-dag-gen
```

## Output

Generates a GraphML-compatible DAG file tracking dependency chains across services, workloads, and infrastructure.

## Integration

Part of the platform's estate compiler pipeline.
