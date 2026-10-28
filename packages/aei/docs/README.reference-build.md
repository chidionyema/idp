# Estate AEI — P0 Agent Execution Intelligence

An evidence-first, read-only execution intelligence reference implementation. Standard library only, Python 3.10+; no new observability stack.

**Included:** versioned event schema; bounded, secret-scrubbed metadata; append-only idempotent SQLite event ledger; nonblocking telemetry emitter; token-authenticated loopback API; execution waterfall; observed parent graph; run comparison; deterministic waste flags; coverage reports; mandatory observability manifest validation; BDD specification and automated tests; synthetic demo.

## Run

```bash
python -m unittest discover -s tests -v
python -m aei.contract examples/router.manifest.json
python -m aei.demo --db output/aei.sqlite3
export AEI_API_TOKEN="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
python -m aei.server --db output/aei.sqlite3
```

Open `http://127.0.0.1:8766/` and enter the token. No network services, external packages or GitHub credentials are required for the demo.

## Ingest an actual event

```python
from aei.client import Emitter
identity = dict(run_id='real-run-id',task_id='task-id',agent_id='agent-id',
                harness_id='harness-id',trace_id='trace-id',revision='git-sha')
emitter = Emitter('http://127.0.0.1:8766', token, identity)
emitter.emit('task.started', attributes={'status':'started'})
# ... execute work and instrument its real observable boundaries ...
emitter.emit('task.completed', attributes={'outcome':'verified'})
emitter.close()
print(emitter.stats())
```

## API

All routes require `Authorization: Bearer <AEI_API_TOKEN>`.

- `POST /api/events` — validated single event, 64 KiB maximum.
- `GET /api/runs` — latest runs.
- `GET /api/run?id=...` — raw evidence, deterministic evaluation and visualisation data.
- `GET /api/compare?a=...&b=...` — side-by-side evidence comparison, with explicit verification warning.
- `GET /health` — process/store reachability, not estate instrumentation coverage.

Read `RESEARCH.md` for repo findings, `features/aei.feature` for BDD scenarios, and `AGENT_HANDOFF.md` for production integration work.

## Security and accuracy

The server binds to loopback only. Attribute names are allowlisted, strings scrubbed, unknown fields rejected at ingestion. No prompt bodies, private reasoning, secrets, or arbitrary tool output should enter the event ledger. Metadata-only collection still needs access control and retention policy. No telemetry failure is allowed to block agent execution. Evaluator findings are *derived*, not source observations. Missing values remain unknown, not zero.
