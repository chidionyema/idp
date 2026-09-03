"""crew#340: with 6 rows of trace data stored, ClickHouse sat at 86-88 percent CPU idle on the
2 vCPU host, trace_log held 6.6 million rows and a 44 MiB insert into events_full took 15-39 s
and hit TIMEOUT_EXCEEDED on the events_core_mv push. Removing the sampling profiler and the
per-second metric tables took idle CPU to 16 percent. Rung 4, incident test: the low-memory
override keeps them removed and keeps query_log, which this incident was diagnosed from."""

import pathlib
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parent.parent
XML = ROOT / "observability" / "clickhouse-low-memory.xml"


def test_incident_crew340_query_profiler_is_off_in_default_profile():
    root = ET.parse(XML).getroot()
    prof = root.find("./profiles/default")
    assert prof is not None
    for key in (
        "query_profiler_real_time_period_ns",
        "query_profiler_cpu_time_period_ns",
    ):
        node = prof.find(key)
        assert node is not None and node.text.strip() == "0", (
            f"{key} must be 0 (crew#340)"
        )
