"""crew#340 incident, rung 4: langfuse-verify must read its probe back through
/api/public/v2/observations. Langfuse 4.x defaults to
LANGFUSE_MIGRATION_V4_WRITE_MODE=events_only, where /api/public/traces answers
404 "not available ... events_only mode". The probe polled that 404 for two
days and reported a silent drop that never happened."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_incident_crew340_probe_reads_back_via_v2_observations():
    src = (ROOT / "bin" / "langfuse-verify").read_text()
    reads = [
        line for line in src.splitlines()
        if "api/public/traces" in line and not line.lstrip().startswith("#")
    ]
    # the POST to otel/v1/traces is ingestion, not a read-back
    assert all("otel/v1/traces" in line for line in reads), reads
    assert re.search(r'api/public/v2/observations\?traceId=\$trace_id', src)
